from store.models import PricingRule

def apply_pricing_rules(base_price, variations):
    adjusted_price = base_price
    for v in variations:
        rule = PricingRule.objects.filter(
            variation_type__iexact=v.variation_type,
            value__iexact=v.variation_value
        ).first()

        if rule:
            adjusted_price += rule.price_adjustment
    return adjusted_price

    