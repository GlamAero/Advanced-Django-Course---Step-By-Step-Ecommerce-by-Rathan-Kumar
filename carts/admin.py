from django.contrib import admin
from .models import Cart, CartItem

class CartAdmin(admin.ModelAdmin):
    list_display = ('cart_id', 'date_added', 'user', 'is_active')
    list_filter = ('date_added', 'is_active')
    search_fields = ('cart_id', 'user__email')
    date_hierarchy = 'date_added'
    readonly_fields = ('date_added',)

    def user(self, obj):
        return obj.user.email if obj.user else "Anonymous"
    user.short_description = 'User'

class CartItemAdmin(admin.ModelAdmin):
    list_display = ('product', 'cart', 'user', 'quantity', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('product__product_name', 'user__email')
    autocomplete_fields = ('product', 'variations')
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at', 'updated_at')
    
    def user(self, obj):
        return obj.user.email if obj.user else "Anonymous"
    user.short_description = 'User'

admin.site.register(Cart, CartAdmin)
admin.site.register(CartItem, CartItemAdmin)