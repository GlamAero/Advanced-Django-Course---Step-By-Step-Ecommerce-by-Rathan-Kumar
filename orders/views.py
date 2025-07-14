import uuid
from django.http import JsonResponse
import stripe
import requests
import logging
import hmac
import hashlib

from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_http_methods
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.core.files.storage import default_storage
from django.urls import reverse
from django.db import transaction

from accounts.decorators import customer_required, vendor_required, customer_or_vendor_required
from accounts.utils import log_activity
from carts.models import CartItem
from orders.models import Payment, OrderItem
from store.utils.stock import deduct_product_stock, add_product_stock


stripe.api_key = settings.STRIPE_SECRET_KEY
logger = logging.getLogger(__name__)

# ======= UTILITY FUNCTIONS =======
def get_paypal_access_token():
    """Retrieve PayPal access token with error handling"""
    try:
        auth = (settings.PAYPAL_CLIENT_ID, settings.PAYPAL_SECRET_KEY)
        data = {'grant_type': 'client_credentials'}
        response = requests.post(
            f"{settings.PAYPAL_API_BASE}/v1/oauth2/token",
            data=data,
            auth=auth,
            timeout=10
        )
        response.raise_for_status()
        return response.json().get('access_token')
    except requests.RequestException as e:
        logger.error(f"PayPal token request failed: {str(e)}")
    except (KeyError, ValueError) as e:
        logger.error(f"PayPal token parsing failed: {str(e)}")
    return None

def verify_flutterwave_signature(payload, signature):
    """Verify Flutterwave webhook signature"""
    secret = settings.FLUTTERWAVE_SECRET_HASH
    generated_signature = hmac.new(
        secret.encode('utf-8'),
        payload,
        hashlib.sha256
    ).hexdigest()
    return generated_signature == signature

def _create_paypal_order(order, amount):
    token = get_paypal_access_token()
    if not token:
        return JsonResponse({"error": "Payment service unavailable"}, status=503)

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
        "PayPal-Request-Id": f"ORDER-{order.order_number}"
    }
    
    payload = {
        "intent": "CAPTURE",
        "purchase_units": [{
            "reference_id": order.order_number,
            "amount": {
                "currency_code": "USD",
                "value": str(amount)
            }
        }]
    }
    
    try:
        response = requests.post(
            f"{settings.PAYPAL_API_BASE}/v2/checkout/orders",
            headers=headers,
            json=payload,
            timeout=15
        )
        response.raise_for_status()
        order_data = response.json()
        
        # Store PayPal ID with order
        order.paypal_order_id = order_data["id"]
        order.save()
        
        return JsonResponse({
            "id": order_data["id"],
            "status": order_data["status"],
            "links": order_data["links"]
        })
        
    except requests.RequestException as e:
        logger.error(f"PayPal API error: {str(e)}")
        return JsonResponse({"error": "Payment gateway error"}, status=502)
    except (KeyError, ValueError) as e:
        logger.error(f"PayPal response parsing error: {str(e)}")
        return JsonResponse({"error": "Invalid gateway response"}, status=502)

def _create_stripe_intent(order, amount):
    
    try:
        # Convert to cents
        amount_cents = int(amount * 100)
        
        intent = stripe.PaymentIntent.create(
            amount=amount_cents,
            currency="usd",
            metadata={
                "order_id": order.id,
                "order_number": order.order_number,
                "user_id": order.user.id
            },
            description=f"Order #{order.order_number}",
            receipt_email=order.email
        )
        
        # Store Stripe ID with order
        order.stripe_payment_intent = intent.id
        order.save()
        
        return JsonResponse({"clientSecret": intent.client_secret})
        
    except stripe.error.StripeError as e:
        logger.error(f"Stripe error: {str(e)}")
        return JsonResponse({"error": str(e)}, status=400)
    except Exception as e:
        logger.exception(f"Stripe processing error: {str(e)}")
        return JsonResponse({"error": "Payment processing failed"}, status=500)

