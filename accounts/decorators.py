from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import redirect
from functools import wraps
from django.http import HttpResponseForbidden, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse
from orders.models import Order
from django.apps import apps


def customer_required(view_func):
    decorated_view_func = user_passes_test(
        lambda u: u.is_authenticated and u.is_customer(),
        login_url='customer_login'
    )(view_func)
    return decorated_view_func

def vendor_required(view_func):
    decorated_view_func = user_passes_test(
        lambda u: u.is_authenticated and u.is_vendor(),
        login_url='vendor_login'
    )(view_func)
    return decorated_view_func


def customer_or_vendor_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, order_number, *args, **kwargs):
        # Redirect unauthenticated users to login redirect
        if not request.user.is_authenticated:
            next_param = request.build_absolute_uri()
            login_url = reverse('accounts:login') + f'?next={next_param}'
            return HttpResponseRedirect(login_url)

        # Retrieve the order or return 404 if not found
        Order = apps.get_model('orders', 'Order')
        order = get_object_or_404(Order, order_number=order_number)

        # Properly get vendor user from VendorProfile
        vendor_user = None
        if hasattr(order, 'vendor') and order.vendor:
            # Access the user through the VendorProfile
            vendor_user = order.vendor.user

        # Check authorization
        if request.user == order.user or request.user == vendor_user:
            return view_func(request, order_number, *args, **kwargs)

        return HttpResponseForbidden("You are unauthorized to view this order.")
    return _wrapped_view