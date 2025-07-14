from django.contrib import admin
from django.utils.html import format_html
from .forms import VariationCombinationAdminForm
from store.models import VariationCombination

# @admin.register(VariationCombination)
class VariationCombinationAdmin(admin.ModelAdmin):
    form = VariationCombinationAdminForm
    list_display = (
        'product',
        'summary',
        'price',
        'stock',
        'is_active',
        'created_date',
    )
    list_editable = ('price', 'stock', 'is_active')
    list_filter = ('product', 'is_active')
    search_fields = ('product__product_name', 'sku')
    readonly_fields = ('created_date',)

    def summary(self, obj):
        variations = obj.variations.all()
        return ", ".join(
            f"{v.variation_type}: {v.variation_value}" 
            for v in variations
        )
    summary.short_description = "Variations"


    