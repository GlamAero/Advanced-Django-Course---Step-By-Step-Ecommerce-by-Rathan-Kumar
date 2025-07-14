from django.utils import timezone
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.admin import SimpleListFilter

from .models import Account, VendorProfile, CustomerProfile, UserActivity
from .forms import VendorProfileAdminForm, CustomerProfileAdminForm


@admin.action(description='Mark selected vendors as verified')
def mark_verified(modeladmin, request, queryset):
    # Filter vendors eligible for verification
    eligible_qs = queryset.filter(
        is_verified=False,
        business_license_file__isnull=False,
        business_license_number__isnull=False,
        business_license_expiry__gt=timezone.now().date()
    )
    
    # Bulk update eligible vendors
    updated_count = eligible_qs.update(is_verified=True)
    
    # Calculate how many vendors were skipped
    skipped_count = queryset.filter(is_verified=False).count() - updated_count
    
    modeladmin.message_user(
        request,
        f"{updated_count} vendor(s) verified. {skipped_count} skipped (missing or expired documents)."
    )


class PreferredContactMethodFilter(SimpleListFilter):
    title = 'Preferred Contact Method'
    parameter_name = 'preferred_contact_method'

    def lookups(self, request, model_admin):
        return [
            ('email', 'Email'),
            ('phone', 'Phone'),
        ]

    def queryset(self, request, queryset):
        if self.value() in ['email', 'phone']:
            return queryset.filter(preferred_contact_method=self.value())
        return queryset


class VendorProfileInline(admin.StackedInline):
    model = VendorProfile
    can_delete = False
    verbose_name_plural = 'Vendor Profile'
    form = VendorProfileAdminForm


class CustomerProfileInline(admin.StackedInline):
    model = CustomerProfile
    can_delete = False
    verbose_name_plural = 'Customer Profile'
    form = CustomerProfileAdminForm


@admin.register(Account)
class AccountAdmin(UserAdmin):
    list_display = (
        'email', 'first_name', 'last_name', 'username', 'role',
        'is_active', 'is_staff', 'is_superadmin', 'is_admin'
    )
    list_display_links = ('email', 'first_name', 'last_name')
    readonly_fields = ('last_login', 'date_joined')
    ordering = ('-date_joined',)
    list_filter = ('is_active', 'is_staff', 'is_superadmin', 'is_admin', 'role')
    filter_horizontal = ('groups', 'user_permissions')

    fieldsets = (
        (None, {'fields': ('email', 'username', 'password')}),
        ('Personal Info', {'fields': ('first_name', 'last_name', 'phone_number')}),
        ('Role', {'fields': ('role',)}),
        ('Permissions', {
            'fields': (
                'is_active', 'is_staff', 'is_admin', 'is_superadmin',
                'groups', 'user_permissions', 'requires_2fa',
            )
        }),
        ('Important Dates', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'email', 'username', 'first_name', 'last_name', 'role',
                'password1', 'password2', 'is_active', 'is_staff', 'is_superadmin',
            ),
        }),
    )

    inlines = []

    def get_inline_instances(self, request, obj=None):
        # Only show inlines for existing objects
        if obj is None:
            return []
        if obj.is_vendor():
            return [VendorProfileInline(self.model, self.admin_site)]
        elif obj.is_customer():
            return [CustomerProfileInline(self.model, self.admin_site)]
        return []


@admin.register(VendorProfile)
class VendorProfileAdmin(admin.ModelAdmin):
    form = VendorProfileAdminForm
    list_display = ('user', 'company_name', 'is_verified', 'business_license_number', 'created_at', 'updated_at')
    search_fields = ('user__email', 'company_name')
    readonly_fields = ('created_at', 'updated_at')
    list_filter = ('is_verified', 'created_at')
    actions = [mark_verified]


@admin.register(CustomerProfile)
class CustomerProfileAdmin(admin.ModelAdmin):
    form = CustomerProfileAdminForm
    list_display = ('user', 'date_of_birth', 'preferred_contact_method', 'created_at', 'updated_at')
    search_fields = ('user__email',)
    readonly_fields = ('created_at', 'updated_at')
    list_filter = (PreferredContactMethodFilter, 'created_at')


@admin.register(UserActivity)
class UserActivityAdmin(admin.ModelAdmin):
    list_display = ('user', 'activity_type', 'ip_address', 'timestamp')
    list_filter = ('activity_type', 'timestamp')
    search_fields = ('user__email', 'ip_address')
    readonly_fields = ('user', 'activity_type', 'ip_address', 'user_agent', 'timestamp')
    ordering = ('-timestamp',)
