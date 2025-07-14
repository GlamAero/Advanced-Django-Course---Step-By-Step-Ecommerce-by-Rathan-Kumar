from django.shortcuts import render, get_object_or_404
from django.views.generic import ListView, DetailView
from django.db import models  # Added missing import
from .models import Category
from store.models import Product
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Count, Q
from django.core.cache import cache

class CategoryListView(ListView):
    model = Category
    template_name = 'category/category_list.html'
    context_object_name = 'categories'
    
    def get_queryset(self):
        cache_key = 'all_active_categories'
        categories = cache.get(cache_key)
        
        if not categories:
            categories = Category.objects.filter(
                is_active=True, 
                parent__isnull=True
            ).annotate(
                product_count=Count('products', filter=Q(products__is_available=True))
            ).order_by('-featured', 'category_name')
            cache.set(cache_key, categories, 3600)  # Cache for 1 hour
        
        return categories

class CategoryDetailView(DetailView):
    model = Category
    template_name = 'category/category_detail.html'
    context_object_name = 'category'
    slug_url_kwarg = 'category_slug'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        category = self.object
        
        # Get products with prefetching and filtering
        products = Product.objects.filter(
            category=category,  # Changed to singular 'category'
            is_available=True
        ).prefetch_related(
            'images', 
            'variation_combinations'
        ).select_related(
            'vendor'
        ).annotate(
            min_price=models.Min('variation_combinations__price'),
            max_price=models.Max('variation_combinations__price')
        ).order_by('-created_date')
        
        # Pagination
        paginator = Paginator(products, 24)  # 24 products per page
        page = self.request.GET.get('page')
        try:
            products = paginator.page(page)
        except PageNotAnInteger:
            products = paginator.page(1)
        except EmptyPage:
            products = paginator.page(paginator.num_pages)
        
        context['products'] = products
        context['subcategories'] = category.get_children().filter(is_active=True)
        context['breadcrumbs'] = self.get_breadcrumbs(category)
        return context
    
    def get_breadcrumbs(self, category):
        breadcrumbs = []
        for ancestor in category.get_ancestors(include_self=True):
            breadcrumbs.append({
                'name': ancestor.category_name,
                'url': ancestor.get_absolute_url()
            })
        return breadcrumbs

def category_navigation(request):
    """AJAX endpoint for dynamic category navigation"""
    category_slug = request.GET.get('category')
    
    if category_slug:
        category = get_object_or_404(Category, slug=category_slug)
        subcategories = category.get_children().filter(is_active=True)
    else:
        subcategories = Category.objects.filter(
            parent__isnull=True, 
            is_active=True
        )
    
    return render(request, 'category/_category_navigation.html', {
        'subcategories': subcategories
    })