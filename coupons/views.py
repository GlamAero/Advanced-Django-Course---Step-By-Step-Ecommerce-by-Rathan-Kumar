from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from .models import Coupon
from carts.models import Cart

@require_POST
@login_required
def validate_coupon(request):
    code = request.POST.get('code')
    cart_id = request.session.get('cart_id')
    
    if not code:
        return JsonResponse({'valid': False, 'error': 'Coupon code is required'})
    
    try:
        coupon = Coupon.objects.get(code=code, active=True)
    except Coupon.DoesNotExist:
        return JsonResponse({'valid': False, 'error': 'Invalid coupon code'})
    
    # Get cart total
    cart_total = 0
    if cart_id:
        try:
            cart = Cart.objects.get(cart_id=cart_id)
            cart_total = cart.get_cart_total()
        except Cart.DoesNotExist:
            pass
    
    # Validate coupon
    if not coupon.is_valid_for_user(request.user, cart_total):
        return JsonResponse({'valid': False, 'error': 'Coupon not applicable'})
    
    # Calculate discount
    discount_amount = coupon.discount if coupon.discount_type == 'fixed' else coupon.discount
    discount_type = coupon.discount_type
    discounted_total = coupon.apply_discount(cart_total)
    
    # Store in session
    request.session['coupon_id'] = coupon.id
    request.session['coupon_code'] = coupon.code
    request.session['discount_amount'] = float(discount_amount)
    request.session['discount_type'] = discount_type
    
    return JsonResponse({
        'valid': True,
        'code': coupon.code,
        'discount_type': discount_type,
        'discount_amount': float(discount_amount),
        'discounted_total': float(discounted_total),
        'message': f"Coupon applied successfully! You saved ${discount_amount}" if discount_type == 'fixed' 
                   else f"Coupon applied successfully! You saved {discount_amount}%"
    })

