from django.db import models
from category.models import Category
from django.urls import reverse
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver


class Product(models.Model):
    PRODUCT_TYPE_CHOICES = [
        ('simple', 'Simple (no variations)'),
        ('variation', 'Product with variations only'),
        ('combination', 'Product with variation combinations'),
    ]

    product_type = models.CharField(
        max_length=20,
        choices=PRODUCT_TYPE_CHOICES,
        default='simple',
    )

    product_name = models.CharField(max_length=200, unique=True)
    slug = models.SlugField(max_length=200, unique=True)
    description = models.TextField()
    price = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)  # Only for simple
    images = models.ImageField(upload_to='photos/products')
    stock = models.IntegerField(default=0)
    is_available = models.BooleanField(default=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    created_date = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)

    def get_url(self):
        return reverse('product_detail', args=[self.category.slug, self.slug])

    def __str__(self):
        return f"{self.product_name} [{self.product_type}]"


class Variation(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    variation_category = models.CharField(max_length=100)
    variation_value = models.CharField(max_length=100)
    stock = models.PositiveIntegerField(null=True, blank=True, default=0)
    price = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_date = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.variation_category}: {self.variation_value}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.product.product_type == 'variation':
            total_stock = Variation.objects.filter(
                product=self.product,
                is_active=True,
                stock__isnull=False
            ).aggregate(total=models.Sum('stock'))['total'] or 0
            self.product.stock = total_stock
            self.product.save(update_fields=['stock'])


class VariationCombination(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="variation_combinations")
    variations = models.ManyToManyField(Variation)
    stock = models.PositiveIntegerField(default=0)
    price = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_date = models.DateTimeField(auto_now=True)

    def __str__(self):
        variations_text = ", ".join(
            f"{v.variation_category}:{v.variation_value}" for v in self.variations.all()
        )
        return f"{self.product.product_name} - {variations_text}"

    def reduce_stock(self, quantity):
        if self.stock >= quantity:
            self.stock -= quantity
            self.save(update_fields=['stock'])
            return True
        return False

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        total = VariationCombination.objects.filter(
            product=self.product,
            is_active=True
        ).aggregate(total=models.Sum('stock'))['total'] or 0
        self.product.stock = total
        self.product.save(update_fields=['stock'])


class VariationManager(models.Manager):
    def by_category(self, category_name):
        return self.filter(variation_category=category_name, is_active=True)


@receiver([post_save, post_delete], sender=VariationCombination)
def update_product_stock_from_combinations(sender, instance, **kwargs):
    product = instance.product
    total_stock = VariationCombination.objects.filter(
        product=product,
        is_active=True
    ).aggregate(total=models.Sum('stock'))['total'] or 0
    product.stock = total_stock
    product.save(update_fields=['stock'])