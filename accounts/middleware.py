from django.shortcuts import redirect
from django.urls import reverse
from django.conf import settings
from .utils import log_activity


class TwoFactorMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        
    def __call__(self, request):
        response = self.get_response(request)
        return response
        
    def process_view(self, request, view_func, view_args, view_kwargs):
        # Skipped middleware for specific views
        if view_func.__name__ in ['two_factor_verify', 'logout_view', 'customer_login_view', 
                                'vendor_login_view', 'activate', 'home_redirect_view']:
            return None

        # Require 2FA for sensitive views
        if request.user.is_authenticated and request.user.requires_2fa:
            if not request.session.get('2fa_verified'):
                log_activity(request.user, '2fa_required_redirect', request)
                return redirect(reverse('two_factor_verify') + f'?next={request.path}')
        
        return None


class SecurityHeadersMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        
    def __call__(self, request):
        response = self.get_response(request)
        
        # Added security headers
        response['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'SAMEORIGIN'
        
        # Added reCAPTCHA domains to CSP
        response['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self' https://www.google.com/recaptcha/ https://www.gstatic.com/; "
            "style-src 'self' 'unsafe-inline'"
        )
        
        return response