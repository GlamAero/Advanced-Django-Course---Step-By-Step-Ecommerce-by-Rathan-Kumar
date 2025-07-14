from django.contrib import admin
from django.utils.html import format_html
from .models import Wishlist, WishlistItem

class WishlistItemInline(admin.TabularInline):
    model = WishlistItem
    extra = 0
    readonly_fields = ('added_at', 'product_link')
    fields = ('product_link', 'added_at')
    
    def product_link(self, obj):
        url = reverse("admin:store_product_change", args=[obj.product.id])
        return format_html('<a href="{}">{}</a>', url, obj.product)
    product_link.short_description = 'Product'

@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    list_display = ('user', 'item_count', 'created_at', 'updated_at')
    search_fields = ('user__email', 'user__username')
    readonly_fields = ('created_at', 'updated_at', 'item_count')
    list_filter = ('created_at', 'updated_at')
    inlines = [WishlistItemInline]
    
    def item_count(self, obj):
        return obj.item_count
    item_count.short_description = 'Items'

@admin.register(WishlistItem)
class WishlistItemAdmin(admin.ModelAdmin):
    list_display = ('wishlist', 'product', 'added_at')
    search_fields = (
        'wishlist__user__email', 
        'product__product_name',
        'product__sku'
    )
    list_filter = ('added_at',)
    autocomplete_fields = ('wishlist', 'product')
    readonly_fields = ('added_at',)
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'wishlist__user', 
            'product'
        )
    

