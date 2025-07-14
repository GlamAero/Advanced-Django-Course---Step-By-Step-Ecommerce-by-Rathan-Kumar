# coupons/models.py
from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from store.models import Product, Category

User = get_user_model()

class Coupon(models.Model):
    DISCOUNT_TYPES = (
        ('percentage', 'Percentage'),
        ('fixed', 'Fixed Amount'),
    )
    
    APPLIES_TO_CHOICES = (
        ('all', 'All Products'),
        ('products', 'Specific Products'),
        ('categories', 'Product Categories'),
    )
    
    code = models.CharField(max_length=50, unique=True, db_index=True)
    description = models.TextField(blank=True)
    discount_type = models.CharField(
        max_length=20, 
        choices=DISCOUNT_TYPES, 
        default='percentage'
    )
    discount = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    max_discount = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    min_purchase = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Minimum order amount to apply coupon"
    )
    applies_to = models.CharField(
        max_length=20, 
        choices=APPLIES_TO_CHOICES, 
        default='all'
    )
    products = models.ManyToManyField(
        Product, 
        blank=True,
        related_name='coupons'
    )
    categories = models.ManyToManyField(
        Category, 
        blank=True,
        related_name='coupons'
    )
    active = models.BooleanField(default=True)
    single_use = models.BooleanField(default=False)
    valid_from = models.DateTimeField(default=timezone.now)
    valid_to = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    users_used = models.ManyToManyField(
        User, 
        blank=True,
        related_name='coupons_used'
    )
    use_count = models.PositiveIntegerField(default=0, editable=False)

    class Meta:
        ordering = ['-valid_to']
        verbose_name = 'Coupon'
        verbose_name_plural = 'Coupons'
        indexes = [
            models.Index(fields=['active']),
            models.Index(fields=['valid_to']),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(valid_to__gt=models.F('valid_from')),
                name="coupon_valid_dates"
            )
        ]

    def __str__(self):
        return f"{self.code} ({self.get_discount_type_display()})"
    
    def clean(self):
        if self.valid_to and self.valid_to < timezone.now():
            self.active = False
        if self.valid_from and self.valid_to:
            if self.valid_from > self.valid_to:
                raise ValidationError("Valid from date cannot be after valid to date")
    
    def is_valid_for_user(self, user, cart_total=0):
        """Check if coupon is valid for specific user and cart"""
        # Check validity period
        now = timezone.now()
        if not (self.valid_from <= now <= self.valid_to):
            return False
            
        # Check if active
        if not self.active:
            return False
            
        # Check minimum purchase
        if self.min_purchase and cart_total < self.min_purchase:
            return False
            
        # Check single use restriction
        if self.single_use and user in self.users_used.all():
            return False
            
        return True
    
    def apply_discount(self, amount):
        """Apply coupon discount to amount"""
        if self.discount_type == 'percentage':
            discounted = amount * (1 - self.discount / 100)
            if self.max_discount:
                max_discount = min(amount - discounted, self.max_discount)
                return amount - max_discount
            return discounted
        else:
            return max(0, amount - self.discount)
        