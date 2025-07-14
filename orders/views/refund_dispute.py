# orders/views/refund_dispute.py
import uuid
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_http_methods
from django.core.files.storage import default_storage
from django.contrib import messages
from django.utils import timezone
from accounts.decorators import customer_required, customer_or_vendor_required
from accounts.utils import log_activity
from orders.models import Order, OrderItem, Refund, Dispute, DisputeEvidence
from orders.forms import RefundRequestForm, DisputeForm
from store.utils.stock import add_product_stock

@customer_required
@require_http_methods(["GET", "POST"])
def request_refund(request, order_number):
    """Customer view to request a refund for a completed order."""
    order = get_object_or_404(Order, order_number=order_number, user=request.user)

    if order.status != 'Completed':
        messages.error(request, "Only completed orders can be refunded.")
        return redirect('orders:order_detail', order_number=order_number)

    form = RefundRequestForm(request.POST or None, order=order)

    if form.is_valid():
        refund = Refund.objects.create(
            order=order,
            reason=form.cleaned_data['reason'],
            additional_info=form.cleaned_data.get('additional_info', ''),
            status='pending'
        )

        # Associate selected products with the refund
        refund.items.set(form.cleaned_data['products'])

        messages.success(request, "Your refund request has been submitted.")
        log_activity(request.user, 'refund_requested', request, 
                    details=f"Refund requested for order #{order_number}")
        return redirect('orders:order_detail', order_number=order_number)

    return render(request, 'orders/request_refund.html', {
        'order': order,
        'form': form
    })

@staff_member_required
def process_refund(request, refund_id):
    """Admin view to process refunds"""
    refund = get_object_or_404(Refund, id=refund_id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'approve':
            with transaction.atomic():
                # Process refund based on payment method
                if refund.order.payment.payment_method == 'paypal':
                    result = _process_paypal_refund(refund)
                elif refund.order.payment.payment_method == 'stripe':
                    result = _process_stripe_refund(refund)
                elif refund.order.payment.payment_method == 'flutterwave':
                    result = _process_flutterwave_refund(refund)
                else:
                    # Manual refund for bank/COD
                    result = {'success': True, 'message': 'Manual refund required'}
                
                if result.get('success'):
                    refund.status = 'approved'
                    refund.processed_at = timezone.now()
                    refund.save()
                    
                    # Restock products
                    for item in refund.items.all():
                        add_product_stock(item.product, item.quantity)
                    
                    messages.success(request, "Refund processed successfully")
                    log_activity(request.user, 'refund_processed', request, 
                                details=f"Refund #{refund_id} processed")
                else:
                    messages.error(request, f"Refund failed: {result.get('message')}")
                
                return redirect('orders:admin_refund_requests')
        
        elif action == 'reject':
            refund.status = 'rejected'
            refund.save()
            messages.warning(request, "Refund request rejected")
            return redirect('orders:admin_refund_requests')
    
    return render(request, 'admin/process_refund.html', {'refund': refund})

@customer_or_vendor_required
def create_dispute(request, order_number):
    """
    Create a dispute for an order with proper multiple file handling.
    """
    # Get the order using the same logic as order_detail
    try:
        # First try to get order as customer
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
                return HttpResponseForbidden("You are not authorized to create a dispute for this order.")
                
            order = order_items.first().order
        except OrderItem.DoesNotExist:
            return HttpResponseForbidden("Order not found or unauthorized")

    form = DisputeForm(request.POST or None, request.FILES or None)

    if form.is_valid():
        dispute = Dispute.objects.create(
            order=order,
            initiated_by=request.user,
            reason=form.cleaned_data['reason'],
            details=form.cleaned_data['details'],
            status='open'
        )

        files = request.FILES.getlist('evidence_files')
        for file in files:
            filename = f"{uuid.uuid4().hex[:8]}_{file.name}"
            file_path = default_storage.save(f'disputes/{dispute.id}/{filename}', file)
            DisputeEvidence.objects.create(
                dispute=dispute,
                file=file_path,
                original_filename=file.name
            )

        messages.success(request, "Dispute created successfully.")
        log_activity(request.user, 'dispute_created', request, 
                    details=f"Dispute created for order #{order_number}")
        return redirect('orders:order_detail', order_number=order_number)

    return render(request, 'orders/create_dispute.html', {
        'order': order,
        'form': form
    })

@staff_member_required
def resolve_dispute(request, dispute_id):
    """Admin view to resolve disputes"""
    dispute = get_object_or_404(Dispute, id=dispute_id)
    
    if request.method == 'POST':
        resolution = request.POST.get('resolution')
        if resolution in ['refund_full', 'refund_partial', 'return_product', 'close_no_action']:
            dispute.resolution = resolution
            dispute.resolved_by = request.user
            dispute.resolved_at = timezone.now()
            dispute.status = 'resolved'
            dispute.save()
            
            # Execute resolution
            if resolution in ['refund_full', 'refund_partial']:
                # Create refund record
                refund = Refund.objects.create(
                    order=dispute.order,
                    reason=f"Dispute resolution: {dispute.reason}",
                    status='approved',
                    processed_at=timezone.now()
                )
                
                # Add products to refund
                refund.items.add(dispute.item)
                
                # Process refund
                if dispute.order.payment.payment_method == 'paypal':
                    _process_paypal_refund(refund)
                elif dispute.order.payment.payment_method == 'stripe':
                    _process_stripe_refund(refund)
                elif dispute.order.payment.payment_method == 'flutterwave':
                    _process_flutterwave_refund(refund)
            
            messages.success(request, "Dispute resolved successfully")
            log_activity(request.user, 'dispute_resolved', request, 
                        details=f"Dispute #{dispute_id} resolved")
            return redirect('orders:admin_disputes')
    
    return render(request, 'admin/resolve_dispute.html', {'dispute': dispute})