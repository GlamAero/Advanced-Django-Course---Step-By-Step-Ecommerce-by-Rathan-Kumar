# accounts/urls_api.py
from django.urls import path
from rest_framework import routers
from . import views_api

router = routers.DefaultRouter()
router.register(r'users', views_api.UserViewSet, basename='user')
router.register(r'activities', views_api.ActivityViewSet, basename='activity')
router.register(r'vendor-profiles', views_api.VendorProfileViewSet, basename='vendorprofile')
router.register(r'customer-profiles', views_api.CustomerProfileViewSet, basename='customerprofile')

urlpatterns = [
    path('verify-email/', views_api.VerifyEmailAPI.as_view(), name='api-verify-email'),
    path('password/reset/', views_api.PasswordResetAPI.as_view(), name='api-password-reset'),
    path('password/set/', views_api.SetPasswordAPI.as_view(), name='api-password-set'),
    path('two-factor/toggle/', views_api.ToggleTwoFactorAPI.as_view(), name='api-toggle-2fa'),
    path('two-factor/backup-tokens/', views_api.TwoFactorBackupTokensAPI.as_view(), name='api-backup-tokens'),
] + router.urls