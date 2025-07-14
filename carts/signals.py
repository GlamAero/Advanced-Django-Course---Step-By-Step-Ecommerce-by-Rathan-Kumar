from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from .models import CartItem, Cart
from django.utils import timezone
from datetime import timedelta
from django.core.exceptions import ValidationError


@receiver(pre_save, sender=CartItem)
def validate_cart_item_stock(sender, instance, **kwargs):
    """Ensure cart item quantity doesn't exceed available stock."""

    # Skip check if quantity hasn't changed
    if instance.pk:
        try:
            original = CartItem.objects.get(pk=instance.pk)
            if original.quantity == instance.quantity:
                return  # No change in quantity; skip validation
        except CartItem.DoesNotExist:
            pass  # Fallback to full validation for new-like instances

    combination = instance.get_variation_combination()
    available_stock = combination.stock if combination else instance.product.stock

    if instance.quantity > available_stock:
        raise ValidationError(f"Only {available_stock} available in stock")

@receiver(post_save, sender=Cart)
def check_cart_activity(sender, instance, **kwargs):
    """Check cart activity status and update accordingly"""
    # Mark abandoned carts (30 minutes inactive)
    if instance.status == 'active':
        abandonment_threshold = timezone.now() - timedelta(minutes=30)
        if instance.last_activity < abandonment_threshold:
            instance.status = 'abandoned'
            instance.save()
    
    # Expire anonymous carts after 7 days
    if not instance.user and instance.status == 'active':
        expiration_threshold = timezone.now() - timedelta(days=7)
        if instance.last_activity < expiration_threshold:
            instance.status = 'expired'
            instance.is_active = False
            instance.save()

@receiver(post_save, sender=CartItem)
def update_cart_activity(sender, instance, **kwargs):
    """Update cart activity timestamp when items change"""
    if instance.cart:
        instance.cart.last_activity = timezone.now()
        instance.cart.save()