from django.contrib import admin
from .models import Payment, Order, OrderProduct


# Register your models here.

# To know which OrderProduct belong to a particular Order and this is seen in the Order table of the admin page. In other words, it associates each OrderProduct to the Order which birth it in the Order table of the admin section.
class OrderProductInline(admin.TabularInline):
    model = OrderProduct
    readonly_fields = ['payment', 'user', 'product', 'quantity', 'product_price', 'ordered', 'variations']
    extra = 0  # '0' means no extra spaces


class OrderAdmin(admin.ModelAdmin):
    list_display = ['order_number', 'full_name', 'phone', 'email', 'city', 'order_total', 'tax', 'status', 'is_ordered', 'created_at']
    list_filter = ['status', 'is_ordered']
    search_fields = ['order_number', 'first_name', 'last_name', 'phone', 'email']
    list_per_page = 20
    inlines = [OrderProductInline]


admin.site.register(Payment)
admin.site.register(Order, OrderAdmin)
admin.site.register(OrderProduct)
