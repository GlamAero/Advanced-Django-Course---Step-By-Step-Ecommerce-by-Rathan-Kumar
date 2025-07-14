from django.db import models
from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.core.validators import FileExtensionValidator
from django_otp.models import Device
from django_otp.plugins.otp_static.models import StaticDevice
from django.db.models.signals import post_save
from django.dispatch import receiver
from accounts.managers import MyAccountManager


class Account(AbstractBaseUser, PermissionsMixin):
    ROLE_CHOICES = (
        ('vendor', 'Vendor'),
        ('customer', 'Customer'),
        ('admin', 'Admin'),
    )

    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)
    username = models.CharField(max_length=30, unique=True)
    email = models.EmailField(max_length=254, unique=True)
    phone_number = models.CharField(max_length=15, blank=True)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='customer')
    date_joined = models.DateTimeField(auto_now_add=True)
    last_login = models.DateTimeField(auto_now=True)
    is_admin = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=False)
    is_superadmin = models.BooleanField(default=False)
    requires_2fa = models.BooleanField(default=False, verbose_name="Requires 2FA")
    email_verified = models.BooleanField(default=False)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

    objects = MyAccountManager()

    def __str__(self):
        return self.email

    def has_perm(self, perm, obj=None):
        return self.is_admin or self.is_superadmin

    def has_module_perms(self, app_label):
        return self.is_admin or self.is_superadmin

    @property
    def is_superuser(self):
        return self.is_superadmin

    def is_vendor(self):
        return self.role == 'vendor'

    def is_customer(self):
        return self.role == 'customer'
    
    def verify_token(self, token):
        for device in Device.objects.filter(user=self):
            if device.verify_token(token):
                return True
        return False

    def get_backup_tokens(self):
        device, created = StaticDevice.objects.get_or_create(user=self, name='backup')
        return device.token_set.values_list('token', flat=True)

def vendor_license_path(instance, filename):
    return f'vendors/{instance.user.id}/licenses/{filename}'

def vendor_profile_image_path(instance, filename):
    return f'vendors/{instance.user.id}/profile_images/{filename}'

class VendorProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    company_name = models.CharField(max_length=255, blank=True)
    business_license_number = models.CharField(max_length=100, blank=True)
    website = models.URLField(blank=True)
    address = models.TextField(blank=True)
    business_license_file = models.FileField(
        upload_to=vendor_license_path,
        validators=[FileExtensionValidator(['pdf', 'jpg', 'jpeg', 'png'])],
        blank=True,
        null=True
    )
    profile_image = models.ImageField(
        upload_to=vendor_profile_image_path,
        validators=[FileExtensionValidator(['jpg', 'jpeg', 'png'])],
        blank=True,
        null=True,
        help_text="Upload a profile image (jpg, jpeg, png)."
    )
    is_verified = models.BooleanField(default=False, help_text="Is the vendor profile verified?")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    business_license_expiry = models.DateField(null=True, blank=True)

    def clean(self):
    if self.business_license_expiry and self.business_license_expiry < timezone.now().date():
        raise ValidationError("Business license has expired")

    def __str__(self):
        return f"Vendor Profile for {self.user.email}"

class CustomerProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    date_of_birth = models.DateField(null=True, blank=True)
    preferred_contact_method = models.CharField(max_length=50, blank=True)
    shipping_address = models.TextField(blank=True)
    billing_address = models.TextField(blank=True)
    preferences = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"CustomerProfile for {self.user.email}"

from django.db import models
from accounts.models import Account  # Adjust import as per your project structure

class UserActivity(models.Model):
    ACTIVITY_TYPES = [
        ('login', 'Login'),
        ('logout', 'Logout'),
        ('account_activated', 'Account Activated'),
        ('password_reset_requested', 'Password Reset Requested'),
        ('password_reset', 'Password Reset'),
        ('profile_update', 'Profile Updated'),
    ]
    
    user = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='activities')
    activity_type = models.CharField(max_length=50, choices=ACTIVITY_TYPES)
    ip_address = models.GenericIPAddressField()
    user_agent = models.CharField(max_length=500)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
        verbose_name_plural = 'User Activities'
        indexes = [
            models.Index(fields=['-timestamp']),
            models.Index(fields=['activity_type']),
        ]
        
    def __str__(self):
        return f"{self.get_activity_type_display()} by {self.user.email}"
