from django.contrib import admin
from django.utils.html import format_html
from .models import Order, Payment, OrderItem, Refund, Dispute, VendorPayout, DisputeEvidence

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        "transaction_id", "user", "payment_method", "order_total", 
        "amount_paid", "status", "created_at"
    )
    list_filter = ("status", "payment_method", "created_at")
    search_fields = ("transaction_id", "paypal_order_id", "user__email", "user__username")
    actions = ["mark_payments_completed"]

    @admin.action(description="Mark selected payments as Completed")
    def mark_payments_completed(self, request, queryset):
        updated = queryset.update(status="COMPLETED")
        self.message_user(request, f"{updated} payment(s) marked as COMPLETED.")

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "order_number", "user", "status", "order_total", "is_ordered", "created_at"
    )
    list_filter = ("status", "is_ordered", "created_at")
    search_fields = ("order_number", "user__email", "user__username", "email")
    actions = ["mark_orders_completed", "mark_orders_pending"]

    @admin.action(description="Mark selected orders as Completed (only if payment is COMPLETE)")
    def mark_orders_completed(self, request, queryset):
        updated = 0
        for order in queryset.select_related("payment"):
            if order.payment and order.payment.status == "COMPLETED":
                order.status = "Completed"
                order.is_ordered = True
                order.save()
                updated += 1
        self.message_user(request, f"{updated} order(s) marked as COMPLETED.")

    @admin.action(description="Mark selected orders as Pending")
    def mark_orders_pending(self, request, queryset):
        updated = queryset.update(status="Pending", is_ordered=False)
        self.message_user(request, f"{updated} order(s) marked as PENDING.")

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = (
        "order", "product", "user", "quantity", "product_price", "ordered", "created_at"
    )
    list_filter = ("ordered", "created_at")
    search_fields = (
        "order__order_number", "product__product_name", "user__email", "user__username"
    )

@admin.register(Refund)
class RefundAdmin(admin.ModelAdmin):
    list_display = ("order", "status", "requested_at", "processed_at")
    list_filter = ("status", "requested_at")
    search_fields = ("order__order_number",)

@admin.register(Dispute)
class DisputeAdmin(admin.ModelAdmin):
    list_display = ("order", "initiated_by", "status", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("order__order_number", "initiated_by__email")

@admin.register(DisputeEvidence)
class DisputeEvidenceAdmin(admin.ModelAdmin):
    list_display = ("dispute", "original_filename", "uploaded_at")
    search_fields = ("dispute__order__order_number",)

@admin.register(VendorPayout)
class VendorPayoutAdmin(admin.ModelAdmin):
    list_display = ("vendor", "amount", "status", "payout_date")
    list_filter = ("status", "payout_date")
    search_fields = ("vendor__business_name",)