from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache
from .models import Review
from store.models import Product

@receiver([post_save, post_delete], sender=Review)
def update_product_rating(sender, instance, **kwargs):
    product = instance.product
    reviews = product.reviews.filter(is_approved=True)
    count = reviews.count()
    total = sum([r.rating for r in reviews])

    product.rating = round(total / count, 1) if count else 0
    product.review_count = count
    product.save(update_fields=['rating', 'review_count'])

    cache.delete(f'product_{product.slug}_detail')
