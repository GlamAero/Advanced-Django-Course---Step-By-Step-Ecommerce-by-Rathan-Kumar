import logging
import time
from urllib.parse import urlparse

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login as auth_login, logout as auth_logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.tokens import default_token_generator
from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import EmailMessage
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode, url_has_allowed_host_and_scheme
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.debug import sensitive_post_parameters
from django_ratelimit.decorators import ratelimit
from django_ratelimit.exceptions import Ratelimited
from axes.decorators import axes_dispatch
from django_otp.plugins.otp_static.models import StaticDevice

from accounts.selectors import get_user_activity_summary
from accounts.services import EmailSendError, send_activation_email

from .forms import (
    VendorRegistrationForm, CustomerRegistrationForm,
    VendorLoginForm, CustomerLoginForm,
    VendorProfileForm, CustomerProfileForm,
    PasswordResetForm, SetPasswordForm
)
from .models import Account, VendorProfile, CustomerProfile
from carts.models import Cart, CartItem
from carts.views import _cart_id
from .decorators import customer_required, vendor_required
from .utils import log_activity, get_client_ip
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password


logger = logging.getLogger(__name__)

# ========================
# SESSION KEYS MANAGEMENT
# ========================
SESSION_2FA_USER_ID = '2fa_user_id'
SESSION_2FA_REMEMBER_ME = '2fa_remember_me'
SESSION_2FA_USER_TYPE = '2fa_user_type'
SESSION_LAST_LOGIN_TYPE = 'last_login_type'
SESSION_UID = 'uid'

# ===================
# UTILITY FUNCTIONS
# ===================
def ratelimit_handler(request, exception=None):
    if isinstance(exception, Ratelimited):
        return render(request, 'accounts/rate_limit.html', status=429)
    return HttpResponseForbidden("Forbidden", status=403)

def _merge_cart_items(request, user):
    try:
        cart = Cart.objects.get(cart_id=_cart_id(request))
        cart_items = CartItem.objects.filter(cart=cart)

        if cart_items.exists():
            user_cart_items = CartItem.objects.filter(user=user)
            user_variation_map = {}
            for u_item in user_cart_items:
                key = (u_item.product.id, tuple(u_item.variations.values_list('id', flat=True)))
                user_variation_map[key] = u_item

            for item in cart_items:
                key = (item.product.id, tuple(item.variations.values_list('id', flat=True)))
                if key in user_variation_map:
                    user_item = user_variation_map[key]
                    user_item.quantity += item.quantity
                    user_item.save()
                    item.delete()
                else:
                    item.user = user
                    item.save()
    except Cart.DoesNotExist:
        pass
    except Exception as e:
        logger.error(f"Error merging cart items for {user.email}: {e}")

def _complete_login(request, user, user_type, remember_me):
    auth_login(request, user)
    request.session[SESSION_LAST_LOGIN_TYPE] = user_type
    
    if not remember_me:
        request.session.set_expiry(settings.SESSION_COOKIE_AGE)
    
    _merge_cart_items(request, user)
    log_activity(user, 'login', request)
    messages.success(request, "Logged in successfully")
    return _redirect_after_login(request, 'vendor_dashboard' if user_type == 'vendor' else 'home')

def _complete_2fa_login(request, user, user_type, remember_me):
    _complete_login(request, user, user_type, remember_me)
    
    # Clean up session
    for key in [SESSION_2FA_USER_ID, SESSION_2FA_REMEMBER_ME, SESSION_2FA_USER_TYPE]:
        request.session.pop(key, None)

def _redirect_after_login(request, default_view):
    next_url = request.GET.get('next') or request.POST.get('next')
    
    # Disallowed paths to prevent redirect attacks
    DISALLOWED_PATHS = [
        '/logout/',
        '/admin/',
        '/password/change/',
        '/account/delete/'
    ]
    
    if next_url and url_has_allowed_host_and_scheme(
        url=next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure()
    ):
        # Additional path validation
        if any(next_url.startswith(path) for path in DISALLOWED_PATHS):
            return redirect(default_view)
        return redirect(next_url)
    return redirect(default_view)

def redirect_with_next(view_name, request):
    url = reverse(view_name)
    next_url = request.GET.get('next', '')
    if next_url:
        return redirect(f'{url}?next={next_url}')
    return redirect(url)

def is_vendor_url(url):
    if not url:
        return False
    parsed = urlparse(url)
    vendor_paths = ['/vendor/', '/dashboard/vendor/', '/manage/']
    return any(path in parsed.path for path in vendor_paths)

# =====================
# VIEW FUNCTIONS
# =====================
def home_redirect_view(request):
    if request.user.is_authenticated:
        if request.user.is_vendor():
            return redirect('vendor_dashboard')
        return redirect('home')
    return render(request, 'home.html')

@customer_required
def customer_dashboard(request):
    return render(request, 'accounts/customer_dashboard.html', {
        'user': request.user,
        'profile': request.user.customerprofile
    })

@vendor_required
def vendor_dashboard(request):
    return render(request, 'accounts/vendor_dashboard.html')

