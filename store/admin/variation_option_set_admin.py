from django.contrib import admin
from django.urls import path, reverse
from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import render
from django.core.exceptions import ValidationError
from store.models import VariationOptionSet, VariationOption, Variation, VariationCombination
from store.utils.sku_generator import generate_sku
from itertools import product as cartesian
import csv

# @admin.register(VariationOptionSet)
class VariationOptionSetAdmin(admin.ModelAdmin):
    list_display = ('product', 'created_date')
    filter_horizontal = ('options',)
    readonly_fields = ('created_date',)

    def get_urls(self):
        return [
            path(
                '<int:set_id>/generate/',
                self.admin_site.admin_view(self.generate_combinations),
                name='generate_combinations'
            )
        ] + super().get_urls()

    def generate_combinations(self, request, set_id):
        option_set = VariationOptionSet.objects.get(id=set_id)
        options = {}
        
        for opt in option_set.options.all():
            values = [v.strip() for v in opt.values.split(',') if v.strip()]
            if values:
                options[opt.variation_type] = values
        
        if not options:
            self.message_user(request, "No valid options found", level='error')
            return HttpResponseRedirect(reverse(
                'admin:store_variationoptionset_change', 
                args=[set_id]
            ))
        
        combos = list(cartesian(*options.values()))
        generated = []
        
        for combo_values in combos:
            variations = []
            for var_type, val in zip(options.keys(), combo_values):
                variation, created = Variation.objects.get_or_create(
                    product=option_set.product,
                    variation_type=var_type,
                    variation_value=val,
                    defaults={'is_active': True}
                )
                variations.append(variation)
            
            sku = generate_sku(option_set.product, variations)
            
            combo, created = VariationCombination.objects.get_or_create(
                sku=sku,
                defaults={
                    'product': option_set.product,
                    'price': 0.00,
                    'stock': 0,
                    'is_active': True
                }
            )
            combo.variations.set(variations)
            combo.save()
            generated.append(combo)
        
        self.message_user(
            request, 
            f"Generated {len(generated)} combinations",
            level='success'
        )
        
        if request.GET.get('format') == 'csv':
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename="{option_set.product.slug}_combinations.csv"'
            writer = csv.writer(response)
            writer.writerow(['SKU', 'Variations', 'Price', 'Stock'])
            
            for combo in generated:
                variations = ', '.join(
                    f"{v.variation_type}={v.variation_value}" 
                    for v in combo.variations.all()
                )
                writer.writerow([combo.sku, variations, combo.price, combo.stock])
            
            return response
        
        return HttpResponseRedirect(reverse(
            'admin:store_variationcombination_changelist'
        ) + f'?product__id__exact={option_set.product.id}')
    


    