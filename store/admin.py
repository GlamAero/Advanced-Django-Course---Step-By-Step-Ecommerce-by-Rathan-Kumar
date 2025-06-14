from django.contrib import admin
from .models import Product, Variation


# Register your models here.

class ProductAdmin(admin.ModelAdmin):

    # 'list_display' specifies the fields to be displayed in the admin list view:
    list_display = ('product_name', 'price', 'stock', 'modified_date', 'is_available')

    # 'prepopulated_fields' is used to automatically fill the slug field based on the product name when creating a new product
    prepopulated_fields = {'slug': ('product_name',)}


class VariationAdmin(admin.ModelAdmin):

    # 'list_display' specifies the fields to be displayed in the admin list view:
    list_display = ('product', 'variation_category', 'variation_value', 'is_active')

    # this means to be able to edit the given('is_active') below in the admin front without needing to click on each variation to edit:
    list_editable = ('is_active',)

    # to filter the below('product', 'variation_category', 'variation_value') in the admin front without needing to click on each variation to filter: 
    list_filter = ('product', 'variation_category', 'variation_value')


admin.site.register(Product, ProductAdmin)
admin.site.register(Variation, VariationAdmin)