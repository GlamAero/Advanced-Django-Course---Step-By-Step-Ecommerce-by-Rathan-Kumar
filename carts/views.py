from django.shortcuts import render, redirect, get_object_or_404
from store.models import Product, Variation
from .models import Cart, CartItem
from django.http import HttpResponse


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

    #--------------------------PRODUCT--------------------------#
    product = get_object_or_404(Product, id=product_id)


    #------------------- FOR PRODUCT VARIATION:------------------#

    # to get a list of product variations, meaning a list of products and their corresponding variations:
    product_variation = []

    if request.method == 'POST':

        # 'key' is got from the 'product_details.html' file, in the 'select' area. 
        # 'item' is the name given to the 'select' element in our 'product_detail.html' page.
        # 'request.POST' is the dictionary containing the options we selected in 'product_detail.html' page.
        # Thus 'item' is like 'color' or 'size' while 'request.POST[item] is like 'blue' for color or 'medium' for size
        for item in request.POST:
            # If the 'color' is 'blue', 'color' is the 'item' and will be saved as 'key'
            # Similarly if the 'size' is 'medium', 'size' is the 'item' and will be saved as 'key'  
            key = item

            # Then 'blue' being 'request.POST[key]' will be saved as 'value'
            # Similarly, in the case of 'size', 'size' being 'request.POST[key]' will be saved as 'value'
            value = request.POST[key]
            
            # get the 'variation' where the key and value chosen by the user corresponds with the values in the 'models.py file
            # 'iexact' means to ignore whether the inputed value is capital or small letter.
            try:
                variation = Variation.objects.get(product=product, variation_category__iexact=key, variation_value__iexact=value)
                
                # here we append the variations to the 'product_variation' we created above:
                product_variation.append(variation)
            except:
                pass

    
    # --------------------------- CART-------------------------#
    try:
        cart = Cart.objects.get(cart_id=_cart_id(request))
    except Cart.DoesNotExist:
        cart = Cart.objects.create(cart_id=_cart_id(request))
    cart.save()


    #------------------------CART_ITEM--------------------------#

    # get all the items of the product in the cart, after being added to cart. This is taken from the database(models.py file)
    is_cart_item_exists = CartItem.objects.filter(product=product, cart=cart).exists()

    # check if cart_item exists:
    if is_cart_item_exists:
        cart_item = CartItem.objects.filter(product=product, cart=cart) 

        # Existing variations -> Database
        # Current variations = product_variation
        # Item ID

        ex_var_list = []
        id = []

        # from the above, 'cart_item' is the instance of the product model added to cart e.g 'Air Jordan boots'. 
        # And 'item' is a single CartItem(single product variation) of that particular product e.g 'Air Jordan boot of size 10 and color black'
        for item in cart_item:# 'item'  e.g  in the cart/database

            # the existing item with all its variation(s) that has been added to cart when we previously added to cart:
            existing_variation = item.variations.all()
            ex_var_list.append(list(existing_variation))

            id.append(item.id)

        # print(ex_var_list)

        # if the variation of the product chosen by the user is already in the existing product variation in the cart/database:
        if product_variation in ex_var_list:

            # increase the cart_item quantity:

            # first, get the index value of the 'product_variation' in the 'ex_var_list'
            index = ex_var_list.index(product_variation)

            # then, get the id of the index value of the 'product_variation' in the 'ex_var_list'
            item_id = id[index]

            item = CartItem.objects.get(product=product, id=item_id)
            item.quantity += 1
            item.save()

        else:
            # create a new cart item:
            item = CartItem.objects.create(product=product, quantity=1, cart=cart)

            
            # adding the variation above to the cart_item:
            if len(product_variation) > 0: # this is the same as: 'if product_variation.exists:'

                # before adding an item to cart alongside its variations, remove the connection between the (old)'item' in the previous 'add to cart' and its associated variations in the ManyToManyField. But do not delete the actual variation objects from the database. This way a new set of variation can be added to the same item:
                item.variations.clear()

                # add a new set of variations to the item selected:
                item.variations.add(*product_variation)
            item.save()
        
    else:
        # if the product does not exist at all in the CartItem section of the database:
        cart_item = CartItem.objects.create(
            product=product,
            quantity=1,
            cart=cart,
        )

        # adding the variation above to the cart_item:
        if len(product_variation) > 0:  # this is the same as: 'if product_variation.exists:'

            # before adding an item to cart alongside its variations, remove the connection between the 'item' existing in the cart and its associated variations in the ManyToManyField. But do not delete the actual variation objects from the database. This way a new set of variation can be added to the item:
            cart_item.variations.clear()

            cart_item.variations.add(*product_variation)

        cart_item.save()

    return redirect('cart')



# The 'remove_cart' function is used to remove a product quantity or a product(if the quantity is originally less or equal to 1) from the cart:
def remove_cart(request, product_id, cart_item_id):
    cart = Cart.objects.get(cart_id=_cart_id(request))
    product = get_object_or_404(Product, id=product_id)

    try:
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
    cart = Cart.objects.get(cart_id=_cart_id(request))
    product = get_object_or_404(Product, id=product_id)
    cart_item = CartItem.objects.get(product=product, cart=cart, id=cart_item_id)
    cart_item.delete()
    
    return redirect('cart')



# This 'cart' function is used to display the cart items and their total price in the cart:
# It first retrieves the cart with the cart ID from the session.
# *Then it retrieves the cart items from the database* 
# Thereafter, it calculates the total price and quantity of items in the cart.
def cart(request, total=0, quantity=0, cart_items=None):
    try:
        cart = Cart.objects.get(cart_id=_cart_id(request))

        # The 'cart_items' variable retrieves all the cart items associated with the cart
        # - The 'is_active=True' condition ensures that only active items are retrieved. That is, items that are still in the cart and not marked as inactive.
        # - The 'cart_items' variable is a queryset that contains all the cart items associated with the cart
        cart_items = CartItem.objects.filter(cart=cart, is_active=True)
        for cart_item in cart_items:
            total += (cart_item.product.price * cart_item.quantity)
            quantity += cart_item.quantity

        tax = (total * 0.02) # '0.02' is the tax rate(2/100)
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

