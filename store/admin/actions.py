from django.contrib import admin
from django.db import models
from itertools import product as cartesian_product
from store.models import VariationCombination

@admin.action(description="Reset stock to zero")
def reset_stock(modeladmin, request, queryset):
    updated = queryset.update(stock=0)
    modeladmin.message_user(
        request,
        f"✅ Stock reset to zero for {updated} product(s).",
        level='success'
    )

@admin.action(description="Auto-generate all valid variation combinations")
def bulk_create_combinations(modeladmin, request, queryset):
    created_total = 0
    for product in queryset:
        categories = product.variation_set.values_list(
            'variation_type', flat=True
        ).distinct()
        
        if not categories:
            continue
        
        variation_groups = [
            list(product.variation_set.filter(variation_type=cat))
            for cat in categories
        ]
        
        for combo in cartesian_product(*variation_groups):
            existing = VariationCombination.objects.filter(
                product=product,
                variations__in=combo
            ).annotate(
                num_vars=models.Count('variations')
            ).filter(num_vars=len(combo))
            
            if not existing.exists():
                new_combo = VariationCombination.objects.create(
                    product=product, 
                    stock=0
                )
                new_combo.variations.set(combo)
                created_total += 1

    modeladmin.message_user(
        request,
        f"✅ Created {created_total} new variation combination(s).",
        level='success'
    )

    