from django.shortcuts import render, get_object_or_404, redirect
from .forms import ProductStockForm, VariationStockForm
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponse
from orders.models import OrderItem  # Optional
from inventory.models import StockLog
from .utils import log_stock_update  # You must define this
from django.contrib import messages  # Optional, for user feedback
from .models import Vendor, VendorProduct, VendorVariationCombination  # Assuming your vendor and product models are here
import logging



logger = logging.getLogger(__name__)


# Create your views here.

@login_required
def vendor_dashboard(request):
    # request.user means the logged-in user because of the @login_required decorator
    user = request.user

    # Check if user has vendor access
    if not hasattr(user, "vendor") or not user.is_vendor:
        return redirect("/")  # Redirect unauthorized users

    vendor = user.vendor

    # Only show products that belong to the logged-in vendor
    products = VendorProduct.objects.filter(vendor=vendor).prefetch_related("variations")

    return render(request, "vendor/dashboard.html", {
        "vendor": vendor,
        "products": products,
    })


@login_required
def add_product(request):
    vendor = request.user.vendor

    if request.method == "POST":
        form = ProductStockForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save(commit=False)
            product.vendor = vendor  # Assign ownership
            product.save()

            log_stock_update(vendor, product, "added", product.stock)
            return redirect("vendor_dashboard")

    return render(request, "vendor/add_product.html", {"form": ProductStockForm()})


def log_stock_update(vendor, product, action, quantity):

    StockLog.objects.create(
        vendor=vendor,
        product=product,
        action=action,     # "added", "updated", "removed", etc.
        quantity=quantity,
    )


@login_required
def set_product_stock(request, product_id):
    product = get_object_or_404(VendorProduct, id=product_id, vendor=request.user)

    if request.method == "POST":
        form = ProductStockForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            new_stock = form.cleaned_data.get("stock_quantity", 0)

            # Prevent negative stock
            if new_stock < 0:
                messages.error(request, "Stock value cannot be negative.")
                return render(request, "vendor/set_product_stock.html", {"form": form, "product": product})

            old_stock = product.stock_quantity
            if new_stock != old_stock:
                action = "updated" if new_stock > 0 else "removed"
                log_stock_update(request.user, product, action, new_stock)

            form.save()
            messages.success(request, "Product stock updated successfully.")
            return redirect("vendor_dashboard")

    else:
        form = ProductStockForm(instance=product)

    return render(request, "vendor/set_product_stock.html", {"form": form, "product": product})


# this view sets the stock for a variation combination for a vendor
@login_required
def set_variation_stock(request, variation_combination_id):
    vendor = request.user.vendor
    variation_combination = get_object_or_404(VendorVariationCombination, id=variation_combination_id, VendorProduct__vendor=vendor)

    if request.method == "POST":
        form = VariationStockForm(request.POST)
        if form.is_valid():
            category = form.cleaned_data["category"]
            quantity = form.cleaned_data["quantity"]

            if quantity < 0:  # Prevent negative stock input
                return HttpResponse("Stock value cannot be negative.", status=400)

            variation_combination.set_stock(category, quantity)  # Assign stock properly
            return redirect("vendor_dashboard")

    return render(request, "vendor/set_variation_stock.html", {"form": VariationStockForm()})


# this function sets the stock for a variation combination for a specific category
@transaction.atomic
def set_stock(variation_combination, category, quantity):
    if quantity < 0:
        return HttpResponse("Stock value cannot be negative.", status=400)

    variation_combination.set_stock(category, quantity)


# this function logs stock updates for a vendor's product
def log_stock_update(vendor, product, action, quantity):
    logger.info(f"Vendor {vendor.name} {action} stock for {product.product_name}: {quantity} units")


# this function reduces the stock of a variation combination when a purchase is made
@transaction.atomic
def reduce_stock_on_purchase(variation_combination, category, quantity):
    if variation_combination.stock_per_category.get(category, 0) >= quantity:
        variation_combination.stock_per_category[category] -= quantity
        variation_combination.save()

        log_stock_update(
            variation_combination.product.vendor,
            variation_combination.product,
            "reduced (purchase)",
            quantity
        )


@login_required
def view_inventory(request):
    vendor = request.user.vendor
    products = VendorProduct.objects.filter(vendor=vendor)

    return render(request, "vendor/inventory.html", {"products": products})


@login_required
def update_product_pricing(request, product_id):
    vendor = request.user.vendor
    product = get_object_or_404(VendorProduct, id=product_id, vendor=vendor)

    if request.method == "POST":
        price = request.POST.get("price")
        discount = request.POST.get("discount_percentage")

        if float(price) <= 0:
            return HttpResponse("Price must be greater than zero.", status=400)
        if float(discount) < 0 or float(discount) > 100:
            return HttpResponse("Discount must be between 0-100%.", status=400)

        product.price = price
        product.discount_percentage = discount
        product.save()

        log_stock_update(vendor, product, "updated price & discount", price)
        return redirect("vendor_dashboard")

    return render(request, "vendor/update_pricing.html", {"product": product})

