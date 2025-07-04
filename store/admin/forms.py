from django import forms
from django.core.exceptions import ValidationError
from ..models import Product, Variation, VariationCombination
from django.forms.widgets import Select


# ——————————————————————————————————————
# ProductForm
# ——————————————————————————————————————
class ProductForm(forms.ModelForm):
    """
    Validates product data before saving.
    Ensures that simple products must have a price.
    """
    class Meta:
        model = Product
        fields = '__all__'

    def clean(self):
        cleaned_data = super().clean()
        product_type = cleaned_data.get('product_type') or getattr(self.instance, 'product_type', 'simple')
        price = cleaned_data.get('price')

        # Require price for products with no variations
        if product_type == 'simple' and not price:
            raise ValidationError("Price is required for simple products with no variations.")

        return cleaned_data

# ——————————————————————————————————————
# VariationForm
# ——————————————————————————————————————
class ProductTypeAwareSelect(Select):
    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex=subindex, attrs=attrs)
        if value:
            try:
                product = Product.objects.get(id=value)
                option['attrs']['data-product-type'] = product.product_type
            except Product.DoesNotExist:
                pass
        return option


class ProductTypeAwareSelect(Select):
    """Custom select that adds data-product-type to each option (for JavaScript filtering)."""
    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex=subindex, attrs=attrs)
        if value:
            try:
                product = Product.objects.only('product_type').get(id=value)
                option['attrs']['data-product-type'] = product.product_type
            except Product.DoesNotExist:
                pass
        return option

class VariationForm(forms.ModelForm):
    """
    Admin form for Variation that:
    - Introduces 'product_type' dropdown for client-side filtering
    - Populates 'product' dropdown with variation/combination products
    - Removes 'price' field server-side if product type is 'combination'
    """
    product_type = forms.ChoiceField(
        label="Product Type",
        required=False,
        choices=[
            ('', '— Select Type —'),
            ('variation', 'Variation'),
            ('combination', 'Combination'),
        ]
    )

    class Meta:
        model = Variation
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Prefetch valid products
        products = Product.objects.filter(
            product_type__in=['variation', 'combination']
        ).only('id', 'product_name', 'product_type')
        self.fields['product'].queryset = products

        # Replace 'product' field widget with enhanced select (for JS)
        product_choices = [('', '---------')] + [
            (p.id, f"{p.product_name} [{p.product_type}]") for p in products
        ]
        self.fields['product'].widget = ProductTypeAwareSelect(
            choices=product_choices,
            attrs={'id': 'id_product'}
        )

        # Reorder fields: product_type appears before product
        reordered = {
            'product_type': self.fields.pop('product_type'),
            'product': self.fields.pop('product'),
        }
        reordered.update(self.fields)
        self.fields = reordered

        # Remove price field if editing and product is 'combination'
        instance = kwargs.get('instance')
        product = instance.product if instance else None
        if product and product.product_type == 'combination':
            self.fields.pop('price', None)

    def clean(self):
        cleaned_data = super().clean()
        product = cleaned_data.get('product')
        stock = cleaned_data.get('stock')

        if not product:
            return cleaned_data

        if product.product_type == 'combination':
            return cleaned_data  # No price or stock enforcement needed

        if product.product_type == 'variation':
            if stock is None:
                raise ValidationError("Stock is required for variation-based products.")
            if stock > product.stock:
                raise ValidationError(
                    f"Variation stock ({stock}) cannot exceed product stock ({product.stock})."
                )

        return cleaned_data

# ——————————————————————————————————————
# VariationCombinationForm
# ——————————————————————————————————————
class VariationCombinationForm(forms.ModelForm):
    """
    Custom form for VariationCombination that:
    - Validates relationship integrity.
    - Filters variations to only those linked to products of type 'combination'.
    """
    """Custom form that restricts selection to valid products and variations."""
    class Meta:
        model = VariationCombination
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Step 1: Filter the variations field to only include those from 'combination' product
        self.fields['variations'].queryset = Variation.objects.filter(
            product__product_type='combination'
        )

        # Filter the product field to only show combination-type products
        self.fields['product'].queryset = Product.objects.filter(
            product_type__in=['variation', 'combination']
        )

        # Step 2: Ensure related variation widget allows "+" icon
        self.fields['variations'].widget.can_add_related = True
        self.fields['product'].widget.can_add_related = True


    def clean(self):
        # Step 3: Validate submitted data
        cleaned_data = super().clean()
        product = cleaned_data.get('product')
        variations = cleaned_data.get('variations')
        stock = cleaned_data.get('stock')

        # Validate product and variations presence
        if not product or not variations:
            raise ValidationError("Please select a product and at least one variation.")

        # Step 4: Ensure all selected variations belong to the selected product
        for v in variations:
            if v.product != product:
                raise ValidationError(f"The variation '{v}' does not belong to the selected product.")

        # Step 5: Validate stock constraint against product's stock
        if stock is not None and stock > product.stock:
            raise ValidationError(f"Combination stock ({stock}) cannot exceed product stock ({product.stock}).")

        return cleaned_data


