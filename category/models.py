from django.db import models
from django.urls import reverse
from django.utils.text import slugify
from mptt.models import MPTTModel, TreeForeignKey
from django.core.exceptions import ValidationError
from django.utils import timezone

class Category(MPTTModel):
    category_name = models.CharField(
        max_length=50,
        unique=True,
        help_text="Required and unique"
    )
    slug = models.SlugField(
        max_length=100,
        unique=True,
        help_text="Automatically generated from category name"
    )
    description = models.TextField(
        max_length=500,
        blank=True,
        help_text="Optional description for SEO"
    )
    cat_image = models.ImageField(
        upload_to='categories/%Y/%m/%d/',
        blank=True,
        null=True,
        help_text="Upload a category image"
    )
    parent = TreeForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='subcategories',
        help_text="Select parent category for hierarchical structure"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Toggle category visibility"
    )
    featured = models.BooleanField(
        default=False,
        help_text="Feature this category on homepage"
    )
    meta_title = models.CharField(
        max_length=100,
        blank=True,
        help_text="SEO meta title (optional)"
    )
    meta_description = models.TextField(
        max_length=300,
        blank=True,
        help_text="SEO meta description (optional)"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        editable=False
    )
    updated_at = models.DateTimeField(
        auto_now=True
    )

    class MPTTMeta:
        order_insertion_by = ['category_name']
        verbose_name_plural = 'categories'

    class Meta:
        verbose_name = 'Category'
        verbose_name_plural = 'Categories'
        ordering = ['tree_id', 'lft']
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['is_active']),
            models.Index(fields=['featured']),
        ]

    def __str__(self):
        return self.category_name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.category_name)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('products_by_category', args=[self.slug])

    def get_full_path(self):
        ancestors = self.get_ancestors(include_self=True)
        return ' > '.join(c.category_name for c in ancestors)

    def clean(self):
        # Prevent category from being its own parent
        if self.parent and self.parent.id == self.id:
            raise ValidationError("A category cannot be its own parent")
            
        # Prevent circular parent relationships
        if self.parent and self.parent in self.get_descendants():
            raise ValidationError("Circular parent relationship detected")

    @property
    def image_url(self):
        if self.cat_image and hasattr(self.cat_image, 'url'):
            return self.cat_image.url
        return '/static/images/default-category.png'

    def get_product_count(self):
        return self.products.filter(is_available=True).count()
    