@vendor_required
def vendor_profile(request):
    profile, _ = VendorProfile.objects.get_or_create(
        user=request.user,
        defaults={'company_name': request.user.email}
    )
    
    if request.method == 'POST':
        form = VendorProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            log_activity(request.user, 'profile_update', request)
            messages.success(request, "Vendor profile updated successfully")
            return redirect('vendor_dashboard')
        messages.error(request, "Please correct the errors below")
    else:
        form = VendorProfileForm(instance=profile)
    
    return render(request, 'accounts/vendor_profile.html', {'form': form})

@customer_required
def customer_profile(request):
    profile, _ = CustomerProfile.objects.get_or_create(
        user=request.user,
        defaults={}
    )
    
    if request.method == 'POST':
        form = CustomerProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            log_activity(request.user, 'profile_update', request)
            messages.success(request, "Customer profile updated successfully")
            return redirect('customer_dashboard')
        messages.error(request, "Please correct the errors below")
    else:
        form = CustomerProfileForm(instance=profile)

    context = { 'form': form, 'activity_summary': get_user_activity_summary(request.user) }
    
    return render(request, 'accounts/customer_profile.html', context)

def register(request):
    role = request.GET.get('role', 'customer')
    if role not in ['vendor', 'customer']:
        messages.error(request, "Invalid role selected")
        return redirect('home')

    form_class = VendorRegistrationForm if role == 'vendor' else CustomerRegistrationForm

    if request.method == 'POST':
        form = form_class(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.role = role
            user.is_active = False
            user.save()
                
            try:
                send_activation_email(user, request)
                messages.success(request, "Registration successful! Please check your email to activate your account.")
            except EmailSendError:
                messages.error(request, "Failed to send activation email. Please try again or contact support")

            return redirect('vendor_login' if role == 'vendor' else 'customer_login')
    else:
        form = form_class()

    return render(request, 'accounts/register.html', {'form': form, 'role': role})

def _handle_login(request, form, user_type):
    """Shared login handling for both vendor and customer"""
    if request.user.is_authenticated:
        if user_type == 'vendor' and request.user.is_vendor():
            return _redirect_after_login(request, 'vendor_dashboard')
        return _redirect_after_login(request, 'home')
    
    next_url = request.GET.get('next', '')
    
    if request.method == 'POST' and form.is_valid():
        email = form.cleaned_data.get('email')
        password = form.cleaned_data.get('password')
        remember_me = form.cleaned_data.get('remember_me')
        user = authenticate(request, username=email, password=password)
        
        if not user:
            messages.error(request, "Invalid credentials")
            time.sleep(1.5)
            return render(request, f'accounts/{user_type}_login.html', {'form': form})
        
        # Validate user type
        if user_type == 'vendor' and not user.is_vendor():
            messages.error(request, "This account is not registered as a vendor")
            return render(request, f'accounts/{user_type}_login.html', {'form': form})
        elif user_type == 'customer' and user.is_vendor():
            messages.error(request, "Please use vendor login")
            return render(request, f'accounts/{user_type}_login.html', {'form': form})
        
        # Validate account status
        if not user.is_active:
            messages.error(request, "Account deactivated")
            return render(request, f'accounts/{user_type}_login.html', {'form': form})
        
        if not user.email_verified:
            messages.warning(request, "Please verify your email address")
            return render(request, f'accounts/{user_type}_login.html', {'form': form})
        
        # Handle 2FA
        if user.requires_2fa:
            request.session[SESSION_2FA_USER_ID] = user.id
            request.session[SESSION_2FA_REMEMBER_ME] = remember_me
            request.session[SESSION_2FA_USER_TYPE] = user_type
            return redirect('two_factor_verify')
        
        # Complete regular login
        return _complete_login(request, user, user_type, remember_me)
    
    return render(request, f'accounts/{user_type}_login.html', {
        'form': form,
        'next': next_url
    })


@axes_dispatch
@ratelimit(key='post:email', rate='5/m', block=True)
@sensitive_post_parameters()
@csrf_protect
def vendor_login_view(request):
    form = VendorLoginForm(request.POST or None)
    return _handle_login(request, form, 'vendor')


@axes_dispatch
@ratelimit(key='post:email', rate='5/m', block=True)
@sensitive_post_parameters()
@csrf_protect
def customer_login_view(request):
    form = CustomerLoginForm(request.POST or None)
    return _handle_login(request, form, 'customer')


@ratelimit(key='ip', rate='5/h')
def two_factor_verify(request):
    user_id = request.session.get(SESSION_2FA_USER_ID)
    remember_me = request.session.get(SESSION_2FA_REMEMBER_ME, False)
    user_type = request.session.get(SESSION_2FA_USER_TYPE, 'customer')
    
    if not user_id:
        messages.error(request, "Session expired")
        return redirect('vendor_login' if user_type == 'vendor' else 'customer_login')
    
    try:
        user = Account.objects.get(id=user_id)
    except Account.DoesNotExist:
        messages.error(request, "Invalid session")
        return redirect('vendor_login' if user_type == 'vendor' else 'customer_login')
    
    backup_device, created = StaticDevice.objects.get_or_create(
        user=user, 
        name='backup'
    )
    
    backup_tokens = list(backup_device.token_set.values_list('token', flat=True))
    if not backup_tokens:
        backup_device.generate_tokens(10)
        backup_tokens = list(backup_device.token_set.values_list('token', flat=True))
    
    if request.method == 'POST':
        token = request.POST.get('token')
        if user.verify_token(token):
            _complete_2fa_login(request, user, user_type, remember_me)
            return redirect('vendor_dashboard' if user_type == 'vendor' else 'home')
        else:
            if token in backup_tokens:
                backup_device.token_set.filter(token=token).delete()
                _complete_2fa_login(request, user, user_type, remember_me)
                return redirect('vendor_dashboard' if user_type == 'vendor' else 'home')
            else:
                messages.error(request, "Invalid code")
    
    return render(request, 'accounts/two_factor_verify.html', {
        'backup_tokens': backup_tokens
    })


def login_redirect(request):
    user_type = request.GET.get('type', '').lower()
    if user_type == 'vendor':
        return redirect_with_next('vendor_login', request)
    if user_type == 'customer':
        return redirect_with_next('customer_login', request)
    
    next_url = request.GET.get('next', '')
    if is_vendor_url(next_url):
        return redirect_with_next('vendor_login', request)
    
    referer = request.META.get('HTTP_REFERER', '')
    if is_vendor_url(referer):
        return redirect_with_next('vendor_login', request)
    
    if request.session.get(SESSION_LAST_LOGIN_TYPE) == 'vendor':
        return redirect_with_next('vendor_login', request)
    
    return redirect_with_next('customer_login', request)

def logout_view(request):
    if not request.user.is_authenticated:
        return redirect('home')
    
    log_activity(request.user, 'logout', request)
    
    session_keys = [
        SESSION_LAST_LOGIN_TYPE,
        SESSION_2FA_USER_ID,
        SESSION_2FA_REMEMBER_ME,
        SESSION_UID
    ]
    for key in session_keys:
        request.session.pop(key, None)
    
    auth_logout(request)
    messages.success(request, "Logged out successfully")
    return redirect('home')


def activate(request, uidb64, token):
    """
    Activate user account if the token is valid and the user is not already verified.
    """
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = Account._default_manager.get(pk=uid)
    except (TypeError, ValueError, OverflowError, Account.DoesNotExist):
        user = None

    if user and default_token_generator.check_token(user, token):
        if not user.email_verified:  # Prevent re-activation
            user.email_verified = True
            user.is_active = True  # Ensure account is active upon activation
            user.save()
            log_activity(user, 'account_activated', request)
            messages.success(request, "Account activated successfully")
            auth_login(request, user)
            return redirect('vendor_dashboard' if user.is_vendor() else 'customer_dashboard')
        else:
            messages.info(request, "Account already activated")
            return redirect('login')
    else:
        messages.error(request, "Invalid or expired activation link")
        return redirect('home')


def forgot_password(request):
    if request.method == 'POST':
        form = PasswordResetForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data.get('email')
            if Account.objects.filter(email=email).exists():
                user = Account.objects.get(email__iexact=email)
                current_site = get_current_site(request)
                message = render_to_string('accounts/reset_password_email.html', {
                    'user': user,
                    'domain': current_site.domain,
                    'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                    'token': default_token_generator.make_token(user),
                })
                EmailMessage("Password Reset", message, to=[email]).send()
                log_activity(user, 'password_reset_requested', request)
                messages.success(request, "Password reset email sent")
                return redirect('customer_login')
        messages.error(request, "Email not found")
    else:
        form = PasswordResetForm()
    return render(request, 'accounts/forgot_password.html', {'form': form})

def reset_password_validate(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = Account._default_manager.get(pk=uid)
    except (TypeError, ValueError, OverflowError, Account.DoesNotExist):
        user = None

    if user and default_token_generator.check_token(user, token):
        request.session[SESSION_UID] = uid
        messages.info(request, "Please reset your password")
        return redirect('reset_password')
    else:
        messages.error(request, "Invalid reset link")
        return redirect('customer_login')

def reset_password(request):
    uid = request.session.get(SESSION_UID)
    if not uid:
        messages.error(request, "Session expired. Please try resetting your password again.")
        return redirect('forgot_password')
    
    user = get_object_or_404(Account, pk=uid)
    
    if request.method == 'POST':
        form = SetPasswordForm(request.POST)
        if form.is_valid():
            password = form.cleaned_data.get('new_password')
            user.set_password(password)
            user.save()
            log_activity(user, 'password_reset', request)
            del request.session[SESSION_UID]
            messages.success(request, "Password reset successful. Please log in with your new password.")
            return redirect('customer_login')
    else:
        form = SetPasswordForm()
    
    return render(request, 'accounts/reset_password.html', {'form': form})
