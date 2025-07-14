from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.utils import timezone
from .models import Coupon

@receiver(pre_save, sender=Coupon)
def validate_coupon_dates(sender, instance, **kwargs):
    """Ensure coupon validity dates make sense"""
    if instance.valid_to and instance.valid_to < timezone.now():
        instance.active = False
    if instance.valid_from and instance.valid_to:
        if instance.valid_from > instance.valid_to:
            raise ValueError("Valid from date cannot be after valid to date")