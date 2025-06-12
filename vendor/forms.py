from django import forms
from vendor.models import VendorVariationCombination, VendorProduct


class VariationStockForm(forms.ModelForm):
    category = forms.CharField(max_length=100)  # Vendor selects category for stock assignment
    quantity = forms.IntegerField(min_value=0)  # Prevent negative stock values

    class Meta:
        model = VendorVariationCombination
        fields = ["product", "variations"]


class ProductStockForm(forms.ModelForm):
    class Meta:
        model = VendorProduct
        fields = ["name", "stock_quantity", "price", "image"]

        widgets = {
            "name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "e.g. Wireless Mouse"
            }),
            "stock_quantity": forms.NumberInput(attrs={
                "class": "form-control",
                "min": "0",
                "placeholder": "Enter stock quantity"
            }),
            "price": forms.NumberInput(attrs={
                "class": "form-control",
                "step": "0.01",
                "placeholder": "e.g. 2999.99"
            }),
            "image": forms.ClearableFileInput(attrs={
                "class": "form-control"
            }),
        }

        labels = {
            "name": "Product Name",
            "stock_quantity": "Stock Quantity",
            "price": "Price (₦)",
            "image": "Product Image",
        }

        help_texts = {
            "stock_quantity": "Only positive integers allowed.",
            "price": "Enter product price in Naira (₦).",
            "image": "Optional. Upload a product image.",
        }

    def clean_stock_quantity(self):
        stock = self.cleaned_data.get("stock_quantity")
        if stock is None:
            raise forms.ValidationError("This field is required.")
        if stock < 0:
            raise forms.ValidationError("Stock quantity cannot be negative.")
        return stock

    def clean_price(self):
        price = self.cleaned_data.get("price")
        if price is None:
            raise forms.ValidationError("This field is required.")
        if price < 0:
            raise forms.ValidationError("Price cannot be negative.")
        return price

