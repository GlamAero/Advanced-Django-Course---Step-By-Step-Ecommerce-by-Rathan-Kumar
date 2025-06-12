# Import needed modules and functions from Django and your own apps
from django.shortcuts import render, get_object_or_404
from django.db.models import Q
from django.http import HttpRequest, HttpResponse
from django.urls import reverse
from django.utils.html import escape

# Import models and utilities
from vendor.models import Product
from category.models import Category
from carts.models import CartItem
from carts.views import _cart_id
from utils.pagination import paginate_queryset


# Store page - shows all products or products in a specific category
def store(request: HttpRequest, category_slug: str = None) -> HttpResponse:
    """
    Shows the store page with all products or products filtered by category.
    Adds pagination, breadcrumb navigation, and SEO metadata.
    """
    # Start breadcrumb with home and store links
    breadcrumb = [
        {'name': 'Home', 'url': '/'},
        {'name': 'Store', 'url': reverse('store')},
    ]

    if category_slug:
        # If a category is selected, get it or show 404 if not found
        category = get_object_or_404(Category, slug=category_slug)
        # Filter products under this category
        products = Product.objects.filter(category=category, is_available=True)
        items_per_page = 1  # Set number of products per page
        # Add category to breadcrumb
        breadcrumb.append({'name': category.category_name, 'url': category.get_url()})
        # Set SEO info
        page_title = f"{category.category_name} - Store"
        meta_description = f"Browse products in {category.category_name}"
    else:
        # If no category, show all available products
        products = Product.objects.filter(is_available=True).order_by('id')
        items_per_page = 3
        # Set SEO info
        page_title = "Browse All Products - Store"
        meta_description = "Shop all available products in our store."

    # Apply pagination
    paged_products, current_page = paginate_queryset(request, products, per_page=items_per_page)

    # Pass data to template
    context = {
        'products': paged_products,
        'product_count': products.count(),
        'breadcrumb': breadcrumb,
        'page_title': page_title,
        'meta_description': meta_description,
        'canonical_url': request.build_absolute_uri(),  # Full URL for SEO
    }

    # Render the store page
    return render(request, 'stores/store.html', context)


# Product detail page - shows info about a single product
def product_detail(request: HttpRequest, category_slug: str, product_slug: str) -> HttpResponse:
    """
    Shows details for a single product including its variations and cart status.
    Adds breadcrumb, SEO metadata, and structured data for search engines.
    """
    # Get the product and related variations or show 404 if not found
    product = get_object_or_404(
        Product.objects.prefetch_related('variations'),
        slug=product_slug,
        category__slug=category_slug
    )

    # Get all product variations (like size, color)
    variations = product.variations.all()

    # Check if this product is already in the user's cart
    in_cart = CartItem.objects.filter(cart__cart_id=_cart_id(request), product=product).exists()

    # Create breadcrumb for product detail page
    breadcrumb = [
        {'name': 'Home', 'url': '/'},
        {'name': 'Store', 'url': reverse('store')},
        {'name': product.category.category_name, 'url': product.category.get_url()},
        {'name': product.product_name, 'url': product.get_url()},
    ]

    # SEO metadata
    page_title = product.product_name
    meta_description = escape(product.description[:160]) if product.description else "Buy high-quality products online."

    # Structured data for better SEO (shown in Google search results)
    structured_data = {
        "@context": "https://schema.org/",
        "@type": "Product",
        "name": product.product_name,
        "image": [request.build_absolute_uri(product.image.url)] if product.image else [],
        "description": product.description,
        "sku": str(product.id),
        "brand": {"@type": "Brand", "name": "YourBrand"},
        "offers": {
            "@type": "Offer",
            "url": request.build_absolute_uri(),
            "priceCurrency": "USD",
            "price": str(product.price),
            "availability": "https://schema.org/InStock" if product.stock > 0 else "https://schema.org/OutOfStock"
        }
    }

    # Pass data to template
    context = {
        'product': product,
        'variations': variations,
        'in_cart': in_cart,
        'breadcrumb': breadcrumb,
        'page_title': page_title,
        'meta_description': meta_description,
        'canonical_url': request.build_absolute_uri(),
        'structured_data': structured_data,
    }

    # Render the product detail page
    return render(request, 'store/product_detail.html', context)


# Search page - filters products based on a keyword
def search(request: HttpRequest) -> HttpResponse:
    """
    Searches products by keyword and shows the results.
    Includes breadcrumb and SEO support.
    """
    keyword = request.GET.get('keyword')

    # Start breadcrumb for search
    breadcrumb = [
        {'name': 'Home', 'url': '/'},
        {'name': 'Search Results', 'url': '#'}
    ]

    # Default empty values
    products = Product.objects.none()
    product_count = 0

    if keyword:
        # Filter products by name or description
        products = Product.objects.filter(
            Q(description__icontains=keyword) |
            Q(product_name__icontains=keyword)
        ).order_by('-date_stock_created')
        product_count = products.count()

    # Pass data to template
    context = {
        'products': products,
        'product_count': product_count,
        'breadcrumb': breadcrumb,
        'page_title': f"Search results for '{keyword}'" if keyword else "Search",
        'meta_description': f"Results for {keyword}" if keyword else "Search our store.",
        'canonical_url': request.build_absolute_uri(),
    }

    # Render search results using the same store template
    return render(request, 'stores/store.html', context)
