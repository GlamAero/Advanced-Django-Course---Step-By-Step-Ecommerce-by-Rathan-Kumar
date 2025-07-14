def apply_pricing_rules(base_price, variations):
    price = base_price
    for v in variations:
        if v.variation_category == 'Size' and v.variation_value == 'XL':
            price += 500
        elif v.variation_category == 'Material' and v.variation_value == 'Cotton':
            price += 200
    return price