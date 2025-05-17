from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Account


# Register your models here.

# To make the custom user model 'Account' the default user model in the admin panel, we need to create a custom admin class that inherits from 'UserAdmin' and specify the fields we want to display in the admin panel.
# We also need to register this custom admin class with the admin site.
# In addition, this makes the password a read-only field in the admin panel, so that it cannot be changed directly from the admin interface. Instead, you would need to use the Django shell or a custom form to change the password for a user.
class AccountAdmin(UserAdmin):
    list_display = ('email', 'first_name', 'last_name', 'username', 'last_login', 'date_joined', 'is_active')
    list_display_links = ('email', 'first_name', 'last_name')
    readonly_fields = ('last_login', 'date_joined')
    ordering = ('-date_joined',)
    filter_horizontal = ()
    list_filter = ()
    fieldsets = ()



# Register the custom user model with the admin site
admin.site.register(Account, AccountAdmin)