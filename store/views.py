from django.shortcuts import render, get_object_or_404
from store.models import Product
from category.models import Category
from carts.models import CartItem
from carts.views import _cart_id
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q


# Create your views here.
def store(request, category_slug=None):
    categories = None
    products = None
    if category_slug != None:
        # If a category slug is provided, filter products by that category
        categories = get_object_or_404(Category, slug=category_slug)
        products = Product.objects.filter(category=categories, is_available=True)

        # '6' is the number of products to display per page
        # 'page' is the current page number

        # Paginate products, 1 per page
        paginator = Paginator(products, 1)

        # Get the requested page number from the URL
        page = request.GET.get('page')

        # Get products for that page
        paged_products = paginator.get_page(page)

        # Get the count of products
        product_count = products.count()

    else:
        # If no category slug is provided, get all available products 
        products = Product.objects.filter(is_available=True).order_by('id')


        # '3' is the number of products to display per page
        # 'page' is the current page number

        # Paginate products, 3 per page
        paginator = Paginator(products, 3)

        # Get the requested page number from the URL
        page = request.GET.get('page')

        # Get products for that page
        paged_products = paginator.get_page(page)
    
        # Get the count of products
        product_count = products.count()
    

    context = {
        'products': paged_products,
        'product_count': product_count,
    }
    return render(request, 'stores/store.html', context)


def product_detail(request, category_slug, product_slug):
    try:
        # Get the product by its slug and category
        single_product = Product.objects.get(category__slug=category_slug, slug=product_slug)

        # checking if the product is in the cart
        # 'exists()' returns True if the product is in the cart, otherwise False
        in_cart = CartItem.objects.filter(cart__cart_id=_cart_id(request), product=single_product).exists()

    except Exception as e:
        raise e

    context = {
        'single_product': single_product,
        'in_cart': in_cart,
    }
    return render(request, 'stores/product_detail.html', context)
    

def search(request):
    # 'keyword' is the key of the search value entered by the user
    # 'request.GET' is a dictionary-like object containing the GET parameters(key-value pairs) of the request in the searchbar. This request is made when the user submits the search form with information to be searched for. This information is passed to the view function as a GET request.
    # 'request.GET.get('keyword')' retrieves the 'value' of the 'keyword' parameter(key) from the GET request. 
    if 'keyword' in request.GET:
        keyword = request.GET['keyword']
        if keyword:
            # If a keyword is provided, filter products by that keyword
            products = Product.objects.order_by('-created_date').filter(Q(description__icontains=keyword) | Q(product_name__icontains=keyword))
            
            product_count = products.count()

        context = {
            'products': products,
            'product_count': product_count,
        }
    return render(request, 'stores/store.html', context)





