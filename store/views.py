from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q, Sum, Case, When, Value, IntegerField
from django.http import HttpResponse, JsonResponse, HttpResponseForbidden
from django.contrib.auth.decorators import login_required
from accounts.decorators import vendor_required, customer_required
from django.utils import timezone
from django.template.loader import render_to_string
from django.db.models.functions import Coalesce
from django.views.decorators.cache import cache_page

from store.models import Product, VariationCombination, Category
from carts.models import CartItem
from carts.views import _cart_id
from orders.models import Order
from wishlist.models import Wishlist
from weasyprint import HTML

# -------------------------
# STORE LISTING & PRODUCT VIEWS
# -------------------------

@cache_page(60 * 15)  # Cache for 15 minutes
def store(request, category_slug=None):
    # Base queryset with optimized select_related
    products = Product.objects.filter(
        is_available=True
    ).select_related('category', 'vendor__user')
    
    # Apply category filter if provided
    if category_slug:
        category = get_object_or_404(Category, slug=category_slug)
        products = products.filter(category=category)
        
        # Also include subcategories
        subcategories = category.get_descendants(include_self=True)
        products = products.filter(category__in=subcategories)

    # Optimized stock filtering using conditional expressions
    products = products.annotate(
        total_stock=Case(
            When(product_type='simple', then='stock'),
            When(product_type='variation', then='stock'),
            When(product_type='combination', then=Coalesce(
                Sum('variation_combinations__stock'), Value(0)
            )),
            default=Value(0),
            output_field=IntegerField()
        )
    ).filter(total_stock__gt=0).order_by('-created_date')

    # Pagination with error handling
    paginator = Paginator(products, 12)
    page = request.GET.get('page')
    
    try:
        paged_products = paginator.page(page)
    except PageNotAnInteger:
        paged_products = paginator.page(1)
    except EmptyPage:
        paged_products = paginator.page(paginator.num_pages)

    context = {
        'products': paged_products,
        'product_count': paginator.count,
        'current_category': category if category_slug else None,
    }
    return render(request, 'store/store.html', context)


def product_detail(request, category_slug, product_slug):
    # Optimized query with prefetch_related
    product = get_object_or_404(
        Product.objects.prefetch_related(
            'variations', 
            'variation_combinations__variations'
        ),
        category__slug=category_slug, 
        slug=product_slug,
        is_available=True
    )
    
    # Check if product is in cart
    in_cart = CartItem.objects.filter(
        cart__cart_id=_cart_id(request), 
        product=product
    ).exists()
    
    # Check if product is in wishlist for authenticated users
    in_wishlist = False
    if request.user.is_authenticated:
        in_wishlist = Wishlist.objects.filter(
            user=request.user, 
            product=product
        ).exists()

    # Prepare variation data
    variations = product.variations.filter(is_active=True)
    variation_categories = sorted({v.variation_type.strip().capitalize() for v in variations})
    
    # Prepare combination data
    variation_combinations = product.variation_combinations.filter(
        is_active=True
    ).prefetch_related('variations')

    context = {
        'single_product': product,
        'in_cart': in_cart,
        'in_wishlist': in_wishlist,
        'variations': variations,
        'variation_categories': variation_categories,
        'variation_combinations': variation_combinations,
    }
    return render(request, 'store/product_detail.html', context)


# -------------------------
# PRODUCT SEARCH
# -------------------------

def search(request):
    keyword = request.GET.get('keyword', '').strip()
    products = Product.objects.none()
    
    if keyword:
        # Create search vector with weights
        products = Product.objects.annotate(
            total_stock=Case(
                When(product_type='simple', then='stock'),
                When(product_type='variation', then='stock'),
                When(product_type='combination', then=Coalesce(
                    Sum('variation_combinations__stock'), Value(0)
                )),
                default=Value(0),
                output_field=IntegerField()
            )
        ).filter(
            Q(product_name__icontains=keyword) | 
            Q(description__icontains=keyword) |
            Q(vendor__company_name__icontains=keyword) |
            Q(category__category_name__icontains=keyword),
            is_available=True,
            total_stock__gt=0
        ).order_by('-created_date').select_related('vendor', 'category')

    # Paginate results
    paginator = Paginator(products, 12)
    page = request.GET.get('page')
    
    try:
        paged_products = paginator.page(page)
    except PageNotAnInteger:
        paged_products = paginator.page(1)
    except EmptyPage:
        paged_products = paginator.page(paginator.num_pages)

    context = {
        'products': paged_products,
        'product_count': paginator.count,
        'keyword': keyword
    }
    return render(request, 'store/store.html', context)


# -------------------------
# VENDOR PRODUCTS
# -------------------------

@vendor_required
def vendor_products(request):
    vendor = request.user.vendorprofile
    products = Product.objects.filter(vendor=vendor).select_related(
        'category'
    ).prefetch_related(
        'variations', 
        'variation_combinations'
    ).order_by('-created_date')
    
    # Add stock annotation
    products = products.annotate(
        total_stock=Case(
            When(product_type='simple', then='stock'),
            When(product_type='variation', then='stock'),
            When(product_type='combination', then=Coalesce(
                Sum('variation_combinations__stock'), Value(0)
            )),
            default=Value(0),
            output_field=IntegerField()
        )
    )
    
    return render(request, 'store/vendor_products.html', {
        'products': products
    })


# -------------------------
# PDF DOWNLOAD FOR COMBOS
# -------------------------

@vendor_required
def download_combo_summary(request, product_id):
    product = get_object_or_404(
        Product.objects.prefetch_related('variation_combinations__variations'), 
        id=product_id
    )
    
    # Validate vendor ownership
    if product.vendor != request.user.vendorprofile:
        return HttpResponseForbidden("You do not have permission to access this product's combinations.")

    combos = product.variation_combinations.filter(is_active=True)

    # Render HTML template
    html = render_to_string('store/pdf/combo_summary.html', {
        'product': product,
        'combos': combos,
        'generated': timezone.now().strftime("%Y-%m-%d %H:%M")
    })

    # Generate PDF
    pdf_file = HTML(string=html).write_pdf()

    # Create HTTP response
    response = HttpResponse(pdf_file, content_type="application/pdf")
    response['Content-Disposition'] = f'attachment; filename="{product.slug}_combinations.pdf"'
    return response


# -------------------------
# AJAX COMBO LOOKUP
# -------------------------

def combo_info(request):
    product_id = request.GET.get('product_id')
    variation_params = request.GET.dict()
    
    # Remove non-variation parameters
    variation_params.pop('product_id', None)
    variation_params.pop('csrfmiddlewaretoken', None)
    
    if not product_id or not variation_params:
        return JsonResponse({'error': 'Missing parameters'}, status=400)
    
    try:
        product = Product.objects.get(id=product_id)
    except Product.DoesNotExist:
        return JsonResponse({'error': 'Product not found'}, status=404)
    
    # Find matching combination
    combos = product.variation_combinations.filter(
        is_active=True
    ).prefetch_related('variations')
    
    for combo in combos:
        match = True
        for key, value in variation_params.items():
            if not combo.variations.filter(
                variation_type__iexact=key,
                variation_value__iexact=value
            ).exists():
                match = False
                break
        
        if match:
            return JsonResponse({
                'price': str(combo.price),
                'stock': combo.stock,
                'sku': combo.sku,
                'id': combo.id,
            })
    
    # Return default if no match found
    return JsonResponse({
        'price': str(product.price),
        'stock': 0,
        'sku': product.slug,
        'id': product.id,
    })

    