def _create_flutterwave_payment(order, amount):
    """Create Flutterwave payment transaction"""
    try:
        # Generate unique transaction reference
        tx_ref = f"FLW-{order.order_number}-{uuid.uuid4().hex[:8]}"
        
        headers = {
            "Authorization": f"Bearer {settings.FLUTTERWAVE_SECRET_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "tx_ref": tx_ref,
            "amount": str(amount),
            "currency": settings.FLUTTERWAVE_CURRENCY,
            "redirect_url": f"{settings.BASE_URL}{reverse('orders:payment_success')}?order_number={order.order_number}",
            "payment_options": "card, mobilemoney, ussd",
            "meta": {
                "order_number": order.order_number,
                "user_id": order.user.id
            },
            "customer": {
                "email": order.email,
                "name": f"{order.first_name} {order.last_name}",
                "phone_number": order.phone
            },
            "customizations": {
                "title": settings.SITE_NAME,
                "description": f"Payment for Order #{order.order_number}",
                "logo": settings.LOGO_URL
            }
        }
        
        response = requests.post(
            "https://api.flutterwave.com/v3/payments",
            headers=headers,
            json=payload,
            timeout=15
        )
        response.raise_for_status()
        response_data = response.json()
        
        if response_data.get("status") == "success":
            # Store Flutterwave reference with order
            order.flutterwave_tx_ref = tx_ref
            order.save()
            
            return JsonResponse({
                "payment_link": response_data["data"]["link"],
                "tx_ref": tx_ref
            })
        else:
            logger.error(f"Flutterwave payment error: {response_data.get('message')}")
            return JsonResponse({"error": "Payment gateway error"}, status=502)
            
    except requests.RequestException as e:
        logger.error(f"Flutterwave API error: {str(e)}")
        return JsonResponse({"error": "Payment gateway connection failed"}, status=502)
    except (KeyError, ValueError) as e:
        logger.error(f"Flutterwave response parsing error: {str(e)}")
        return JsonResponse({"error": "Invalid gateway response"}, status=502)
    except Exception as e:
        logger.exception(f"Flutterwave processing error: {str(e)}")
        return JsonResponse({"error": "Payment processing failed"}, status=500)

def _create_offline_payment(order, method):
    try:
        with transaction.atomic():
            # Update existing payment record
            payment = Payment.objects.get(order=order)
            payment.payment_method = method
            payment.status = 'PENDING'
            payment.save()
            
            order.status = "Pending Payment" if method == "bank_transfer" else "COD Pending"
            order.save()
            
        return JsonResponse({
            "message": "Payment recorded. Awaiting confirmation",
            "payment_id": payment.id
        })
        
    except Payment.DoesNotExist:
        logger.error(f"No payment record found for order {order.id}")
        return JsonResponse({"error": "Order payment record missing"}, status=400)

def _capture_paypal(order, order_id, request):
    token = get_paypal_access_token()
    if not token:
        return JsonResponse({"error": "Payment service unavailable"}, status=503)
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
        "PayPal-Request-Id": f"CAPTURE-{order.order_number}"
    }
    
    try:
        response = requests.post(
            f"{settings.PAYPAL_API_BASE}/v2/checkout/orders/{order_id}/capture",
            headers=headers,
            json={},
            timeout=15
        )
        response.raise_for_status()
        capture_data = response.json()
        
        if capture_data.get("status") == "COMPLETED":
            return _process_payment_success(order, "paypal", capture_data, request)
        
        logger.error(f"PayPal capture failed: {response.text}")
        return JsonResponse({"error": "Payment capture failed"}, status=400)
        
    except requests.RequestException as e:
        logger.error(f"PayPal capture API error: {str(e)}")
        return JsonResponse({"error": "Payment gateway error"}, status=502)

def _capture_stripe(order, payment_intent, request):
    try:
        intent = stripe.PaymentIntent.retrieve(payment_intent)
        
        if intent.status == "succeeded":
            return _process_payment_success(order, "stripe", intent, request)
        
        logger.warning(f"Stripe payment not succeeded: {intent.status}")
        return JsonResponse({"error": "Payment not completed"}, status=400)
        
    except stripe.error.StripeError as e:
        logger.error(f"Stripe capture error: {str(e)}")
        return JsonResponse({"error": str(e)}, status=400)

