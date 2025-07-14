from django.contrib import admin
from ..models import Variation, VariationCombination

class VariationInline(admin.TabularInline):
    """
    Inline form for managing individual variations directly from the product admin.
    """
    model = Variation
    extra = 1  # Show one empty form row by default

class VariationCombinationInline(admin.TabularInline):
    """
    Inline form for managing grouped variation combinations inside the product admin.
    Provides a multi-select interface for linking variations.
    """
    model = VariationCombination
    extra = 1
    filter_horizontal = ('variations',)  # Enable dual list for selecting related variations