
from django.contrib import admin
from django import forms
from .models import Product, Variation, VariationCombination

class ProductAdmin(admin.ModelAdmin):
    list_display = ('product_name', 'price', 'stock', 'modified_date', 'is_available')
    prepopulated_fields = {'slug': ('product_name',)}

class VariationAdmin(admin.ModelAdmin):
    list_display = ('product', 'variation_category', 'variation_value', 'is_active')
    list_editable = ('is_active',)
    list_filter = ('product', 'variation_category', 'variation_value')

class VariationCombinationForm(forms.ModelForm):
    class Meta:
        model = VariationCombination
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Remove the "+" add button for variations to prevent duplicate variations
        self.fields['variations'].widget.can_add_related = False

class VariationCombinationAdmin(admin.ModelAdmin):
    form = VariationCombinationForm
    list_display = ('product', 'get_variations', 'stock', 'is_active', 'created_date')
    list_editable = ('is_active',)
    list_filter = ('product', 'is_active', 'created_date')

    def get_variations(self, obj):
        return ", ".join([f"{v.variation_category}:{v.variation_value}" for v in obj.variations.all()])
    get_variations.short_description = 'Variations'

admin.site.register(Product, ProductAdmin)
admin.site.register(Variation, VariationAdmin)
admin.site.register(VariationCombination, VariationCombinationAdmin)