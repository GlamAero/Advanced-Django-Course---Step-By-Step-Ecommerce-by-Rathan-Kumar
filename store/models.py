from django.db import models
from django.urls import reverse
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.exceptions import ValidationError
from category.models import Category
from accounts.models import VendorProfile
import re
from django.utils.text import slugify
from django.db.models import Sum, Avg, Count
from django.db import transaction

VARIATION_TYPE_HINTS = {
    'size': [r'^S$', r'^M$', r'^L$', r'^XL$', r'^\d+$'],
    'color': [r'^(red|blue|green|black|white)$'],
    'material': [r'^(cotton|leather|wool)$'],
}

def infer_variation_type(value):
    value = value.strip().lower()
    for var_type, patterns in VARIATION_TYPE_HINTS.items():
        for pattern in patterns:
            if re.match(pattern, value):
                return var_type.capitalize()
    return "Custom"

PRODUCT_TYPE_CHOICES = [
    ('simple', 'Simple (no variations)'),
    ('variation', 'Product with individual variations'),
    ('combination', 'Product with variation combinations'),
]

class Product(models.Model):
    vendor = models.ForeignKey(
        VendorProfile, 
        on_delete=models.CASCADE,
        related_name='products',
        verbose_name="Vendor"
    )
    product_type = models.CharField(
        max_length=20,
        choices=PRODUCT_TYPE_CHOICES,
        default='simple'
    )
    product_name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    description = models.TextField()
    price = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)
    images = models.ImageField(upload_to='photos/products')
    stock = models.PositiveIntegerField(default=0)
    is_available = models.BooleanField(default=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    created_date = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)
    
    # New fields for ratings and reviews
    rating = models.DecimalField(
        max_digits=3, 
        decimal_places=1, 
        default=0.0,
        editable=False,
        help_text="Average rating from approved reviews"
    )
    review_count = models.PositiveIntegerField(
        default=0,
        editable=False,
        help_text="Count of approved reviews"
    )

    featured_categories = models.ManyToManyField(Category, related_name='featured_products', blank=True)

    class Meta:
        ordering = ['-created_date']
        verbose_name = 'Product'
        verbose_name_plural = 'Products'
        indexes = [
            models.Index(fields=['rating']),
            models.Index(fields=['is_available']),
        ]

    def __str__(self):
        return f"{self.product_name} [{self.product_type}]"

    def get_absolute_url(self):
        return reverse('product_detail', args=[self.category.slug, self.slug])

    def clean(self):
        if not self.pk:
            return

        if self.product_type == 'variation':
            expected_stock = self.variations.filter(is_active=True).aggregate(
                total=Sum('stock')
            )['total'] or 0
            if self.stock != expected_stock:
                raise ValidationError(
                    f"Stock mismatch for variation-type product: declared {self.stock}, expected {expected_stock}."
                )

        if self.product_type == 'combination':
            expected_stock = self.variation_combinations.filter(is_active=True).aggregate(
                total=Sum('stock')
            )['total'] or 0
            if self.stock != expected_stock:
                raise ValidationError(
                    f"Stock mismatch for combination-type product: declared {self.stock}, expected {expected_stock}."
                )

    @property
    def display_price(self):
        if self.product_type == 'combination':
            combo = self.variation_combinations.filter(is_active=True).order_by('price').first()
            return combo.price if combo else None
        elif self.product_type == 'variation':
            variation = self.variations.filter(is_active=True).order_by('price').first()
            return variation.price if variation else None
        return self.price

    def update_rating(self):
        """Recalculate rating average and review count"""
        # Aggregate approved reviews
        result = self.reviews.filter(is_approved=True).aggregate(
            average_rating=Avg('rating'),
            review_count=Count('id')
        )
        
        # Update fields
        self.rating = result['average_rating'] or 0.0
        self.review_count = result['review_count'] or 0
        self.save(update_fields=['rating', 'review_count'])
        
        # Update category product count
        self.category.update_product_count()


