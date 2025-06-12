from django.shortcuts import render, redirect, get_object_or_404
from vendor.models import Product, Variation, VariationCombination
from .models import Cart, CartItem
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required



# Create your views here.

# The below function(a private function because the function name began with '_') generates a unique cart ID for each session:
def _cart_id(request):
    # 'session_key' is a unique identifier(session_id) for the session
    cart = request.session.session_key
    if not cart:
        request.session.create()
        cart = request.session.session_key
    return cart


# The 'add_cart' function is used to add a product to the cart:
# - It first checks if the cart already exists in the database. If not, it creates a new cart.
# - Then, it checks if the product is already in the cart. If it is, it increases the quantity by 1. If not, it creates a new cart item with a quantity of 1.
# *It sends the cart item to the database.*
# - Finally, it redirects the user to the cart page.
def add_cart(request, product_id):

    #--------------------------USER-----------------------------#
    # 'request.user' is the user making a request in the frontend, whether logged in or not.
    # If the 'user', that is 'request.user' is not logged_in(is_authenticated), such is an 'Anonymous user'. And rather than returning 'None', it returns 'Anonymous user' because in django 'request.user' is never 'None' even when no user is logged in. Instead, Django assigns an instance of 'AnonymousUser'. This design choice ensures consistency and avoids unnecessary 'None' checks in code.
    current_user = request.user

    #--------------------------PRODUCT--------------------------#
    product = get_object_or_404(Product, id=product_id)

    # ----------------- FOR PRODUCT VARIATION:----------------#
    # to get a list of product variations, meaning a list of products and their corresponding variations:
    # Extract Variations in One Step
    product_variation = []

    # 'key' is got from the 'product_details.html' file, in the 'select' area.
    # 'item' is the name given to the 'select' element in our 'stores/product_detail.html' page.
    # 'request.POST' is the dictionary containing the options we selected in 'product_detail.html' page.
    # Thus 'item' is like 'color' or 'size' while 'request.POST[item] is like 'blue' for color or 'medium' for size
    if request.method == 'POST':
        # If the 'color' is 'blue', 'color' is the 'item' and will be saved as 'key'
        # Similarly if the 'size' is 'medium', 'size' is the 'item' and will be saved as 'key'
        # The value the user gave for 'color' would be used. Thus, for 'blue' being 'request.POST[key]', it will be saved as 'value'
        # Similarly, in the case of 'size'; for 'medium' being 'request.POST[key]' will be saved as 'value'
        for key, value in request.POST.items():
            # get the 'variation' where the key and value chosen by the user corresponds with the values in the 'models.py file
            # 'iexact' means to ignore whether the inputed value is capital or small letter.
            try:
                variation = Variation.objects.get(product=product, variation_category__iexact=key, variation_value__iexact=value)
                # here we append the variations to the 'product_variation' we created above:
                product_variation.append(variation)
            except Variation.DoesNotExist:
                pass  # Avoid errors if an invalid selection is made

    # Check if a VariationCombination exists for the chosen variations
    variation_combination = VariationCombination.objects.filter(product=product, variations__in=product_variation).first()

    if not variation_combination:
        variation_combination = VariationCombination.objects.create(product=product)
        variation_combination.variations.set(product_variation)  # Assign selected variations
        variation_combination.save()  # Ensure data is saved in the database


    # If User is Logged In (Use User-Based Cart):
    # if the current user is logged in:
    # remember that logged in user already have a cart assigned them in function 'login' in 'accounts/views.py'
    if current_user.is_authenticated:
        # ------------------------CART_ITEM--------------------------#

        # get all the items of the product in the cart, after being added to cart. This is taken from the database(models.py file)
        # Here we did not use the 'cart=cart'(where'cart_id=cart_id' to filter the CartItem we need because the user is logged in, thus we use the 'user=current_user(who has 'user_id') to filter. Unlike the 'cart_id' of Cart session, it is more stable and unique per user and does not generate a token each time a user adds to cart whn not logged in.
        is_cart_item_exists = CartItem.objects.filter(product=product, user=current_user).exists()

        # check if cart_item(product, e.g Air Jordan) exists:
        if is_cart_item_exists:

            # Note that we used 'user=request.user' instead of 'cart=cart' in the definition of the 'cart_item' here. This is so because we are logged in and so we have a logged in user we can use.
            # Also the logged in user is already assigned a 'cart' object in the function 'login' of 'accounts/views.py', hence not accessed here.
            cart_items = CartItem.objects.filter(product=product, user=current_user)

            # the below means the existing variation(s) associated with the cart_item(particular product(that is: product with id=product_id of product the user selected) in the said cart) that has been added to cart when we previously added to cart.
            # 'item.variations.all()' retrieves all variations (size, color, etc.) linked to a specific cart_item(item). It returns the variations of that cart item (Color = Black, Size = Medium).
            # This('item.variations.all') does not return all the variations of all products in the cart. Rather, it returns all variations(e.g color: red, size: medium etc) of one item(e.g Air Jordan) the user selected when they 'added to cart' at a time.

            # 'cart_items' is a queryset that contains all cart items for the given product and user.
            # 'existing_variation' is a list of variations associated with the current cart item.
            for item in cart_items:
                existing_variation = list(item.variations.all())

                # Compare Variations as Sets for Accuracy
                # 'set(product_variation)' converts the list of variations selected by the user to a set for accurate comparison.
                # 'set(existing_variation)' converts the list of existing variations in the cart item to a set for accurate comparison.
                # This ensures that the order of variations does not affect the comparison.
                # 'set' is used to compare the variations selected by the user with the existing variations in the cart item.
                if set(product_variation) == set(existing_variation):
                    item.quantity += 1  # Increase quantity
                    item.save()
                    break

            # If no existing variation matches, create a new cart item
            else:
                cart_item = CartItem.objects.create(product=product, quantity=1, user=current_user)
                cart_item.variations.set(product_variation)
                cart_item.save()

        # if the cart_item(product, e.g Air Jordan) does not exist in the cart/database, create a new one
        else:
            # if the product does not exist at all in the CartItem section of the database:
            cart_item = CartItem.objects.create(product=product, quantity=1, user=current_user)
            cart_item.variations.set(product_variation)
            cart_item.save()

    else:  
        # If User is NOT Logged In (Use Session-Based Cart)
        # Here we are not logged in, so we will use the session-based cart.
        # Get or Create Cart
        # 'request.session.get('cart_id')' retrieves the cart ID from the session. If it does not exist, it returns None.
        # 'cart_id' is the unique identifier for the cart session.
        # 'request.session' is a dictionary-like object that stores data for the user's session.
        # 'request.session.get('cart_id')' checks if the cart ID already exists in the session.
        # If it does not exist, it creates a new cart and saves the cart ID in the session.
        # '_cart_id(request)' is a function defined above to generate a unique cart ID for the session.
        cart_id = request.session.get('cart_id')
        if not cart_id:
            cart = Cart.objects.create(cart_id=_cart_id(request))
            cart.save()
            request.session['cart_id'] = cart.cart_id
        else:
            cart = Cart.objects.get(cart_id=cart_id)

        is_cart_item_exists = CartItem.objects.filter(product=product, cart=cart).exists()
        
        if is_cart_item_exists:
            cart_items = CartItem.objects.filter(product=product, cart=cart)

            # The 'cart_items' variable retrieves all the cart items associated with the cart
            # - The 'is_active=True' condition ensures that only active items are retrieved. That is, items that are still in the cart and not marked as inactive.
            for item in cart_items:

                # 'item.variations.all()' retrieves all variations (size, color, etc.) linked to a specific cart_item(item). It returns the variations of that cart item (Color = Black, Size = Medium).
                # This('item.variations.all') does not return all the variations of all products in the cart. Rather, it returns all variations(e.g color: red, size: medium etc) of one item(e.g Air Jordan) the user selected when they 'added to cart' at a time.
                existing_variation = list(item.variations.all())

                # Compare Variations as Sets for Accuracy
                # 'set(product_variation)' converts the list of variations selected by the user to a set for accurate comparison.
                # 'set(existing_variation)' converts the list of existing variations in the cart item to a set for accurate comparison.
                if set(product_variation) == set(existing_variation):
                    # If the variations match, increase the quantity and save the item
                    # 'item.quantity' retrieves the quantity of the cart item.
                    item.quantity += 1
                    item.save()
                    
                    # If the variations match, increase the quantity and save the item
                    break

            # If no existing variation matches, create a new cart item
            else:

                # If no existing variation matches, create a new cart item
                cart_item = CartItem.objects.create(product=product, quantity=1, cart=cart)
                # 'cart_item.variations.set(product_variation)' sets the variations for the cart item.
                cart_item.variations.set(product_variation)
                cart_item.save()

        # if the cart_item(product, e.g Air Jordan) does not exist in the cart/database, create a new one
        else:
            cart_item = CartItem.objects.create(product=product, quantity=1, cart=cart)

            # 'cart_item.variations.set(product_variation)' sets the variations for the cart item.
            # 'product_variation' is a list of variations selected by the user.
            # 'cart_item.variations.set(product_variation)' sets the variations for the cart item.
            # This ensures that the cart item has the correct variations associated with it.
            cart_item.variations.set(product_variation)
            cart_item.save()

    return redirect('cart')


