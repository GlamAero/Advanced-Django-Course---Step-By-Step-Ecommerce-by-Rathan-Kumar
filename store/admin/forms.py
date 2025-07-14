from django import forms
from django.core.exceptions import ValidationError
from store.models import Product, Variation, VariationCombination, VariationOption

class ProductAdminForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = '__all__'
        widgets = {
            'vendor': forms.HiddenInput()
        }

    def __init__(self, *args, **kwargs):
        request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        
        if not self.instance.pk and request and request.user.is_vendor():
            self.fields['vendor'].initial = request.user.vendorprofile
            self.fields['vendor'].disabled = True

    def clean(self):
        cleaned_data = super().clean()
        product_type = cleaned_data.get("product_type")
        price = cleaned_data.get("price")
        
        if product_type == "simple" and not price:
            raise ValidationError({"price": "Price is required for simple products."})
        return cleaned_data


class VariationAdminForm(forms.ModelForm):
    class Meta:
        model = Variation
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['product'].queryset = Product.objects.filter(
            product_type__in=['variation', 'combination']
        )


class VariationCombinationAdminForm(forms.ModelForm):
    class Meta:
        model = VariationCombination
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["product"].queryset = Product.objects.filter(
            product_type="combination"
        )
        self.fields["variations"].queryset = Variation.objects.filter(
            product__product_type="combination"
        )

    def clean(self):
        cleaned_data = super().clean()
        product = cleaned_data.get("product")
        variations = cleaned_data.get("variations")
        
        if product and product.product_type != "combination":
            raise ValidationError({
                "product": "Only combination-type products can have variation combinations."
            })
            
        if variations and variations.count() < 2:
            raise ValidationError({
                "variations": "A combination must include at least two variations."
            })
            
        mismatched = [v for v in variations if v.product != product]
        if mismatched:
            names = ", ".join(str(v) for v in mismatched)
            raise ValidationError({
                "variations": f"Variations do not belong to product: {names}"
            })
            
        return cleaned_data