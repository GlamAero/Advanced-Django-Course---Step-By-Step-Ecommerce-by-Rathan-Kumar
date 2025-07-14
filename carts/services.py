from decimal import Decimal
from django.conf import settings

class ShippingCalculator:
    @staticmethod
    def calculate(cart, shipping_method='standard', address=None):
        """
        Calculate shipping costs based on:
        - Cart weight
        - Shipping method
        - Destination
        - Package dimensions (not implemented)
        """
        # Base costs by method
        method_costs = {
            'standard': Decimal('5.00'),
            'expedited': Decimal('12.00'),
            'priority': Decimal('20.00'),
        }
        
        # Get total cart weight
        total_weight = sum(
            item.product.weight * item.quantity 
            for item in cart.cart_items.filter(is_active=True)
        ) or Decimal('0.00')
        
        # Weight-based cost ($0.75 per kg)
        weight_cost = total_weight * Decimal('0.75')
        
        # International shipping premium
        is_international = False
        if address and address.country and address.country != settings.DOMESTIC_COUNTRY:
            is_international = True
            
        international_surcharge = Decimal('15.00') if is_international else Decimal('0.00')
        
        # Fragile items premium
        has_fragile_items = any(
            item.product.is_fragile 
            for item in cart.cart_items.filter(is_active=True)
        )
        fragile_surcharge = Decimal('7.50') if has_fragile_items else Decimal('0.00')
        
        # Calculate total
        base_cost = method_costs.get(shipping_method, Decimal('5.00'))
        return base_cost + weight_cost + international_surcharge + fragile_surcharge