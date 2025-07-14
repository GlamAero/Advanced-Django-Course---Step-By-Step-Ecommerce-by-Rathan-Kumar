from django.urls import path
from . import views


urlpatterns = [
    path('place_order/', views.place_order, name='place_order'),
    path('payments/', views.payments, name='payments'),
    path("paypal/order/create/", views.create_paypal_order, name="create_paypal_order"),
    path("paypal/order/capture/<str:order_id>/", views.capture_paypal_order, name="capture_paypal_order"),
    path('success/', views.success, name='success'),
]




