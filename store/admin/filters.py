from django.contrib import admin

class LowStockFilter(admin.SimpleListFilter):
    title = 'Stock Level'
    parameter_name = 'stock_status'

    def lookups(self, request, model_admin):
        return [
            ('low', '⚠ Low Stock (≤5)'),
        ]

    def queryset(self, request, queryset):
        if self.value() == 'low':
            return queryset.filter(stock__lte=5)
        return queryset
    

class VendorFilter(admin.SimpleListFilter):
    title = 'Vendor'
    parameter_name = 'vendor'

    def lookups(self, request, model_admin):
        vendors = set([p.vendor for p in model_admin.model.objects.all()])
        return [(v.id, v.company_name) for v in vendors]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(vendor__id=self.value())
        return queryset
    

    