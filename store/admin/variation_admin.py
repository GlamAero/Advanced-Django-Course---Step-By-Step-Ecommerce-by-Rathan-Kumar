from django.contrib import admin
from .forms import VariationForm
from .filters import ProductTypeFilter


class ProductTypeFilter(admin.SimpleListFilter):
    """
    Adds a custom filter to allow filtering variations by their product's type.
    """
    title = 'Product Type'
    parameter_name = 'product_type'

    def lookups(self, request, model_admin):
        return [
            ('variation', 'Products with Variations'),
            ('combination', 'Products with Variation Combinations'),
        ]

    def queryset(self, request, queryset):
        value = self.value()
        if value:
            return queryset.filter(product__product_type=value)
        return queryset


from django.contrib import admin
from .forms import VariationForm
from .filters import ProductTypeFilter
from ..models import Variation

class VariationAdmin(admin.ModelAdmin):
    """
    Admin configuration for managing individual product variations.
    Includes dynamic filtering, smart field layout, and stock recalculation.
    """

    form = VariationForm

    # Fields displayed in the admin changelist view
    list_display = (
        'product',
        'variation_category',
        'variation_value',
        'price',
        'stock',
        'is_active',
    )

    list_editable = ('is_active',)  # Allow status toggle inline

    # Sidebar filters for convenience
    list_filter = (
        'variation_category',
        'variation_value',
        ProductTypeFilter,  # Custom filter: shows variations by product type
    )

    # Admin form field layout — ensures product_type appears before product
    fieldsets = (
        (None, {
            'fields': (
                'product_type',  # Virtual field injected via form
                'product',
                'variation_category',
                'variation_value',
                'price',
                'stock',
                'is_active',
            )
        }),
    )

    def save_model(self, request, obj, form, change):
        """
        After saving, recalculate and update the parent product’s total stock.
        """
        super().save_model(request, obj, form, change)
        obj.product.stock = sum(v.stock or 0 for v in obj.product.variation_set.all())
        obj.product.save(update_fields=['stock'])

    def delete_model(self, request, obj):
        """
        After deletion, recalculate and update the parent product’s stock.
        """
        super().delete_model(request, obj)
        obj.product.stock = sum(v.stock or 0 for v in obj.product.variation_set.all())
        obj.product.save(update_fields=['stock'])

    class Media:
        # Load the JS that handles:
        # - filtering product dropdown based on product_type
        # - hiding price field for combination-type products
        js = (
            'admin/js/product_type_filter_live.js',
            'admin/js/toggle_price_field.js',
        )






