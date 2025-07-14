from django.shortcuts import render
from django.utils import timezone
from store.models import Product
from category.models import Category
from django.db.models import Prefetch, Min, Max, Count
from django.core.cache import cache

def home(request):
    # Cache key
    cache_key = f"home_page_data_{request.LANGUAGE_CODE}"
    
    # Try to get cached data
    context = cache.get(cache_key)
    
    if not context:
        # Featured categories
        featured_categories = Category.objects.filter(
            featured=True, 
            is_active=True
        ).prefetch_related('products')[:8]
        
        # New arrivals
        new_arrivals = Product.objects.filter(
            is_available=True,
            created_at__gte=timezone.now() - timezone.timedelta(days=30)
        ).select_related('vendor').prefetch_related(
            Prefetch('images', to_attr='main_image')
        ).order_by('-created_at')[:12]
        
        # Best sellers
        best_sellers = Product.objects.filter(
            is_available=True
        ).annotate(
            order_count=Count('order_products')
        ).order_by('-order_count')[:12]
        
        # On sale
        on_sale = Product.objects.filter(
            is_available=True,
            discounted_price__isnull=False
        ).order_by('-discounted_price')[:12]
        
        # Build context
        context = {
            'featured_categories': featured_categories,
            'new_arrivals': new_arrivals,
            'best_sellers': best_sellers,
            'on_sale': on_sale,
        }
        
        # Cache for 1 hour
        cache.set(cache_key, context, 3600)
    
    return render(request, 'home.html', context)


