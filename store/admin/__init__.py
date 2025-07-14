from django.contrib import admin

# Import modular admin classes for each model
from .product_admin import ProductAdmin
from .variation_admin import VariationAdmin
from .variation_combination_admin import VariationCombinationAdmin
from .variation_option_set_admin import VariationOptionSetAdmin

# Import model definitions
from ..models import Product, Variation, VariationCombination, VariationOptionSet

# Register models with their respective admin configurations
admin.site.register(Product, ProductAdmin)
admin.site.register(Variation, VariationAdmin)
admin.site.register(VariationCombination, VariationCombinationAdmin)
admin.site.register(VariationOptionSet, VariationOptionSetAdmin)
