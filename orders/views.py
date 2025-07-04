from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse
from carts.models import CartItem
from .forms import OrderForm
from .models import Order, Payment, OrderProduct
from store.models import Product, Variation, VariationCombination
import datetime
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
import json, requests
from django.db.models import Count
from decimal import Decimal



# Dedicated Payment View - Displays user's payments
@login_required
def payments(request):
    payments = Payment.objects.filter(user=request.user).order_by("-created_at")
    return render(request, "orders/payments.html", {"payments": payments})


@csrf_exempt
@login_required
def save_payment_data(request):
    if request.method == "POST":
        data = json.loads(request.body)

        order = Order.objects.get(user=request.user, is_ordered=False)
        cart_items = CartItem.objects.filter(user=request.user)

        # (1) Create Payment
        payment = Payment.objects.create(
            user=request.user,
            paypal_order_id=data["paypal_order_id"],
            transaction_id=data["transaction_id"],
            payment_method=data["payment_method"],
            amount_paid=data["amount_paid"],
            status=data["status"],
        )

        # (2) Update Order
        order.payment = payment
        order.is_ordered = True
        order.save()

        # (3) Deduct stock based on product type
        for item in cart_items:
            product = item.product
            quantity = item.quantity
            variations = item.variations.all()
            var_count = variations.count()

            if var_count == 0:
                # SINGLE PRODUCT
                product.stock -= quantity
                product.save()

            elif var_count == 1:
                # PRODUCT WITH ONE VARIATION
                variation = variations.first()
                variation.stock -= quantity
                variation.save()

                # Update total product stock from all related variations
                total_stock = sum(v.stock for v in Variation.objects.filter(product=product))
                product.stock = total_stock
                product.save()

            else:
                # PRODUCT WITH VARIATION COMBINATION
                combo = VariationCombination.objects.filter(
                    product=product,
                    variations__in=variations
                ).annotate(
                    match_count=Count("variations")
                ).filter(
                    match_count=var_count
                ).first()

                if combo:
                    combo.stock -= quantity
                    combo.save()

                    # Update total product stock from all related combinations
                    total_combo_stock = sum(c.stock for c in VariationCombination.objects.filter(product=product))
                    product.stock = total_combo_stock
                    product.save()

        # (4) Clear cart
        cart_items.delete()

        return JsonResponse({'payment_id': payment.transaction_id, 'status': payment.status})


# Move Cart Items To OrderProduct Table
def move_cart_items_to_order(user, order):
    """
    Transfers CartItems to OrderProduct table after successful payment and ensures proper deletion.
    """
    cart_items = CartItem.objects.filter(user=user)
    if cart_items.exists():
        for item in cart_items:
            order_product = OrderProduct.objects.create(
                order=order,
                user=user,
                product=item.product,
                quantity=item.quantity,
                product_price=item.product.price,
                ordered=True,
            )
            order_product.variations.set(item.variations.all())
            item.is_active = False
            item.save()
            item.delete()
    return True


def place_order(request, total=Decimal('0.00'), quantity=0):
    current_user = request.user
    cart_items = CartItem.objects.filter(user=current_user)
    cart_count = cart_items.count()

    if cart_count <= 0:
        return redirect('store')

    grand_total = Decimal('0.00')
    tax = Decimal('0.00')

    for cart_item in cart_items:
        total += cart_item.product.price * cart_item.quantity
        quantity += cart_item.quantity

    tax = total * Decimal('0.02')
    grand_total = total + tax

    if request.method == 'POST':
        form = OrderForm(request.POST)
        if form.is_valid():
            data = Order()
            data.user = current_user
            data.first_name = form.cleaned_data['first_name']
            data.last_name = form.cleaned_data['last_name']
            data.phone = form.cleaned_data['phone']
            data.email = form.cleaned_data['email']
            data.address_line_1 = form.cleaned_data['address_line_1']
            data.address_line_2 = form.cleaned_data['address_line_2']
            data.country = form.cleaned_data['country']
            data.state = form.cleaned_data['state']
            data.city = form.cleaned_data['city']
            data.order_note = form.cleaned_data['order_note']
            data.order_total = grand_total
            data.tax = tax
            data.ip = request.META.get('REMOTE_ADDR')
            data.save()

            current_date = datetime.date.today().strftime("%Y%m%d")
            order_number = current_date + str(data.id)
            data.order_number = order_number
            data.save()

            order = Order.objects.filter(
                user=current_user,
                is_ordered=False,
                order_number=data.order_number
            ).first()

            if not order:
                return JsonResponse({"error": "Order not found in database."}, status=404)

            context = {
                'order': order,
                'cart_items': cart_items,
                'total': total,
                'tax': tax,
                'grand_total': grand_total,
                'paypal_client_id': settings.PAYPAL_CLIENT_ID
            }
            return render(request, 'orders/payments.html', context)
        else:
            return HttpResponse("Something went wrong.")
    else:
        return redirect('checkout')

