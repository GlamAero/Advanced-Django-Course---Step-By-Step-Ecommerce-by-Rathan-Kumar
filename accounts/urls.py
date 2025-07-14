from django.urls import path, include
from . import views

app_name = 'accounts'

urlpatterns = [
    path('register/', views.register, name='register'),
    path('login/', views.login_redirect, name='login'),
    path('login/vendor/', views.vendor_login_view, name='vendor_login'),
    path('login/customer/', views.customer_login_view, name='customer_login'),
    path('dashboard/vendor/', views.vendor_dashboard, name='vendor_dashboard'),
    path('dashboard/customer/', views.customer_dashboard, name='customer_dashboard'),
    path('profile/vendor/', views.vendor_profile, name='vendor_profile'),
    path('profile/customer/', views.customer_profile, name='customer_profile'),
    path('logout/', views.logout_view, name='logout'),
    path('activate/<uidb64>/<token>/', views.activate, name='activate'),
    path('password/forgot/', views.forgot_password, name='forgot_password'),
    path('password/reset/validate/<uidb64>/<token>/', views.reset_password_validate, name='reset_password_validate'),
    path('password/reset/', views.reset_password, name='reset_password'),
    path('2fa/verify/', views.two_factor_verify, name='two_factor_verify'),
    path('social/', include('allauth.urls')),
]

# Conditionally include recaptcha URLs if available
try:
    from django_recaptcha import urls as recaptcha_urls
    urlpatterns.append(path('captcha/', include(recaptcha_urls)))
except ImportError:
    pass