from django.contrib import admin
from .models import Product, Vendor, Variation, VariationCombination

# Base admin class to make models read-only
class ReadOnlyAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    # def has_change_permission(self, request, obj=None):
    #     return False

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Product)
class ProductAdmin(ReadOnlyAdmin):
    list_display = ['vendor', 'product_name', 'stock_quantity', 'price', 'is_available']
    readonly_fields = [f.name for f in Product._meta.fields]


@admin.register(Variation)
class VariationAdmin(ReadOnlyAdmin):
    list_display = ['product', 'variation_value', 'stock_quantity', 'price']
    readonly_fields = [f.name for f in Variation._meta.fields]


@admin.register(VariationCombination)
class VariationCombinationAdmin(ReadOnlyAdmin):
    list_display = ['product', 'stock_per_category', 'date_stock_created']
    readonly_fields = [f.name for f in VariationCombination._meta.fields]


@admin.register(Vendor)
class VendorAdmin(ReadOnlyAdmin):
    list_display = ['email', 'business_name', 'is_verified', 'is_active']
    readonly_fields = [f.name for f in Vendor._meta.fields]
