from django.contrib import admin

class LowStockFilter(admin.SimpleListFilter):
    """
    Sidebar filter for identifying products with low inventory.

    Displays a filter option labeled "⚠ Low Stock (≤5)" that,
    when selected, narrows the list to products with stock ≤ 5.
    """
    title = 'Stock Level'
    parameter_name = 'stock_status'

    def lookups(self, request, model_admin):
        return [
            ('low', '⚠ Low Stock (≤5)'),
        ]

    def queryset(self, request, queryset):
        value = self.value()
        if value == 'low':
            return queryset.filter(stock__lte=5)
        return queryset
    

class ProductTypeFilter(admin.SimpleListFilter):
    """
    Custom admin filter to allow filtering by the product's type.
    """
    title = 'Product Type'
    parameter_name = 'product_type'

    def lookups(self, request, model_admin):
        return [
            ('variation', 'Products with Variations'),
            ('combination', 'Products with Variation Combinations'),
        ]

    def queryset(self, request, queryset):
        value = self.value()
        if value:
            return queryset.filter(product__product_type=value)
        return queryset