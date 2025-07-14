# orders/views/payment_processing.py
import json
import uuid
import stripe
import requests
import logging
import hmac
import hashlib
from decimal import Decimal
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.http import JsonResponse, HttpResponse
from django.db import transaction
from django.conf import settings
from django.urls import reverse
from accounts.decorators import customer_required
from accounts.utils import log_activity
from carts.models import CartItem
from orders.views import _create_flutterwave_payment, _create_offline_payment, _create_paypal_order, _create_stripe_intent
from store.utils.stock import deduct_product_stock
from orders.models import Order, Payment, OrderItem, Refund
from .core import payment_success


stripe.api_key = settings.STRIPE_SECRET_KEY
logger = logging.getLogger(__name__)

# Utility functions (get_paypal_access_token, verify_flutterwave_signature)
# Payment creation functions (_create_paypal_order, _create_stripe_intent, etc.)
# Payment capture functions (_capture_paypal, _capture_stripe, _process_payment_success)
# Refund processing functions (_process_paypal_refund, _process_stripe_refund, etc.)

@csrf_exempt
@customer_required
def create_payment_order(request):
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)
    
    try:
        data = json.loads(request.body)
        payment_method = data["payment_method"]
        amount = Decimal(data["amount"])
        user = request.user
        
        order = Order.objects.filter(
            user=user, 
            is_ordered=False
        ).select_for_update().latest("created_at")

        if payment_method == "paypal":
            return _create_paypal_order(order, amount)
        elif payment_method == "stripe":
            return _create_stripe_intent(order, amount)
        elif payment_method == "flutterwave":
            return _create_flutterwave_payment(order, amount)
        elif payment_method in ("bank_transfer", "cash_on_delivery"):
            return _create_offline_payment(order, payment_method)
            
        return JsonResponse({"error": "Unsupported payment method"}, status=400)
        
    except Order.DoesNotExist:
        logger.error("No pending order found for payment")
        return JsonResponse({"error": "Order not found"}, status=404)
    except (KeyError, ValueError) as e:
        logger.error(f"Invalid payment data: {str(e)}")
        return JsonResponse({"error": "Invalid request data"}, status=400)
    except Exception as e:
        logger.exception(f"Payment creation error: {str(e)}")
        return JsonResponse({"error": "Internal server error"}, status=500)

@csrf_exempt
@customer_required
@require_POST
def capture_payment(request):
    """Handle payment confirmation from various gateways"""
    try:
        data = json.loads(request.body)
        payment_method = data.get('payment_method')
        amount = data.get('amount')
        
        if not payment_method or not amount:
            return JsonResponse({'error': 'Missing required parameters'}, status=400)
        
        user = request.user
        order = Order.objects.select_related('payment').select_for_update().get(
            user=user, 
            is_ordered=False
        )
        
        # Validate payment amount matches order total
        if Decimal(amount) != order.order_total:
            logger.warning(
                f"Amount mismatch for order {order.id}: "
                f"Expected {order.order_total}, got {amount}"
            )
            return JsonResponse({'error': 'Payment amount mismatch'}, status=400)
        
        if payment_method == 'paypal':
            order_id = data.get('orderID')
            if not order_id:
                return JsonResponse({'error': 'Missing PayPal order ID'}, status=400)
            return _capture_paypal(order, order_id, request)
            
        elif payment_method == 'stripe':
            payment_intent = data.get('paymentIntent')
            if not payment_intent:
                return JsonResponse({'error': 'Missing Stripe PaymentIntent'}, status=400)
            return _capture_stripe(order, payment_intent, request)
            
        else:
            return JsonResponse({'error': 'Unsupported payment method'}, status=400)
            
    except Order.DoesNotExist:
        logger.warning("Capture payment failed: No pending order found")
        return JsonResponse({'error': 'Order not found'}, status=404)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON format'}, status=400)
    except Exception as e:
        logger.exception(f"Payment capture error: {str(e)}")
        return JsonResponse({'error': 'Internal server error'}, status=500)
    
@csrf_exempt
@require_POST
def paypal_webhook(request):
    """Handle PayPal webhook notifications"""
    try:
        event = json.loads(request.body)
        event_type = event.get('event_type')
        
        if event_type == 'PAYMENT.CAPTURE.COMPLETED':
            resource = event['resource']
            transaction_id = resource['id']
            amount = Decimal(resource['amount']['value'])
            
            try:
                payment = Payment.objects.select_related('order').get(
                    transaction_id=transaction_id
                )
                payment.status = 'COMPLETED'
                payment.amount_paid = amount
                payment.save()
                
                if payment.order:
                    payment.order.is_ordered = True
                    payment.order.status = 'Processing'
                    payment.order.save()
                    
                return HttpResponse(status=200)
            except Payment.DoesNotExist:
                logger.warning(f"Payment not found: {transaction_id}")
        
        # Handle refunds
        elif event_type == 'PAYMENT.CAPTURE.REFUNDED':
            resource = event['resource']
            refund_id = resource['id']
            
            try:
                refund = Refund.objects.get(transaction_id=refund_id)
                refund.status = 'completed'
                refund.save()
                return HttpResponse(status=200)
            except Refund.DoesNotExist:
                logger.warning(f"Refund not found: {refund_id}")
        
        return HttpResponse(status=200)
    except Exception as e:
        logger.error(f"PayPal webhook error: {str(e)}")
        return HttpResponse(status=400)


