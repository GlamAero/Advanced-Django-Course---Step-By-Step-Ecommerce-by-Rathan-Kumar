from django.db.models.signals import pre_save, pre_delete
from django.dispatch import receiver
from django.db import transaction
from django.utils.text import slugify
from .models import Category
from store.models import Product

@receiver(pre_save, sender=Category)
def update_category_slug(sender, instance, **kwargs):
    """
    Ensure slug is always updated when category name changes
    """
    if instance.pk:
        original = Category.objects.get(pk=instance.pk)
        if original.category_name != instance.category_name:
            instance.slug = slugify(instance.category_name)

@receiver(pre_delete, sender=Category)
def handle_category_deletion(sender, instance, **kwargs):
    """
    Handle product reassignment when deleting categories
    """
    with transaction.atomic():
        # Reassign products to parent category if exists
        if instance.parent:
            Product.objects.filter(category=instance).update(category=instance.parent)
        else:
            # Reassign to root "Uncategorized" category
            uncategorized, created = Category.objects.get_or_create(
                category_name="Uncategorized",
                defaults={
                    'slug': 'uncategorized',
                    'description': 'Products without a category'
                }
            )
            Product.objects.filter(category=instance).update(category=uncategorized)