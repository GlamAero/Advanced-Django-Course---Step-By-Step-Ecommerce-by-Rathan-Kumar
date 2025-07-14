from django.urls import path
from . import views

app_name = "orders"

urlpatterns = [
    # ===== ORDER PROCESSING =====
    path("place_order/", views.place_order, name="place_order"),
    
    # ===== PAYMENT PROCESSING =====
    path("payment/initiate/", views.create_payment_order, name="create_payment_order"),
    path("payment/capture/", views.capture_payment, name="capture_payment"),
    path("payment/success/", views.payment_success, name="payment_success"),
    
    # ===== ORDER MANAGEMENT =====
    path("my-orders/", views.customer_orders, name="customer_orders"),
    path("order/<str:order_number>/", views.order_detail, name="order_detail"),
    
    # ===== VENDOR PAYOUTS =====
    path("vendor/payouts/", views.vendor_payouts, name="vendor_payouts"),
    path("admin/process-payouts/", views.process_vendor_payouts, name="process_vendor_payouts"),
    
    # ===== REFUND MANAGEMENT =====
    path("order/<str:order_number>/request-refund/", views.request_refund, name="request_refund"),
    path("admin/refunds/", views.admin_refund_requests, name="admin_refund_requests"),
    path("admin/refunds/<int:refund_id>/process/", views.process_refund, name="process_refund"),
    
    # ===== DISPUTE MANAGEMENT =====
    path("order/<str:order_number>/create-dispute/", views.create_dispute, name="create_dispute"),
    path("admin/disputes/", views.admin_disputes, name="admin_disputes"),
    path("admin/disputes/<int:dispute_id>/resolve/", views.resolve_dispute, name="resolve_dispute"),
    
    # ===== ADMIN INSIGHTS =====
    path("admin/payment-insights/", views.admin_payment_insights, name="admin_payment_insights"),
    
    # ===== PAYMENT WEBHOOKS =====
    path("webhooks/paypal/", views.paypal_webhook, name="paypal_webhook"),
    path("webhooks/stripe/", views.stripe_webhook, name="stripe_webhook"),
    path("webhooks/flutterwave/", views.flutterwave_webhook, name="flutterwave_webhook"),
]