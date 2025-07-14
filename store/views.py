from django.shortcuts import render, get_object_or_404
from store.models import Product, VariationCombination
from category.models import Category
from carts.models import CartItem
from carts.views import _cart_id
from django.core.paginator import Paginator
from django.db.models import Q

# Only show single products (no variations or combinations) in the store listing
def store(request, category_slug=None):
    categories = None
    products = None
    if category_slug:
        categories = get_object_or_404(Category, slug=category_slug)
        products = Product.objects.filter(category=categories, is_available=True)
    else:
        products = Product.objects.filter(is_available=True).order_by('id')

    # Exclude products that are only variation combinations
    # (Assumes VariationCombination is not shown in Product table)
    paginator = Paginator(products, 6 if not category_slug else 6)
    page = request.GET.get('page')
    paged_products = paginator.get_page(page)
    product_count = products.count()

    context = {
        'products': paged_products,
        'product_count': product_count,
    }
    return render(request, 'stores/store.html', context)

def product_detail(request, category_slug, product_slug):
    try:
        single_product = Product.objects.get(category__slug=category_slug, slug=product_slug)
        in_cart = CartItem.objects.filter(cart__cart_id=_cart_id(request), product=single_product).exists()

        # Get variations and variation combinations for this product
        variations = single_product.variation_set.filter(is_active=True)
        variation_combinations = VariationCombination.objects.filter(product=single_product, is_active=True)

        # Get unique variation categories for template use
        variation_categories = variations.values_list('variation_category', flat=True).distinct()

    except Product.DoesNotExist:
        single_product = None
        in_cart = False
        variations = []
        variation_combinations = []
        variation_categories = []

    context = {
        'single_product': single_product,
        'in_cart': in_cart,
        'variations': variations,
        'variation_combinations': variation_combinations,
        'variation_categories': variation_categories,
    }
    return render(request, 'stores/product_detail.html', context)

def search(request):
    context = {}
    if 'keyword' in request.GET:
        keyword = request.GET['keyword']
        if keyword:
            products = Product.objects.order_by('-created_date').filter(
                Q(description__icontains=keyword) | Q(product_name__icontains=keyword),
                is_available=True
            )
            product_count = products.count()
            context = {
                'products': products,
                'product_count': product_count,
            }
    return render(request, 'stores/store.html', context)