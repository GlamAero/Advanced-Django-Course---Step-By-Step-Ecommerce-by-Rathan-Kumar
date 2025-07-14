from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import Wishlist

User = get_user_model()

@receiver(post_save, sender=User)
def create_user_wishlist(sender, instance, created, **kwargs):
    """
    Create wishlist when new user account is created
    """
    if created:
        Wishlist.objects.create(user=instance)

@receiver(post_delete, sender=Wishlist)
def cleanup_wishlist_images(sender, instance, **kwargs):
    """
    Clean up product images when wishlist items are deleted
    """
    for item in instance.items.all():
        # Trigger product image cleanup if needed
        item.product.clean_images()


