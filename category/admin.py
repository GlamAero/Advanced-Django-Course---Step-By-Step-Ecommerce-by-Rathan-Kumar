from django.contrib import admin
from .models import Category

# Register your models here.
class CategoryAdmin(admin.ModelAdmin):
    # the below says that in the admin page it will prepopulate the slug field with the category name when creating a new category
    prepopulated_fields = {'slug': ('category_name',)}
    list_display = ('category_name', 'slug') 


admin.site.register(Category, CategoryAdmin)
