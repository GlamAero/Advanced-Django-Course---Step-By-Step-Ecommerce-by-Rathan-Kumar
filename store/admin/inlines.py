from django.contrib import admin
from django.utils.html import format_html
from store.models import Variation, VariationCombination

class VariationInline(admin.TabularInline):
    model = Variation
    extra = 1
    show_change_link = True
    fields = (
        'variation_type',
        'variation_value',
        'price',
        'stock',
        'colored_stock_display',
        'is_active',
    )
    readonly_fields = ('colored_stock_display',)

    def colored_stock_display(self, obj):
        stock = obj.stock or 0
        if stock == 0:
            return format_html('<span style="color:red;">⚠️ 0 units</span>')
        color = 'green' if stock > 10 else 'orange' if stock > 5 else 'red'
        return format_html(
            '<strong style="color:{};">{} units</strong>', 
            color, stock
        )
    colored_stock_display.short_description = "Stock Health"


class VariationCombinationInline(admin.TabularInline):
    model = VariationCombination
    extra = 1
    filter_horizontal = ('variations',)
    fields = ('variations', 'price', 'stock', 'is_active', 'sku')
    readonly_fields = ('sku',)


    