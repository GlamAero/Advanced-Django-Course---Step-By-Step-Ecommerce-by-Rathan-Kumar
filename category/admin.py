from django.contrib import admin
from django.utils.html import format_html
from django.db import models  # Added missing import
from .models import Category

class CategoryAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('category_name',)}
    list_display = ('category_name', 'slug', 'display_image', 'product_count', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('category_name', 'slug')
    list_editable = ('is_active',)
    readonly_fields = ('created_at', 'updated_at', 'product_count')
    fieldsets = (
        (None, {
            'fields': ('category_name', 'slug', 'description', 'is_active', 'featured')
        }),
        ('Image', {
            'fields': ('cat_image', 'display_image'),
            'classes': ('collapse',)
        }),
        ('SEO', {
            'fields': ('meta_title', 'meta_description'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at', 'product_count'),
            'classes': ('collapse',)
        })
    )
    
    def display_image(self, obj):
        if obj.cat_image:
            return format_html(
                '<img src="{}" width="50" height="50" style="object-fit: cover;" />',
                obj.cat_image.url
            )
        return "No Image"
    display_image.short_description = 'Image Preview'
    
    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            product_count=models.Count('products')
        )
    
    def product_count(self, obj):
        return obj.product_count
    product_count.admin_order_field = 'product_count'
    product_count.short_description = '# Products'

admin.site.register(Category, CategoryAdmin)
