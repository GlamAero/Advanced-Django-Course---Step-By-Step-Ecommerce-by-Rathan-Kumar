# orders/views/vendor_payouts.py
from decimal import Decimal
from django.conf import settings
from django.shortcuts import render, redirect
from django.contrib import messages
from django.db import transaction
from django.db.models import Sum, F, ExpressionWrapper, DecimalField, Q
from django.contrib.admin.views.decorators import staff_member_required
from accounts.decorators import vendor_required
from accounts.models import VendorProfile
from orders.models import OrderItem, VendorPayout

@vendor_required
def vendor_payouts(request):
    """View for vendors to see their payout history and pending amounts"""
    vendor = request.user.vendorprofile
    payouts = VendorPayout.objects.filter(vendor=vendor).order_by('-created_at')
    
    # Calculate pending amount
    pending_amount = OrderItem.objects.filter(
        product__vendor=vendor,
        order__status='Completed',
        payout__isnull=True
    ).aggregate(
        total=Sum(ExpressionWrapper(
            F('product_price') * F('quantity'),
            output_field=DecimalField()
        ))
    )['total'] or Decimal('0.00')
    
    # Apply commission rate
    commission_rate = Decimal(settings.VENDOR_COMMISSION_RATE) / 100
    pending_amount = pending_amount * (1 - commission_rate)
    
    return render(request, 'orders/vendor_payouts.html', {
        'payouts': payouts,
        'pending_amount': pending_amount
    })


@staff_member_required
def process_vendor_payouts(request):
    """Admin view to process vendor payouts"""
    if request.method == 'POST':
        vendor_id = request.POST.get('vendor_id')
        try:
            vendor = VendorProfile.objects.get(id=vendor_id)
            with transaction.atomic():
                # Get all unpaid order products for this vendor
                unpaid_items = OrderItem.objects.filter(
                    product__vendor=vendor,
                    order__status='Completed',
                    payout__isnull=True
                )
                
                if not unpaid_items.exists():
                    messages.warning(request, "No pending payouts for this vendor")
                    return redirect('orders:admin_payment_insights')
                
                # Calculate total amount
                total_amount = unpaid_items.aggregate(
                    total=Sum(ExpressionWrapper(
                        F('product_price') * F('quantity'),
                        output_field=DecimalField()
                    ))
                )['total'] or Decimal('0.00')
                
                # Apply commission
                commission_rate = Decimal(settings.VENDOR_COMMISSION_RATE) / 100
                commission_amount = total_amount * commission_rate
                payout_amount = total_amount - commission_amount
                
                # Create payout record
                payout = VendorPayout.objects.create(
                    vendor=vendor,
                    amount=payout_amount,
                    fee=commission_amount,
                    method=request.POST.get('payout_method', 'bank_transfer')
                )
                
                # Associate order products with payout
                unpaid_items.update(payout=payout)
                
                messages.success(request, f"Payout of ${payout_amount:.2f} processed for {vendor.company_name}")
                return redirect('orders:admin_payment_insights')
                
        except VendorProfile.DoesNotExist:
            messages.error(request, "Vendor not found")
            return redirect('orders:admin_payment_insights')
    
    # For GET requests, redirect to insights
    return redirect('orders:admin_payment_insights')
