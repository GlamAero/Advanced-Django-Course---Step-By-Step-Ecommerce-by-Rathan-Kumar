from django.contrib import admin
from django.db import models
from itertools import product as cartesian_product
from ..models import VariationCombination

@admin.action(description="Reset stock to zero")
def reset_stock(modeladmin, request, queryset):
    """
    Admin action to reset the stock of selected products to zero.
    """
    count = queryset.update(stock=0)
    modeladmin.message_user(
        request,
        f"✅ Stock reset to zero for {count} product(s)."
    )

@admin.action(description="Auto-generate all valid variation combinations")
def bulk_create_combinations(modeladmin, request, queryset):
    """
    Admin action to generate all valid variation combinations based on
    variation categories for selected products.
    """
    created_total = 0

    for product in queryset:
        # Get distinct variation categories linked to the product
        categories = product.variation_set.values_list('variation_category', flat=True).distinct()

        if not categories:
            continue  # Skip if no variation categories present

        # Group variations by category
        variation_groups = [
            list(product.variation_set.filter(variation_category=cat))
            for cat in categories
        ]

        # Cartesian product gives all possible combinations of variations
        for combo in cartesian_product(*variation_groups):
            # Check if this exact combination already exists
            existing = VariationCombination.objects.filter(product=product)\
                .filter(variations__in=combo)\
                .annotate(num=models.Count('variations'))\
                .filter(num=len(combo))

            if not existing.exists():
                # Create the new variation combination
                new_combo = VariationCombination.objects.create(product=product, stock=0)
                new_combo.variations.set(combo)
                created_total += 1

    modeladmin.message_user(
        request,
        f"✅ Created {created_total} new variation combination(s)."
    )