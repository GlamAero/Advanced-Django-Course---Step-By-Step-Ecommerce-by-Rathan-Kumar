from django.shortcuts import render, get_object_or_404
from store.models import Product
from category.models import Category

# Create your views here.
def store(request, category_slug=None):
    categories = None
    products = None
    if category_slug != None:
        # If a category slug is provided, filter products by that category
        categories = get_object_or_404(Category, slug=category_slug)
        products = Product.objects.filter(category=categories, is_available=True)

        # Get the count of products
        product_count = products.count()

    else:
        # If no category slug is provided, get all available products 
        products = Product.objects.all().filter(is_available=True)
    
        # Get the count of products
        product_count = products.count()
    

    context = {
        'products': products,
        'product_count': product_count,
    }
    return render(request, 'stores/store.html', context)


def product_detail(request, category_slug, product_slug):
    try:
        # Get the product by its slug and category
        single_product = Product.objects.get(category__slug=category_slug, slug=product_slug)
    except Exception as e:
        raise e

    context = {
        'single_product': single_product,
    }
    return render(request, 'stores/product_detail.html', context)
    
