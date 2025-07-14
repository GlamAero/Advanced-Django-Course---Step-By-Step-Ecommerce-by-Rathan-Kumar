# coupons/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Count
from .models import Coupon

@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = (
        'code', 'discount_type', 'discount_value', 'active', 
        'valid_until', 'use_count', 'applies_to'
    )
    list_filter = ('active', 'discount_type', 'applies_to', 'valid_to')
    search_fields = ('code', 'description')
    filter_horizontal = ('products', 'categories', 'users_used')
    readonly_fields = ('use_count', 'created_at', 'updated_at')
    date_hierarchy = 'valid_to'
    fieldsets = (
        (None, {
            'fields': ('code', 'description', 'active', 'single_use')
        }),
        ('Discount Settings', {
            'fields': ('discount_type', 'discount', 'max_discount', 'min_purchase')
        }),
        ('Application Rules', {
            'fields': ('applies_to', 'products', 'categories')
        }),
        ('Validity Period', {
            'fields': ('valid_from', 'valid_to')
        }),
        ('Usage Tracking', {
            'fields': ('users_used', 'use_count')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def discount_value(self, obj):
        if obj.discount_type == 'percentage':
            return f"{obj.discount}%"
        return f"${obj.discount}"
    discount_value.short_description = 'Discount'
    
    def valid_until(self, obj):
        return obj.valid_to.strftime("%Y-%m-%d")
    valid_until.admin_order_field = 'valid_to'
    valid_until.short_description = 'Valid Until'
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(usage_count=Count('users_used'))
    
    def use_count(self, obj):
        return obj.usage_count
    use_count.admin_order_field = 'usage_count'
    use_count.short_description = 'Uses'