@transaction.atomic
def _process_payment_success(order, method, gateway_data, request):
    """Finalize successful payment and complete order"""
    try:
        # Update payment record
        payment = order.payment
        payment.payment_method = method
        payment.status = 'COMPLETED'
        payment.amount_paid = order.order_total
        
        # Set transaction ID based on payment method
        if method == "paypal":
            payment.transaction_id = gateway_data.get('id', '')
        elif method == "stripe":
            payment.transaction_id = gateway_data.id
        
        payment.save()
        
        # Update order status
        order.is_ordered = True
        order.status = "Processing"  # Move to next fulfillment stage
        order.save()
        
        # Process cart items
        cart_items = CartItem.objects.filter(user=request.user)
        for item in cart_items:
            OrderItem.objects.create(
                order=order,
                user=request.user,
                product=item.product,
                quantity=item.quantity,
                product_price=item.product.price,
                ordered=True
            )
            
            # Deduct stock and handle variations
            variations = list(item.variations.all())
            deduct_product_stock(item.product, item.quantity, variations)
            item.delete()
        
        # Clear session cart
        if 'cart_id' in request.session:
            del request.session['cart_id']
        
        # Log activity
        log_activity(request.user, 'order_placed', request, 
                    details=f"Order #{order.order_number} placed")
        
        logger.info(f"Payment success for order #{order.order_number}")
        return JsonResponse({
            "success": True,
            "redirect_url": reverse('orders:payment_success') + f"?order_number={order.order_number}"
        })
        
    except Exception as e:
        logger.exception(f"Order processing failed: {str(e)}")
        return JsonResponse({"error": "Order fulfillment failed"}, status=500)

def _process_paypal_refund(refund):
    """Process PayPal refund"""
    try:
        token = get_paypal_access_token()
        if not token:
            return {'success': False, 'message': 'PayPal authentication failed'}
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        }
        
        # Calculate refund amount
        refund_amount = refund.get_refund_amount()
        
        payload = {
            "amount": {
                "value": str(refund_amount),
                "currency_code": "USD"
            }
        }
        
        response = requests.post(
            f"{settings.PAYPAL_API_BASE}/v2/payments/captures/{refund.order.payment.transaction_id}/refund",
            headers=headers,
            json=payload
        )
        
        if response.status_code in [200, 201]:
            refund_data = response.json()
            refund.transaction_id = refund_data.get('id')
            refund.save()
            return {'success': True}
        else:
            logger.error(f"PayPal refund failed: {response.text}")
            return {'success': False, 'message': response.text}
    
    except Exception as e:
        logger.error(f"PayPal refund error: {str(e)}")
        return {'success': False, 'message': str(e)}

def _process_stripe_refund(refund):
    """Process Stripe refund"""
    try:
        # Calculate refund amount in cents
        refund_amount = int(refund.get_refund_amount() * 100)
        
        # Create refund
        stripe_refund = stripe.Refund.create(
            payment_intent=refund.order.stripe_payment_intent,
            amount=refund_amount
        )
        
        refund.transaction_id = stripe_refund.id
        refund.save()
        return {'success': True}
    
    except stripe.error.StripeError as e:
        logger.error(f"Stripe refund error: {str(e)}")
        return {'success': False, 'message': str(e)}

def _process_flutterwave_refund(refund):
    """Process Flutterwave refund"""
    try:
        headers = {
            "Authorization": f"Bearer {settings.FLUTTERWAVE_SECRET_KEY}",
            "Content-Type": "application/json"
        }
        
        # Calculate refund amount
        refund_amount = refund.get_refund_amount()
        
        payload = {
            "amount": refund_amount,
            "comment": f"Refund for order {refund.order.order_number}"
        }
        
        response = requests.post(
            f"https://api.flutterwave.com/v3/transactions/{refund.order.payment.transaction_id}/refund",
            headers=headers,
            json=payload
        )
        
        if response.status_code == 200:
            refund_data = response.json()
            refund.transaction_id = refund_data['data']['id']
            refund.save()
            return {'success': True}
        else:
            logger.error(f"Flutterwave refund failed: {response.text}")
            return {'success': False, 'message': response.text}
    
    except Exception as e:
        logger.error(f"Flutterwave refund error: {str(e)}")
        return {'success': False, 'message': str(e)}

