from .models import Cart, CartItem
from .views import _cart_id
from django.db.models import Sum

def counter(request):
    if 'admin' in request.path:
        return {}
    
    cart_count = 0
    try:
        if request.user.is_authenticated:
            cart_items = CartItem.objects.filter(
                user=request.user, 
                is_active=True
            ).aggregate(total=Sum('quantity'))
            cart_count = cart_items['total'] or 0
        else:
            cart = Cart.objects.get(cart_id=_cart_id(request))
            cart_items = CartItem.objects.filter(
                cart=cart, 
                is_active=True
            ).aggregate(total=Sum('quantity'))
            cart_count = cart_items['total'] or 0
            
    except (Cart.DoesNotExist, CartItem.DoesNotExist, TypeError, ValueError):
        cart_count = 0

    return {'cart_count': cart_count}