def get_paypal_access_token():
    response = requests.post(
        f"{settings.PAYPAL_API_BASE}/v1/oauth2/token",
        headers={"Accept": "application/json"},
        data={"grant_type": "client_credentials"},
        auth=(settings.PAYPAL_CLIENT_ID, settings.PAYPAL_SECRET),
    )
    return response.json().get("access_token")

@csrf_exempt
def create_paypal_order(request):
    current_user = request.user
    try:
        order = Order.objects.filter(user=current_user, is_ordered=False).latest("created_at")
        grand_total = order.order_total
    except Order.DoesNotExist:
        return JsonResponse({'error': 'Order not found'}, status=404)
    token = get_paypal_access_token()
    order_data = {
        "intent": "CAPTURE",
        "purchase_units": [{
            "amount": {
                "currency_code": "USD",
                "value": f"{grand_total:.2f}"
            }
        }]
    }
    response = requests.post(
        f"{settings.PAYPAL_API_BASE}/v2/checkout/orders",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        },
        json=order_data
    )
    response_data = response.json()
    if response.status_code == 201:
        paypal_order_id = response_data["id"]
        order = Order.objects.filter(user=request.user, is_ordered=False).latest("created_at")
        order.paypal_order_id = paypal_order_id
        order.save()
        return JsonResponse({"paypal_order_id": paypal_order_id})
    else:
        return JsonResponse({"error": "Failed to create PayPal order", "details": response_data}, status=400)

@csrf_exempt
def capture_paypal_order(request, order_id):
    token = get_paypal_access_token()
    if not token:
        return JsonResponse({"error": "Failed to authenticate with PayPal"}, status=500)
    response = requests.post(
        f"{settings.PAYPAL_API_BASE}/v2/checkout/orders/{order_id}/capture",
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"}
    )
    response_data = response.json()
    if response.status_code == 201:
        captures = response_data.get("purchase_units", [{}])[0].get("payments", {}).get("captures", [])
        if captures:
            payment_id = captures[0].get("id", "UNKNOWN")
            payment_status = response_data.get("status", "FAILED")
            amount_paid = captures[0].get("amount", {}).get("value", 0)
            order = Order.objects.filter(paypal_order_id=order_id).first()
            if not order:
                return JsonResponse({"error": "Order not found in the database."}, status=404)
            with transaction.atomic():
                order.transaction_id = payment_id
                if payment_status == "COMPLETED":
                    order.status = "Completed"
                    order.is_ordered = True
                    move_cart_items_to_order(order.user, order)
                    order_products = OrderProduct.objects.filter(order=order)

                    for order_product in order_products:
                        product = order_product.product
                        quantity = order_product.quantity
                        variations = order_product.variations.all()
                        var_count = variations.count()

                        if var_count == 0:
                            # Single product
                            if product.stock >= quantity:
                                product.stock -= quantity
                                product.save()

                        elif var_count == 1:
                            # Product with one variation
                            variation = variations.first()
                            if variation.stock >= quantity:
                                variation.stock -= quantity
                                variation.save()

                                # Update total product stock from all variations
                                total_var_stock = sum(v.stock for v in Variation.objects.filter(product=product))
                                product.stock = total_var_stock
                                product.save()

                        else:
                            # Product with variation combination
                            combo = VariationCombination.objects.filter(
                                product=product,
                                variations__in=variations
                            ).annotate(match=Count('variations')).filter(match=var_count).first()

                            if combo and combo.stock >= quantity:
                                combo.stock -= quantity
                                combo.save()

                                # Update total product stock from all combinations
                                total_combo_stock = sum(c.stock for c in VariationCombination.objects.filter(product=product))
                                product.stock = total_combo_stock
                                product.save()

                    if request.session.get("cart_id"):
                        del request.session["cart_id"]
                        request.session.modified = True
                payment = Payment.objects.create(
                    user=order.user,
                    paypal_order_id=order.paypal_order_id,
                    transaction_id=payment_id,
                    payment_method="PayPal",
                    order_total=order.order_total,
                    amount_paid=amount_paid,
                    status=payment_status
                )
                order_products.update(payment=payment)
                for order_product in order_products:
                    cart_item = CartItem.objects.filter(user=order.user, product=order_product.product).first()
                    if cart_item:
                        order_product.variations.set(cart_item.variations.all())
                order.payment = payment
                order.save()
            return JsonResponse({
                "message": "Payment captured successfully!",
                "order_id": order_id,
                "status": payment_status,
                "payment_id": payment_id
            })
        return JsonResponse({"error": "Payment ID not found in PayPal response."}, status=500)
    return JsonResponse({"error": "Failed to capture PayPal order", "details": response_data}, status=response.status_code)

def success(request):
    return render(request, "orders/success.html")