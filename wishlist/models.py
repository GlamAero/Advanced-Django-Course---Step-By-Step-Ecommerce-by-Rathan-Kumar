from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from accounts.models import Account
from store.models import Product

class Wishlist(models.Model):
    user = models.OneToOneField(
        Account,
        on_delete=models.CASCADE,
        related_name='wishlist',
        verbose_name='User'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Created At'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Updated At'
    )
    
    class Meta:
        verbose_name = 'Wishlist'
        verbose_name_plural = 'Wishlists'
        ordering = ['-updated_at']
        
    def __str__(self):
        return f"Wishlist of {self.user.email}"
    
    @property
    def item_count(self):
        return self.items.count()
    
    def add_item(self, product):
        if not product.is_available:
            raise ValidationError("Product is not available")
            
        if self.items.filter(product=product).exists():
            raise ValidationError("Product already in wishlist")
            
        WishlistItem.objects.create(
            wishlist=self,
            product=product
        )
    
    def remove_item(self, product):
        try:
            item = self.items.get(product=product)
            item.delete()
            return True
        except WishlistItem.DoesNotExist:
            return False

class WishlistItem(models.Model):
    wishlist = models.ForeignKey(
        Wishlist,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name='Wishlist'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='wishlist_items',
        verbose_name='Product'
    )
    added_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Added At'
    )
    
    class Meta:
        verbose_name = 'Wishlist Item'
        verbose_name_plural = 'Wishlist Items'
        unique_together = ('wishlist', 'product')
        ordering = ['-added_at']
    
    def __str__(self):
        return f"{self.product.product_name} in {self.wishlist.user.email}'s wishlist"
    
    def save(self, *args, **kwargs):
        if not self.product.is_available:
            raise ValidationError("Cannot add unavailable product to wishlist")
        super().save(*args, **kwargs)
    
    def move_to_cart(self, request, quantity=1):
        from carts.views import add_cart
        # First remove from wishlist
        self.delete()
        # Then add to cart
        return add_cart(request, self.product.id, quantity=quantity)
