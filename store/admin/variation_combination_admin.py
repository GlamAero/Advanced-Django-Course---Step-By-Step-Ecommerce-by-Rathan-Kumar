from django.contrib import admin
from .forms import VariationCombinationForm
from ..models import VariationCombination

class VariationCombinationAdmin(admin.ModelAdmin):
    """Admin configuration for managing variation combinations."""

    # Use the custom form with validation logic
    form = VariationCombinationForm

    # Define fields visible in the list view
    list_display = (
        'product',
        'get_variations',
        'price',
        'stock',
        'is_active',
        'created_date',
    )

    # Allow quick editing of activation status directly from list view
    list_editable = ('is_active',)

    # Sidebar filters for narrowing down combinations
    list_filter = ('product', 'is_active', 'created_date')

    def get_variations(self, obj):
        """
        Display readable summary of variation values associated with this combination.
        Example: Size:M, Color:Red
        """
        return ", ".join(f"{v.variation_category}:{v.variation_value}" for v in obj.variations.all())

    get_variations.short_description = 'Variations'

    def save_model(self, request, obj, form, change):
        """
        After saving a variation combination, recalculate the parent product’s stock.
        """
        super().save_model(request, obj, form, change)
        obj.product.stock = sum(
            combo.stock or 0 for combo in obj.product.variation_combinations.all()
        )
        obj.product.save(update_fields=['stock'])

    def delete_model(self, request, obj):
        """
        After deleting a combination, recalculate the parent product’s stock.
        """
        super().delete_model(request, obj)
        obj.product.stock = sum(
            combo.stock or 0 for combo in obj.product.variation_combinations.all()
        )
        obj.product.save(update_fields=['stock'])