@csrf_exempt
@require_POST
def stripe_webhook(request):
    """Handle Stripe webhook notifications"""
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    
    try:
        event = stripe.Webhook.construct_event(
            payload,
            sig_header,
            settings.STRIPE_WEBHOOK_SECRET
        )
        
        if event['type'] == 'payment_intent.succeeded':
            payment_intent = event['data']['object']
            transaction_id = payment_intent['id']
            
            try:
                payment = Payment.objects.select_related('order').get(
                    transaction_id=transaction_id
                )
                payment.status = 'COMPLETED'
                payment.amount_paid = Decimal(payment_intent['amount']) / 100
                payment.save()
                
                if payment.order:
                    payment.order.is_ordered = True
                    payment.order.status = 'Processing'
                    payment.order.save()
                    
            except Payment.DoesNotExist:
                logger.warning(f"Stripe payment not found: {transaction_id}")
        
        # Handle refunds
        elif event['type'] == 'charge.refunded':
            refund = event['data']['object']
            refund_id = refund['id']
            
            try:
                refund_record = Refund.objects.get(transaction_id=refund_id)
                refund_record.status = 'completed'
                refund_record.save()
            except Refund.DoesNotExist:
                logger.warning(f"Refund not found: {refund_id}")
        
        return HttpResponse(status=200)
    except stripe.error.SignatureVerificationError:
        logger.warning("Invalid Stripe signature")
        return HttpResponse(status=400)
    except Exception as e:
        logger.error(f"Stripe webhook error: {str(e)}")
        return HttpResponse(status=400)

@csrf_exempt
@require_POST
def flutterwave_webhook(request):
    """Handle Flutterwave payment webhook notifications"""
    try:
        payload = request.body
        signature = request.headers.get('verif-hash')
        
        # Verify signature
        if not verify_flutterwave_signature(payload, signature):
            logger.warning("Invalid Flutterwave signature")
            return HttpResponse(status=401)
            
        data = json.loads(payload)
        event_type = data.get('event')
        
        if event_type == 'charge.completed':
            tx_ref = data.get('data', {}).get('tx_ref')
            transaction_id = data.get('data', {}).get('id')
            amount = Decimal(data.get('data', {}).get('amount'))
            status = data.get('data', {}).get('status')
            
            if status == 'successful':
                try:
                    order = Order.objects.select_related('payment').get(
                        flutterwave_tx_ref=tx_ref
                    )
                    payment = order.payment
                    
                    # Update payment record
                    payment.payment_method = 'flutterwave'
                    payment.transaction_id = transaction_id
                    payment.amount_paid = amount
                    payment.status = 'COMPLETED'
                    payment.save()
                    
                    # Update order status
                    order.is_ordered = True
                    order.status = 'Processing'
                    order.save()
                    
                    # Process order items
                    cart_items = CartItem.objects.filter(user=order.user)
                    for item in cart_items:
                        OrderItem.objects.create(
                            order=order,
                            user=order.user,
                            product=item.product,
                            quantity=item.quantity,
                            product_price=item.product.price,
                            ordered=True
                        )
                        
                        # Deduct stock
                        variations = list(item.variations.all())
                        deduct_product_stock(item.product, item.quantity, variations)
                        item.delete()
                    
                    logger.info(f"Flutterwave payment succeeded for order {order.order_number}")
                    return HttpResponse(status=200)
                except Order.DoesNotExist:
                    logger.warning(f"Order not found for Flutterwave tx_ref: {tx_ref}")
        
        # Handle refunds
        elif event_type == 'refund.completed':
            refund_data = data.get('data', {})
            refund_id = refund_data.get('id')
            
            try:
                refund = Refund.objects.get(transaction_id=refund_id)
                refund.status = 'completed'
                refund.save()
                return HttpResponse(status=200)
            except Refund.DoesNotExist:
                logger.warning(f"Refund not found: {refund_id}")
        
        return HttpResponse(status=200)
    except Exception as e:
        logger.error(f"Flutterwave webhook error: {str(e)}")
        return HttpResponse(status=400)