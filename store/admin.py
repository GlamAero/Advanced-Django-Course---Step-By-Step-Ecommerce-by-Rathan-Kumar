from django.contrib import admin
from .models import Product


# Register your models here.

class ProductAdmin(admin.ModelAdmin):

    # 'list_display' specifies the fields to be displayed in the admin list view
    list_display = ('product_name', 'price', 'stock', 'modified_date', 'is_available')

    # 'prepopulated_fields' is used to automatically fill the slug field based on the product name when creating a new product
    prepopulated_fields = {'slug': ('product_name',)}


admin.site.register(Product, ProductAdmin)
