from django.urls import path
from .views import set_product_stock, set_variation_stock, vendor_dashboard

urlpatterns = [
    path("dashboard/", vendor_dashboard, name="vendor_dashboard"),
    path("set-product-stock/<int:product_id>/", set_product_stock, name="set_product_stock"),
    path("set-variation-stock/<int:variation_combination_id>/", set_variation_stock, name="set_variation_stock"),
]