class Variation(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variations')
    variation_type = models.CharField(max_length=50)
    variation_value = models.CharField(max_length=50)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    stock = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('product', 'variation_type', 'variation_value')
        ordering = ['variation_type', 'variation_value']

    def __str__(self):
        return f"{self.variation_type}: {self.variation_value} (${self.price}, stock: {self.stock})"

    def save(self, *args, **kwargs):
        if not self.variation_type or self.variation_type.lower() in ["", "custom"]:
            self.variation_type = infer_variation_type(self.variation_value)
        
        super().save(*args, **kwargs)
        
        if self.product.product_type == 'variation':
            total_stock = self.product.variations.filter(is_active=True).aggregate(
                total=Sum('stock')
            )['total'] or 0
            self.product.stock = total_stock
            self.product.save(update_fields=['stock'])


class VariationCombination(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="variation_combinations")
    variations = models.ManyToManyField(Variation)
    stock = models.PositiveIntegerField(default=0)
    price = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)
    sku = models.CharField(max_length=200, unique=True, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_date = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['product']),
            models.Index(fields=['sku']),
            models.Index(fields=['is_active']),
        ]
        verbose_name = "Variation Combination"
        verbose_name_plural = "Variation Combinations"

    def __str__(self):
        variations_text = ", ".join(
            f"{v.variation_type}:{v.variation_value}" for v in self.variations.all()
        )
        return f"{self.product.product_name} - {variations_text} [{self.sku or 'no SKU'}]"

    def clean(self):
        if not self.product or not self.variations.exists():
            return

        current_ids = set(self.variations.values_list('id', flat=True))
        existing_combos = VariationCombination.objects.filter(product=self.product)

        if self.pk:
            existing_combos = existing_combos.exclude(pk=self.pk)

        for combo in existing_combos:
            existing_ids = set(combo.variations.values_list('id', flat=True))
            if existing_ids == current_ids:
                raise ValidationError("This combination of variations already exists for this product.")

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        if not self.sku and self.pk and self.variations.exists():
            variation_labels = [v.variation_value.upper().strip() for v in self.variations.all()]
            raw_sku = f"{self.product.slug}-{'-'.join(sorted(variation_labels))}"
            self.sku = slugify(raw_sku)
            super().save(update_fields=['sku'])

        total_stock = VariationCombination.objects.filter(
            product=self.product,
            is_active=True
        ).aggregate(total=models.Sum('stock'))['total'] or 0

        if self.product.stock != total_stock:
            self.product.stock = total_stock
            self.product.save(update_fields=['stock'])


class VariationOptionSet(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variation_option_sets')
    created_date = models.DateTimeField(auto_now_add=True)

    def clean(self):
        if self.product.product_type != 'combination':
            raise ValidationError("Variation sets are only allowed for combination products")
        
        if self.options.count() < 2:
            raise ValidationError("Combination products require two or more variation types.")

    def __str__(self):
        return f"Variation Setup for {self.product.product_name}"


class VariationOption(models.Model):
    set = models.ForeignKey(VariationOptionSet, on_delete=models.CASCADE, related_name='options')
    variation_type = models.CharField(max_length=100)
    values = models.TextField()

    def clean(self):
        entries = [v.strip() for v in self.values.split(",") if v.strip()]
        if not entries:
            raise ValidationError("Variation values must not be empty.")
        if len(set(entries)) < len(entries):
            raise ValidationError("Variation values must not contain duplicates.")

    def __str__(self):
        return f"{self.variation_type} Options for {self.set.product.product_name}"


class PricingRule(models.Model):
    variation_type = models.CharField(max_length=100)
    value = models.CharField(max_length=100)
    price_adjustment = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        unique_together = ('variation_type', 'value')
        ordering = ['variation_type', 'value']

    def __str__(self):
        return f"{self.variation_type}:{self.value} → ${self.price_adjustment}"


@receiver([post_save, post_delete], sender=VariationCombination)
def update_product_stock_from_combinations(sender, instance, **kwargs):
    product = instance.product
    total = VariationCombination.objects.filter(
        product=product, is_active=True
    ).aggregate(total=models.Sum('stock'))['total'] or 0
    product.stock = total
    product.save(update_fields=['stock'])


@receiver(post_delete, sender=Variation)
def update_stock_on_delete(sender, instance, **kwargs):
    if instance.product.product_type == 'variation':
        total_stock = Variation.objects.filter(
            product=instance.product,
            is_active=True
        ).aggregate(total=Sum('stock'))['total'] or 0
        instance.product.stock = total_stock
        instance.product.save(update_fields=['stock'])