# The 'remove_cart' function is used to remove a product quantity or a product(if the quantity is originally (less or) equal to 1) from the cart:
def remove_cart(request, product_id, cart_item_id):
    
    product = get_object_or_404(Product, id=product_id)

    try:
        # you will notice we did not use 'cart=cart' here; this is because we are logged in here so we can use the currently logged in user to query the CartItem instead of the cart. In addition, being logged in automatically means you have a Cart without a need to call it.
        if request.user.is_authenticated:
            cart_item = CartItem.objects.get(product=product, user=request.user, id=cart_item_id)

        # here, because we are not logged in, we are required to use 'cart=cart' for querying the CartItem. Since we are not logged in, we do not automatically have a Cart, thus the need to call it in the query.
        else:
            cart = Cart.objects.get(cart_id=_cart_id(request))
            cart_item = CartItem.objects.get(product=product, cart=cart, id=cart_item_id)

        if cart_item.quantity > 1:
            cart_item.quantity -= 1
            cart_item.save()
        else:
            cart_item.delete()

    except:
        pass
    
    return redirect('cart')



# The 'remove_cart_item' function is used to remove a specific cart item(the entire product and not just the quantity) from the cart:
def remove_cart_item(request, product_id, cart_item_id):
    product = get_object_or_404(Product, id=product_id)

    if request.user.is_authenticated:
        cart_item = CartItem.objects.get(product=product, user=request.user, id=cart_item_id)

    else:
        cart = Cart.objects.get(cart_id=_cart_id(request))
        cart_item = CartItem.objects.get(product=product, cart=cart, id=cart_item_id)

    cart_item.delete()
    
    return redirect('cart')



