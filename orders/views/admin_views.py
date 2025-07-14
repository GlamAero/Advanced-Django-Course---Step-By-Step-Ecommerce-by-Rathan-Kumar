# orders/views/admin_views.py
from datetime import timedelta, timezone
from django.shortcuts import render
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Count, Sum, F, ExpressionWrapper, DecimalField, Q
from orders.models import Payment, VendorProfile, Refund, Dispute

@staff_member_required
def admin_payment_insights(request):
    """Dashboard with payment insights and vendor payouts"""
    # Date ranges
    today = timezone.now().date()
    last_week = today - timedelta(days=7)
    last_month = today - timedelta(days=30)
    
    # Payment method breakdown
    payment_methods = Payment.objects.values('payment_method').annotate(
        total_amount=Sum('amount_paid'),
        total_orders=Count('order')
    ).order_by('-total_amount')
    
    # Vendor payouts
    vendors = VendorProfile.objects.annotate(
        total_sales=Sum('products__order_items__price'),
        pending_payout=Sum(
            ExpressionWrapper(
                F('products__order_items__price') * F('products__order_items__quantity'),
                output_field=DecimalField()
            ),
            filter=Q(products__order_items__order__status='Completed') & 
                   Q(products__order_items__payout__isnull=True)
        )
    ).filter(total_sales__gt=0).order_by('-total_sales')
    
    # Refund statistics
    refunds = Refund.objects.values('status').annotate(
        count=Count('id'),
        total_amount=Sum('amount')
    )
    
    # Dispute statistics
    disputes = Dispute.objects.values('status').annotate(count=Count('id'))
    
    # Payment trends
    payment_trends = Payment.objects.filter(
        created_at__gte=last_month
    ).extra({
        'date': "date(created_at)"
    }).values('date').annotate(
        total=Sum('amount_paid'),
        count=Count('id')
    ).order_by('date')
    
    # Format data for charts
    payment_trends_data = {
        'dates': [pt['date'].strftime('%Y-%m-%d') for pt in payment_trends],
        'amounts': [float(pt['total']) for pt in payment_trends],
        'counts': [pt['count'] for pt in payment_trends]
    }
    
    return render(request, 'admin/payment_insights.html', {
        'payment_methods': payment_methods,
        'vendors': vendors,
        'refunds': refunds,
        'disputes': disputes,
        'payment_trends': payment_trends_data
    })

@staff_member_required
def admin_refund_requests(request):
    """List of refund requests for admin"""
    status_filter = request.GET.get('status', 'pending')
    refunds = Refund.objects.all().order_by('-requested_at')
    
    if status_filter != 'all':
        refunds = refunds.filter(status=status_filter)
    
    return render(request, 'admin/refund_requests.html', {
        'refunds': refunds,
        'status_filter': status_filter
    })

@staff_member_required
def admin_disputes(request):
    """List of disputes for admin"""
    status_filter = request.GET.get('status', 'open')
    disputes = Dispute.objects.all().order_by('-created_at')
    
    if status_filter != 'all':
        disputes = disputes.filter(status=status_filter)
    
    return render(request, 'admin/disputes.html', {
        'disputes': disputes,
        'status_filter': status_filter
    })