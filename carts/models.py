from django.db import models
from store.models import Product, Variation
from accounts.models import Account


# Create your models here.
class Cart(models.Model):
    cart_id = models.CharField(max_length=250, blank=True)
    date_added = models.DateField(auto_now_add=True)

    def __str__(self):
        return self.cart_id
    

class CartItem(models.Model):
    user = models.ForeignKey(Account, on_delete=models.CASCADE, null=True)

    product = models.ForeignKey(Product, on_delete=models.CASCADE)

    # 'ManyToManyField' because a product can have many variations and a single variation can belong to multiple products.
    # These variations can be in sizes, colors etc.
    variations = models.ManyToManyField(Variation, blank=True)
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, null=True)
    quantity = models.IntegerField()

    # 'is_active' is used to check if the item is still in the cart
    # - Instead of deleting items permanently, setting is_active=False allows you to "hide" them
    is_active = models.BooleanField(default=True)

    # total for each product purchased:
    def sub_total(self):
        return self.product.price * self.quantity
    

    # 'unicode' because the 'product' in 'self.product' is a dictionary and not as string so we can't use '__str__'
    def __unicode__(self):
        return self.product