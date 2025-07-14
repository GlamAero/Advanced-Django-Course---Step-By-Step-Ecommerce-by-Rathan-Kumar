from django.contrib import admin
from .forms import VariationAdminForm
from store.models import Variation

# @admin.register(Variation)
class VariationAdmin(admin.ModelAdmin):
    form = VariationAdminForm
    list_display = (
        'product',
        'variation_type',
        'variation_value',
        'price',
        'stock',
        'is_active',
    )
    list_editable = ('price', 'stock', 'is_active')
    list_filter = ('product', 'variation_type', 'is_active')
    search_fields = (
        'product__product_name',
        'variation_type',
        'variation_value'
    )



    