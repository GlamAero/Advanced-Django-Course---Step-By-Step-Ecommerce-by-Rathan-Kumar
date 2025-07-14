from itertools import product as cartesian
from store.models import Variation, VariationCombination
from store.utils.sku_generator import generate_sku

def generate_combinations(option_set):
    options = {}
    for opt in option_set.options.all():
        values = [v.strip() for v in opt.values.split(',') if v.strip()]
        if values:
            options[opt.variation_type] = values

    combos = list(cartesian(*options.values()))
    for combo_values in combos:
        variations = []
        for category, value in zip(options.keys(), combo_values):
            variation, _ = Variation.objects.get_or_create(
                product=option_set.product,
                variation_type=category,
                variation_value=value,
                defaults={'is_active': True}
            )
            variations.append(variation)

        sku = generate_sku(option_set.product, variations)
        
        combo, created = VariationCombination.objects.get_or_create(
            product=option_set.product,
            sku=sku,
            defaults={
                'stock': 0,
                'price': 0.00,
                'is_active': True
            }
        )
        combo.variations.set(variations)
        combo.save()


        