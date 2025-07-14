from django.contrib import admin
from django.utils.html import format_html, mark_safe
from django.urls import reverse
from django.http import HttpResponseRedirect
from django.db.models import Sum

from . import actions, filters
from .inlines import VariationInline, VariationCombinationInline
from .forms import ProductAdminForm
from store.models import Product

# @admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    form = ProductAdminForm
    prepopulated_fields = {'slug': ('product_name',)}
    list_display = (
        'product_name', 
        'vendor', 
        'category',
        'product_type',
        'colored_stock',
        'is_available',
        'created_date'
    )
    list_filter = ('is_available', 'product_type', filters.LowStockFilter, filters.VendorFilter)
    search_fields = ('product_name', 'vendor__company_name', 'category__category_name')
    actions = [actions.reset_stock, actions.bulk_create_combinations]
    readonly_fields = ('created_date', 'modified_date')
    
    fieldsets = (
        (None, {
            'fields': (
                'vendor', 'product_name', 'slug', 'category', 
                'product_type', 'description', 'images', 
                'is_available'
            )
        }),
        ('Pricing & Stock', {
            'fields': ('price', 'stock')
        }),
        ('Dates', {
            'fields': ('created_date', 'modified_date'),
            'classes': ('collapse',)
        }),
    )
    
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.request = request
        return form

    def get_inlines(self, request, obj=None):
        if not obj:
            return []
        if obj.product_type == 'variation':
            return [VariationInline]
        elif obj.product_type == 'combination':
            return [VariationCombinationInline]
        return []

    def colored_stock(self, obj):
        stock = obj.stock or 0
        color = 'green' if stock > 10 else 'orange' if stock > 5 else 'red'
        return format_html(
            '<strong style="color:{};">{}</strong>', 
            color, stock
        )
    colored_stock.short_description = 'Stock'
    colored_stock.admin_order_field = 'stock'

    def save_model(self, request, obj, form, change):
        if not change and request.user.is_vendor():
            obj.vendor = request.user.vendorprofile
        super().save_model(request, obj, form, change)


        