# This 'cart' function is used to display the cart items and their total price in the cart:
# It first retrieves the cart object using the cart ID from the session. 
# '_cart_id(request)' is a function retrieved/created above to retrieve and store the 'session_key'
# *Then it retrieves the cart items from the database* 
# Thereafter, it calculates the total price and quantity of items in the cart.
def cart(request, total=0, quantity=0, cart_items=None):

    try:

        tax = 0  # Initialize tax here
        grand_total = 0  # Initialize grand_total here

        if request.user.is_authenticated:
            cart_items = CartItem.objects.filter(user=request.user, is_active=True)
        else:
            cart = Cart.objects.get(cart_id=_cart_id(request))

            # The 'cart_items' variable retrieves all the cart items associated with the cart
            # - The 'is_active=True' condition ensures that only active items are retrieved. That is, items that are still in the cart and not marked as inactive.
            # - The 'cart_items' variable is a queryset that contains all the cart items associated with the cart
            cart_items = CartItem.objects.filter(cart=cart, is_active=True)
            
        for cart_item in cart_items:
            total += (cart_item.product.price * cart_item.quantity)
            quantity += cart_item.quantity

        tax = (total * 0.02) # '0.02' is the tax rate used here(2/100)
        grand_total = total + tax
    except Cart.DoesNotExist:
        pass #just ignore
    
    context = {
        'total': total,
        'quantity': quantity,
        'cart_items': cart_items,
        'tax': tax,
        'grand_total': grand_total,
    }

    return render(request, 'stores/cart.html', context)


@login_required(login_url='login')
def checkout(request, total=0, quantity=0, cart_items=None):

    # copy the 'try' and 'except' block in function - 'cart' above
    try:

        tax = 0  # Initialize tax here
        grand_total = 0  # Initialize grand_total here

        if request.user.is_authenticated:
            cart_items = CartItem.objects.filter(user=request.user, is_active=True)
        else:
            cart = Cart.objects.get(cart_id=_cart_id(request))

            # The 'cart_items' variable retrieves all the cart items associated with the cart
            # - The 'is_active=True' condition ensures that only active items are retrieved. That is, items that are still in the cart and not marked as inactive.
            # - The 'cart_items' variable is a queryset that contains all the cart items associated with the cart
            cart_items = CartItem.objects.filter(cart=cart, is_active=True)
        for cart_item in cart_items:
            total += (cart_item.product.price * cart_item.quantity)
            quantity += cart_item.quantity

        tax = (total * 0.02) # '0.02' is the tax rate used here(2/100)
        grand_total = total + tax
    except Cart.DoesNotExist:
        pass #just ignore
    
    context = {
        'total': total,
        'quantity': quantity,
        'cart_items': cart_items,
        'tax': tax,
        'grand_total': grand_total,
    }

    return render(request, 'stores/checkout.html', context)



