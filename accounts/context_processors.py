from .models import CustomerProfile, VendorProfile

def user_profiles(request):
    """Add user profiles to template context globally"""
    context = {}
    if request.user.is_authenticated:
        if request.user.is_vendor():
            try:
                context['vendor_profile'] = VendorProfile.objects.get(user=request.user)
            except VendorProfile.DoesNotExist:
                pass
        elif request.user.is_customer():
            try:
                context['customer_profile'] = CustomerProfile.objects.get(user=request.user)
            except CustomerProfile.DoesNotExist:
                pass
    return context