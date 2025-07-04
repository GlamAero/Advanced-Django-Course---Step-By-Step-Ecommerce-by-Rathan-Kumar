from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from .actions import reset_stock, bulk_create_combinations
from .filters import LowStockFilter
from .forms import ProductForm
from .inlines import VariationInline, VariationCombinationInline
from ..models import Product

class ProductAdmin(admin.ModelAdmin):
    """Admin configuration for managing products based on type."""

    form = ProductForm
    prepopulated_fields = {'slug': ('product_name',)}
    list_filter = ('is_available', LowStockFilter)
    actions = [reset_stock, bulk_create_combinations]

    # Optional external JS file (e.g. for toggle logic)
    class Media:
        js = ('admin/js/product_type_toggle.js',)

    # Fields displayed in list view
    def get_list_display(self, request):
        return (
            'product_name',
            'maybe_price',
            'colored_stock',
            'modified_date',
            'is_available'
        )

    def maybe_price(self, obj):
        """Display price if product is simple; else show dash."""
        return obj.price if obj.product_type == 'simple' else format_html('<span style="color:#888;">—</span>')
    maybe_price.short_description = 'Price'
    maybe_price.admin_order_field = 'price'

    def colored_stock(self, obj):
        """Display stock with color indicators based on thresholds."""
        stock = obj.stock or 0
        color = 'green' if stock > 10 else 'orange' if stock > 5 else 'red'
        return format_html('<strong style="color:{};">{}</strong>', color, stock)
    colored_stock.short_description = 'Stock'

    def get_queryset(self, request):
        """Improve performance with prefetching."""
        return super().get_queryset(request).prefetch_related('variation_set', 'variation_combinations')

    def get_form(self, request, obj=None, **kwargs):
        """Dynamically remove price from form based on product_type."""
        form = super().get_form(request, obj, **kwargs)
        product_type = obj.product_type if obj else request.POST.get("product_type") or request.GET.get("product_type")
        if product_type and product_type != "simple":
            form.base_fields.pop("price", None)
        return form

    def get_fields(self, request, obj=None):
        """Dynamically exclude price from field layout."""
        fields = super().get_fields(request, obj)
        product_type = obj.product_type if obj else request.POST.get("product_type") or request.GET.get("product_type")
        if product_type and product_type != "simple":
            fields = [f for f in fields if f != "price"]
        return fields

    def get_inline_instances(self, request, obj=None):
        """Show relevant inlines depending on product_type."""
        if not obj:
            return []
        if obj.product_type == 'variation':
            return [VariationInline(self.model, self.admin_site)]
        elif obj.product_type == 'combination':
            return [VariationCombinationInline(self.model, self.admin_site)]
        return []

    def render_change_form(self, request, context, *args, **kwargs):
        """
        Inject inline JavaScript to toggle price visibility 
        based on selected product type.
        """
        inline_script = """
        <script>
        document.addEventListener('DOMContentLoaded', function () {
            const productTypeSelect = document.querySelector('#id_product_type');
            const priceRow = document.querySelector('.form-row.field-price');
            function togglePriceField() {
                if (!productTypeSelect || !priceRow) return;
                priceRow.style.display = productTypeSelect.value === 'simple' ? 'block' : 'none';
            }
            togglePriceField();
            productTypeSelect.addEventListener('change', togglePriceField);
        });
        </script>
        """

        if not context.get('original'):
            self.message_user(
                request,
                "Save this product first to enable variation or combination entry.",
                level='info'
            )

        context['adminform'].form.fields['product_type'].help_text = mark_safe(
            "Select a product type. The price field will adjust automatically."
        )
        context['custom_inline_js'] = mark_safe(inline_script)
        return super().render_change_form(request, context, *args, **kwargs)