from django.utils import timezone
from .models import Coupon

def apply_coupon_to_order(order, coupon):
    """Apply coupon to an order and update usage stats"""
    # Apply discount
    order.discount = coupon.discount
    order.save()
    
    # Update coupon usage
    coupon.users_used.add(order.user)
    coupon.use_count += 1
    coupon.save()
    
    return order