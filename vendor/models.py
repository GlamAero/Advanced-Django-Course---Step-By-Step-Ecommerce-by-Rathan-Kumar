from django.db import models
from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin, Group, Permission
from django.urls import reverse
from category.models import Category
from django.core.validators import MinValueValidator, MaxValueValidator


class VendorManager(BaseUserManager):
    def create_vendor(self, email, business_name, password=None, **extra_fields):
        if not email:
            raise ValueError("The Email field is required.")
        if not business_name:
            raise ValueError("The Business Name field is required.")
        if not password:
            raise ValueError("The Password field is required.")

        email = self.normalize_email(email)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('is_vendor', True)
        extra_fields['is_staff'] = False
        extra_fields['is_superuser'] = False

        vendor = self.model(email=email, business_name=business_name, **extra_fields)
        vendor.set_password(password)
        vendor.save(using=self._db)
        return vendor

    def create_superuser(self, email, business_name, password=None, **extra_fields):
        if not email:
            raise ValueError("The Email field is required.")
        if not business_name:
            raise ValueError("The Business Name field is required.")
        if not password:
            raise ValueError("The Password field is required.")

        email = self.normalize_email(email)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_vendor', False)

        if extra_fields.get('is_staff') is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get('is_superuser') is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        user = self.model(email=email, business_name=business_name, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user


class Vendor(AbstractBaseUser, PermissionsMixin):
    first_name = models.CharField(max_length=30, blank=True)
    last_name = models.CharField(max_length=30, blank=True)
    email = models.EmailField(unique=True, null=True)  # change to 'email = models.EmailField(unique=True)' in production
    bio = models.TextField(blank=True, null=True) 
    business_name = models.CharField(max_length=255, default="Unnamed Vendor")
    profile_picture = models.ImageField(upload_to='vendor_profile_pictures/', blank=True, null=True)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    is_verified = models.BooleanField(default=False)
    is_vendor = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)
    date_modified = models.DateTimeField(auto_now=True)
    address = models.CharField(max_length=255, blank=True, null=True)
    website = models.URLField(max_length=200, blank=True, null=True)

    # ✅ Resolve conflict with Account model
    groups = models.ManyToManyField(
        Group,
        related_name='vendor_user_set',
        blank=True,
        help_text='The groups this vendor belongs to.',
        verbose_name='vendor groups'
    )
    user_permissions = models.ManyToManyField(
        Permission,
        related_name='vendor_user_permissions',
        blank=True,
        help_text='Specific permissions for this vendor.',
        verbose_name='vendor user permissions'
    )

    objects = VendorManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["business_name"]

    def __str__(self):
        return self.business_name

    def get_absolute_url(self):
        return reverse("vendor_detail", args=[str(self.id)])


class Product(models.Model):
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name="products")
    product_name = models.CharField(max_length=200, unique=True)
    slug = models.SlugField(max_length=200, unique=True)
    description = models.TextField()
    stock_quantity = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)])
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    images = models.ImageField(upload_to='photos/products', blank=True, null=True)
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0.00, validators=[MinValueValidator(0), MaxValueValidator(100)])
    date_stock_created = models.DateTimeField(auto_now_add=True)
    date_modified = models.DateTimeField(auto_now=True)
    is_available = models.BooleanField(default=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    is_featured = models.BooleanField(default=False)
    is_discounted = models.BooleanField(default=False)

    def get_url(self):
        return reverse('product_detail', args=[self.category.slug, self.slug])

    def get_discounted_price(self):
        if self.is_discounted and self.discount_percentage > 0:
            return self.price * (1 - self.discount_percentage / 100)
        return self.price

    def __str__(self):
        return f"{self.product_name} by {self.vendor.business_name}"


class VariationManager(models.Manager):
    def colors(self):
        return self.filter(variation_category='color', is_active=True)

    def sizes(self):
        return self.filter(variation_category='size', is_active=True)


variation_category_choice = (
    ('color', 'Color'),
    ('size', 'Size'),
)


class Variation(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="variations")
    variation_category = models.CharField(max_length=100, choices=variation_category_choice)
    variation_value = models.CharField(max_length=100)
    stock_quantity = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)])
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    images = models.ImageField(upload_to="vendor_variation_images/", blank=True, null=True)
    is_active = models.BooleanField(default=True)
    date_stock_created = models.DateTimeField(auto_now_add=True)
    date_modified = models.DateTimeField(auto_now=True)
    is_available = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    is_discounted = models.BooleanField(default=False)

    objects = VariationManager()

    def get_discounted_price(self):
        if self.is_discounted and self.product.discount_percentage > 0:
            return self.price * (1 - self.product.discount_percentage / 100)
        return self.price

    def __str__(self):
        return f"{self.product.product_name} - {self.variation_value}"


class VariationCombination(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="variation_combinations")
    variations = models.ManyToManyField(Variation, related_name="variation_combinations")
    stock_per_category = models.JSONField(default=dict)
    date_stock_created = models.DateTimeField(auto_now_add=True)
    date_modified = models.DateTimeField(auto_now=True)
    is_featured = models.BooleanField(default=False)
    is_discounted = models.BooleanField(default=False)

    def set_stock(self, category, quantity):
        if quantity < 0:
            raise ValueError("Stock value cannot be negative.")
        self.stock_per_category[category] = quantity
        self.save()

    def reduce_stock(self, category, quantity):
        available = self.stock_per_category.get(category, 0)
        if available < quantity:
            raise ValueError("Not enough stock for category.")
        self.stock_per_category[category] = available - quantity
        self.save()

    def __str__(self):
        variations_str = ", ".join([v.variation_value for v in self.variations.all()])
        return f"{self.product.product_name} - {variations_str} (Stock: {self.stock_per_category})"
