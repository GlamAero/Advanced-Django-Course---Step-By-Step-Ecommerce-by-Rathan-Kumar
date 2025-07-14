from django.core.cache import cache
from .models import Category

def menu_links(request):
    # Cache categories for 1 hour to reduce database queries
    cache_key = 'all_categories_menu'
    links = cache.get(cache_key)
    
    if not links:
        links = Category.objects.filter(
            is_active=True
        ).prefetch_related(
            'subcategories'
        ).order_by(
            'tree_id', 'lft'
        )
        cache.set(cache_key, links, 3600)  # 1 hour cache
    
    return {'categories': links}

