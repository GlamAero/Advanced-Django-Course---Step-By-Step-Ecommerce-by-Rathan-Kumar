from django import forms
from django.core.exceptions import ValidationError
from store.models import Product, Variation, VariationCombination, VariationOption

class ProductAdminForm(forms.ModelForm):
    expected_stock = forms.IntegerField(label="Expected Stock", required=False, disabled=True)

    class Meta:
        model = Product
        fields = '__all__'
        widgets = {
            'vendor': forms.HiddenInput()
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        product = self.instance
        request = kwargs.pop('request', None)

        # Set current user as vendor if new product
        if not product.pk and request and request.user.is_vendor():
            self.initial['vendor'] = request.user.vendorprofile

        if product.pk and product.product_type in ['variation', 'combination']:
            if product.product_type == 'variation':
                total = product.variations.filter(is_active=True).aggregate(
                    total=Sum('stock')
                )['total'] or 0
            else:
                total = product.variation_combinations.filter(
                    is_active=True
                ).aggregate(total=Sum('stock'))['total'] or 0

            self.fields['expected_stock'].initial = total
            self.fields['stock'].disabled = True


class VariationOptionForm(forms.ModelForm):
    class Meta:
        model = VariationOption
        fields = ['variation_type', 'values']
        labels = {
            'variation_type': 'Variation Type',
            'values': 'Values (comma-separated)',
        }
        help_texts = {
            'variation_type': 'e.g. Color, Size, Material',
            'values': 'e.g. Red, Blue, Black',
        }

    def clean_variation_type(self):
        value = self.cleaned_data.get('variation_type', '').strip()
        if not value:
            raise ValidationError("Variation type is required.")
        return value

    def clean_values(self):
        raw = self.cleaned_data.get('values', '')
        entries = [v.strip() for v in raw.split(',') if v.strip()]
        if not entries:
            raise ValidationError("Variation values cannot be empty.")
        if len(set(entries)) < len(entries):
            raise ValidationError("Duplicate variation values are not allowed.")
        return ", ".join(entries)
    
    