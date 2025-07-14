from django.contrib import admin
from .models import Order, Payment, OrderProduct

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("order_number", "user", "status", "order_total", "is_ordered", "created_at")
    list_filter = ("status", "is_ordered", "created_at")
    search_fields = ("order_number", "user__email", "user__username", "email")

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("transaction_id", "user", "payment_method", "order_total", "amount_paid", "status", "created_at")
    list_filter = ("status", "payment_method", "created_at")
    search_fields = ("transaction_id", "paypal_order_id", "user__email", "user__username")

@admin.register(OrderProduct)
class OrderProductAdmin(admin.ModelAdmin):
    list_display = ("order", "product", "user", "quantity", "product_price", "ordered", "created_at")
    list_filter = ("ordered", "created_at")
    search_fields = ("order__order_number", "product__product_name", "user__email", "user__username")