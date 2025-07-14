import logging
from django.utils import timezone
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.utils.http import urlsafe_base64_encode, force_bytes
from django.contrib.auth.tokens import default_token_generator
from .models import Account


logger = logging.getLogger(__name__)


class EmailSendError(Exception):
    """Exception raised when sending activation email fails."""
    pass


def send_activation_email(user, request):
    """Send account activation email with token"""
    try:
        context = {
            'user': user,
            'domain': request.get_host(),
            'uid': urlsafe_base64_encode(force_bytes(user.pk)),
            'token': default_token_generator.make_token(user),  # Django's token generator
        }
        html_content = render_to_string('accounts/activation_email.html', context)
        
        send_mail(
            subject="Activate Your Account",
            message=render_to_string('accounts/activation_email.txt', context),
            html_message=html_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False
        )
        return True
    except Exception as e:
        logger.error(f"Failed to send activation email to {user.email}: {str(e)}")
        return False


def verify_vendor_documents(vendor_profile):
    """Automatically verify vendor if documents meet requirements"""
    if not vendor_profile.business_license_expiry:
        # No expiry date provided, cannot verify
        return False
    
    if vendor_profile.business_license_expiry < timezone.now().date():
        # License expired
        return False
    
    if (vendor_profile.business_license_file and 
        vendor_profile.business_license_number):
        vendor_profile.is_verified = True
        vendor_profile.verification_date = timezone.now()
        vendor_profile.save()
        return True
    
    return False
