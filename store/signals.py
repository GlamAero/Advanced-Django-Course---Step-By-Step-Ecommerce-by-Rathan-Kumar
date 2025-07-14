from django.db.models.signals import post_save, post_delete, pre_save, m2m_changed
from django.dispatch import receiver
from django.db import transaction
from django.core.cache import cache

from .models import Product, Variation, VariationCombination
from orders.models import Order, OrderItem, Review
from category.models import Category

# === Product Signals ===

@receiver(pre_save, sender=Product)
def pre_save_product(sender, instance, **kwargs):
    """Store original values before saving"""
    if instance.pk:
        original = Product.objects.get(pk=instance.pk)
        instance._original_price = original.price
        instance._original_category = original.category

@receiver(post_save, sender=Product)
def update_product_on_save(sender, instance, created, **kwargs):
    """Handle product save: category count + cache"""
    if not created and hasattr(instance, '_original_category'):
        if instance.category != instance._original_category:
            if instance._original_category:
                instance._original_category.update_product_count()
            instance.category.update_product_count()

    cache_keys = [
        f'product_{instance.slug}_detail',
        f'category_{instance.category_id}_products',
        'featured_products',
        'new_arrivals',
    ]
    cache.delete_many(cache_keys)

@receiver(post_delete, sender=Product)
def update_category_on_delete(sender, instance, **kwargs):
    """Update category when product is deleted"""
    if instance.category:
        instance.category.update_product_count()
    cache.delete_many([
        f'category_{instance.category_id}_products',
        'featured_products',
        'new_arrivals',
    ])

# === Order & Inventory Signals ===

@receiver(post_save, sender=OrderItem)
def update_order_total(sender, instance, created, **kwargs):
    """Update order total and inventory when item is added"""
    order = instance.order
    order.update_total()

    if created and order.status == Order.PROCESSING:
        if instance.product.product_type == 'simple':
            instance.product.stock = max(0, instance.product.stock - instance.quantity)
            instance.product.save(update_fields=['stock'])
        elif instance.variation:
            instance.variation.stock = max(0, instance.variation.stock - instance.quantity)
            instance.variation.save(update_fields=['stock'])
        elif instance.variation_combination:
            instance.variation_combination.stock = max(0, instance.variation_combination.stock - instance.quantity)
            instance.variation_combination.save(update_fields=['stock'])

@receiver(post_delete, sender=OrderItem)
def restore_inventory_on_delete(sender, instance, **kwargs):
    """Restore inventory when order item is deleted"""
    if instance.order.status == Order.PROCESSING:
        if instance.product.product_type == 'simple':
            instance.product.stock += instance.quantity
            instance.product.save(update_fields=['stock'])
        elif instance.variation:
            instance.variation.stock += instance.quantity
            instance.variation.save(update_fields=['stock'])
        elif instance.variation_combination:
            instance.variation_combination.stock += instance.quantity
            instance.variation_combination.save(update_fields=['stock'])

@receiver(pre_save, sender=Order)
def pre_save_order(sender, instance, **kwargs):
    """Track original order status"""
    if instance.pk:
        instance._original_status = Order.objects.get(pk=instance.pk).status

@receiver(post_save, sender=Order)
def handle_order_status_change(sender, instance, created, **kwargs):
    """Handle inventory changes based on status transitions"""
    if not created and hasattr(instance, '_original_status'):
        if instance._original_status != Order.CANCELLED and instance.status == Order.CANCELLED:
            # Cancelled → Restock
            for item in instance.items.all():
                if item.product.product_type == 'simple':
                    item.product.stock += item.quantity
                    item.product.save(update_fields=['stock'])
                elif item.variation:
                    item.variation.stock += item.quantity
                    item.variation.save(update_fields=['stock'])
                elif item.variation_combination:
                    item.variation_combination.stock += item.quantity
                    item.variation_combination.save(update_fields=['stock'])

        elif instance._original_status == Order.CANCELLED and instance.status in [Order.PROCESSING, Order.SHIPPED]:
            # Reactivated → Deduct again
            for item in instance.items.all():
                if item.product.product_type == 'simple':
                    item.product.stock = max(0, item.product.stock - item.quantity)
                    item.product.save(update_fields=['stock'])
                elif item.variation:
                    item.variation.stock = max(0, item.variation.stock - item.quantity)
                    item.variation.save(update_fields=['stock'])
                elif item.variation_combination:
                    item.variation_combination.stock = max(0, item.variation_combination.stock - item.quantity)
                    item.variation_combination.save(update_fields=['stock'])

# === Review Signals ===

@receiver([post_save, post_delete], sender=Review)
def update_product_rating(sender, instance, **kwargs):
    """Update average rating and review count"""
    instance.product.update_rating()
    cache.delete(f'product_{instance.product.slug}_detail')

# === Category Signals ===

@receiver(post_save, sender=Category)
def update_category_slug(sender, instance, created, **kwargs):
    """Set slug and refresh children slugs if needed"""
    if created or not instance.slug:
        instance.slug = instance.get_slug()
        instance.save(update_fields=['slug'])

    if not created:
        for child in instance.get_descendants():
            child.slug = child.get_slug()
            child.save(update_fields=['slug'])

# === Cache Invalidation for M2M ===

@receiver(m2m_changed, sender=Product.featured_categories.through)
def invalidate_featured_cache(sender, instance, action, **kwargs):
    """Clear featured and homepage caches"""
    if action in ['post_add', 'post_remove', 'post_clear']:
        cache.delete_many(['featured_products', 'homepage_categories'])
