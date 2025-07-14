from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView
from accounts import views as accounts_views
from .views import home

# Custom error handlers
handler400 = 'accounts.views.bad_request_view'
handler403 = 'accounts.views.permission_denied_view'
handler404 = 'accounts.views.page_not_found_view'
handler500 = 'accounts.views.server_error_view'

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),
    
    # Home
    path('', home, name='home'),
    
    # Apps
    path('accounts/', include('accounts.urls')),
    path('store/', include('store.urls')),
    path('cart/', include('carts.urls')),
    path('orders/', include('orders.urls')),
    path('wishlist/', include('wishlist.urls')),
    
    # Auth
    path('accounts/login/', accounts_views.login_redirect, name='login'),
    path('accounts/', include('allauth.urls')),
    
    # Security
    path('captcha/', include('captcha.urls')),
    
    # Legal
    path('terms/', TemplateView.as_view(template_name='legal/terms.html'), name='terms'),
    path('privacy/', TemplateView.as_view(template_name='legal/privacy.html'), name='privacy'),

    path('api/accounts/', include('accounts.urls_api')),

]

# Media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    
# Debug toolbar
if settings.DEBUG and 'debug_toolbar' in settings.INSTALLED_APPS:
    import debug_toolbar
    urlpatterns = [
        path('__debug__/', include(debug_toolbar.urls)),
    ] + urlpatterns



