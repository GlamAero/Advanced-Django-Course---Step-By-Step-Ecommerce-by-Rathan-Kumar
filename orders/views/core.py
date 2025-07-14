# orders/views/core.py
from decimal import Decimal
import logging
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponseForbidden
from django.contrib import messages
from django.db.models import Q
from django.core.paginator import Paginator
from django.db import transaction
from accounts.decorators import customer_required, vendor_required, customer_or_vendor_required
from carts.models import CartItem
from coupons.models import Coupon
from coupons.services import apply_coupon_to_order
from orders.models import Order, OrderItem, Payment, Refund, Dispute
from orders.forms import OrderForm

logger = logging.getLogger(__name__)

@customer_required
def customer_orders(request):
    user = request.user
    status_filter = request.GET.get("status", "all").lower()
    search_query = request.GET.get("q", "")
    
    orders = Order.objects.filter(user=user).select_related('payment').order_by("-created_at")

    if search_query:
        orders = orders.filter(
            Q(order_number__icontains=search_query) |
            Q(payment__transaction_id__icontains=search_query)
        )

    if status_filter != "all":
        orders = orders.filter(status__iexact=status_filter)

    paginator = Paginator(orders, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(request, "orders/customer_orders.html", {
        "orders": page_obj,
        "status_filter": status_filter,
        "search_query": search_query
    })


@customer_required
def place_order(request):
    user = request.user
    cart_items = CartItem.objects.filter(user=user).select_related('product')

    if not cart_items.exists():
        messages.warning(request, "Your cart is empty")
        return redirect('store')

    total = sum(item.product.price * item.quantity for item in cart_items)
    tax = total * Decimal(settings.TAX_RATE)
    grand_total = total + tax

    if request.method != 'POST':
        return redirect('checkout')

    form = OrderForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Please correct the errors in the form")
        return redirect('checkout')

    try:
        with transaction.atomic():
            order = form.save(commit=False)
            order.user = user
            order.order_total = grand_total
            order.tax = tax
            order.ip = request.META.get('REMOTE_ADDR')
            order.is_ordered = False
            order.save()

            # Create initial payment record
            payment = Payment.objects.create(
                user=user,
                payment_method=request.POST.get('payment_method', 'paypal'),
                amount_paid=0.00,
                status='PENDING'
            )

            order.payment = payment
            order.save()

            # Apply coupon if available in session
            coupon_id = request.session.get('coupon_id')
            if coupon_id:
                try:
                    coupon = Coupon.objects.get(id=coupon_id)
                    order = apply_coupon_to_order(order, coupon)
                    # Clear coupon from session
                    request.session.pop('coupon_id', None)
                    request.session.pop('coupon_code', None)
                except Coupon.DoesNotExist:
                    logger.warning(f"Coupon with id {coupon_id} does not exist.")

        return render(request, 'orders/payments.html', {
            'order': order,
            'cart_items': cart_items,
            'total': total,
            'tax': tax,
            'grand_total': grand_total,
            'paypal_client_id': settings.PAYPAL_CLIENT_ID,
            'stripe_public_key': settings.STRIPE_PUBLIC_KEY,
            'flutterwave_public_key': settings.FLUTTERWAVE_PUBLIC_KEY,
        })

    except Exception as e:
        logger.exception(f"Order placement failed: {str(e)}")
        messages.error(request, "Error processing your order. Please try again.")
        return redirect('checkout')

@customer_required
def payment_success(request):
    order_number = request.GET.get('order_number')
    try:
        order = Order.objects.get(
            user=request.user, 
            order_number=order_number, 
            is_ordered=True
        )
        return render(request, "orders/success.html", {'order': order})
    except Order.DoesNotExist:
        messages.error(request, "Order not found")
        return redirect('store')

@customer_or_vendor_required
def order_detail(request, order_number):
    # First try to get order as customer
    try:
        order = Order.objects.get(
            user=request.user,
            order_number=order_number
        )
    except Order.DoesNotExist:
        # If not found as customer, try as vendor
        try:
            # Get order items belonging to this vendor
            order_items = OrderItem.objects.filter(
                vendor__user=request.user,
                order__order_number=order_number
            )
            
            if not order_items.exists():
                return HttpResponseForbidden("You are not authorized to view this order.")
                
            order = order_items.first().order
        except OrderItem.DoesNotExist:
            return HttpResponseForbidden("Order not found or unauthorized")
    
    order_items = order.items.select_related('product').prefetch_related('variations')
    refunds = Refund.objects.filter(order=order)
    disputes = Dispute.objects.filter(order=order).prefetch_related('evidence')
    
    return render(request, "orders/order_detail.html", {
        "order": order,
        "order_items": order_items,
        "refunds": refunds,
        "disputes": disputes
    })