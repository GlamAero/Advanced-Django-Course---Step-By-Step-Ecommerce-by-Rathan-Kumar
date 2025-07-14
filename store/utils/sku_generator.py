from django.utils.text import slugify

def generate_sku(product, variations):
    variation_values = sorted([
        v.variation_value.strip().lower().replace(" ", "-")
        for v in variations
    ])
    return slugify(f"{product.slug}-{'-'.join(variation_values)}")

