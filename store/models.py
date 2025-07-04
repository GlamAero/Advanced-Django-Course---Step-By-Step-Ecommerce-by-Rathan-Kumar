from django.db import models
from category.models import Category
from django.urls import reverse
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

class Product(models.Model):
    product_name = models.CharField(max_length=200, unique=True)
    slug = models.SlugField(max_length=200, unique=True)
    description = models.TextField()
    price = models.DecimalField(max_digits=15, decimal_places=2)
    images = models.ImageField(upload_to='photos/products')
    stock = models.IntegerField()
    is_available = models.BooleanField(default=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    created_date = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)

    def get_url(self):
        return reverse('product_detail', args=[self.category.slug, self.slug])

    def __str__(self):
        return self.product_name

class Variation(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    variation_category = models.CharField(max_length=100)  # Dynamic, no choices
    variation_value = models.CharField(max_length=100)
    stock = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_date = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.variation_category}: {self.variation_value}"

class VariationCombination(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="variation_combinations")
    variations = models.ManyToManyField(Variation)
    stock = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_date = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.product.product_name} - " + ", ".join([f"{v.variation_category}:{v.variation_value}" for v in self.variations.all()])

    def reduce_stock(self, quantity):
        if self.stock >= quantity:
            self.stock -= quantity
            self.save()
            return True
        return False

class VariationManager(models.Manager):
    def by_category(self, category_name):
        return self.filter(variation_category=category_name, is_active=True)

# --- SIGNALS TO KEEP PRODUCT.STOCK IN SYNC WITH VARIATIONCOMBINATION STOCK SUM ---
@receiver([post_save, post_delete], sender=VariationCombination)
def update_product_stock_from_combinations(sender, instance, **kwargs):
    product = instance.product
    total_stock = VariationCombination.objects.filter(product=product, is_active=True).aggregate(
        total=models.Sum('stock')
    )['total'] or 0
    product.stock = total_stock
    product.save()


