from django.db.models import Q
from store.models import VariationCombination
from django.core.exceptions import ValidationError

def deduct_product_stock(product, quantity, variations):
    """Deduct stock from product or variation combination"""
    if not variations:
        if product.stock < quantity:
            raise ValidationError(f"Insufficient stock for {product.product_name}")
        product.stock -= quantity
        product.save()
        return
    
    # Find matching combination
    combo = VariationCombination.objects.filter(
        product=product,
        variations__in=variations
    ).annotate(
        variation_count=Count('variations')
    ).filter(
        variation_count=len(variations)
    ).first()
    
    if not combo:
        raise ValidationError("No matching variation combination found")
    
    if combo.stock < quantity:
        raise ValidationError(f"Insufficient stock for combination: {combo.sku}")
    
    combo.stock -= quantity
    combo.save()


def add_product_stock(product, quantity, variations):
    """Add stock back to product or variation combination"""
    if not variations:
        product.stock += quantity
        product.save()
        return
    
    # Find matching combination
    combo = VariationCombination.objects.filter(
        product=product,
        variations__in=variations
    ).annotate(
        variation_count=Count('variations')
    ).filter(
        variation_count=len(variations)
    ).first()
    
    if not combo:
        raise ValidationError("No matching variation combination found")
    
    combo.stock += quantity
    combo.save()


    