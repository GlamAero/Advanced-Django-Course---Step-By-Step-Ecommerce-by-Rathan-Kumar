from .models import Cart, CartItem
from .views import _cart_id


def counter(request):

    cart_count = 0
    
    # THIS FUNCTION IS USED TO COUNT THE TOTAL QUANTITIES OF PRODUCTS IN ALL THE CART ITEMS IN THE CART AND ADD IT TO THE CONTEXT
    # *'if 'admin' in request.path' checks if the current URL('request.path') contains the word "admin". And if so, it returns an empty dictionary('return {}').
    # If not, it retrieves the quantity of each cart items from the database, add them all and counts them.

    if 'admin' in request.path:
        return {}
    else:
        try:
            cart = Cart.objects.filter(cart_id=_cart_id(request))

            # if the current user is logged in:
            if request.user.is_authenticated:

                # get all the cart_items where the user is the currently logged in user:
                cart_items = CartItem.objects.filter(user=request.user)
            
            else:
                # 'cart[:1]' retrieves the first cart object from the queryset.
                cart_items = CartItem.objects.filter(cart=cart[:1])
            for cart_item in cart_items:
                cart_count += cart_item.quantity

        except cart.DoesNotExists:
            cart_count = 0

    return dict(cart_count=cart_count)



    # THIS FUNCTION IS USED TO COUNT THE CART ITEM IN THE CART AND ADD IT TO THE CONTEXT
    # if 'admin' in request.path: 
    #     return {}
    # else: 
    #     try: 
    #         cart = Cart.objects.get(cart_id=_cart_id(request))
    #         # cart_count = cart.cartitem_set.all().count()
    #         cart_items = CartItem.objects.filter(cart=cart)
    #         cart_count = cart_items.count()
    #     except Cart.DoesNotExist: 
    #         cart_count = 0 
    # return dict(cart_count=cart_count)
