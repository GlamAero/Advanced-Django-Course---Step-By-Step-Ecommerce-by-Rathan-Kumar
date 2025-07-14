from django import forms
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponseBadRequest
from django.contrib import messages
from django.db import transaction, IntegrityError
from django.core.exceptions import ValidationError
from decimal import Decimal
from django.db.models import Sum
from django.utils import timezone
from datetime import timedelta
from accounts.decorators import customer_required
from store.models import Product, Variation, VariationCombination
from coupons.models import Coupon
from .models import Cart, CartItem
from django_ratelimit.decorators import ratelimit
from django.views.decorators.csrf import csrf_protect



def _cart_id(request):
    if not request.session.session_key:
        request.session.create()
    return request.session.session_key

@ratelimit(key='ip', rate='30/m')
@csrf_protect
def add_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id, is_available=True)
    current_user = request.user

    # Process variations from POST data
    product_variations = []
    if request.method == 'POST':
        for key in request.POST:
            if key.startswith('variation_'):
                try:
                    variation = Variation.objects.get(
                        product=product,
                        variation_category=key.replace('variation_', ''),
                        variation_value=request.POST[key]
                    )
                    product_variations.append(variation)
                except Variation.DoesNotExist:
                    # Variation specified does not exist for this product, ignore or handle as needed
                    pass

    # Validate variation combination
    if product_variations:
        possible_combinations = VariationCombination.objects.filter(
            product=product,
            is_active=True,
            stock__gt=0
        )

        matching_combination = None
        for combination in possible_combinations:
            # Compare sets of variations for exact match
            if set(combination.variations.all()) == set(product_variations):
                matching_combination = combination
                break

        if not matching_combination:
            return JsonResponse({
                'status': 'error',
                'message': 'This combination is not available'
            }, status=400)

    cart = get_or_create_cart(request)

    try:
        with transaction.atomic():
            # Query for existing cart items with the same product and cart
            cart_items = CartItem.objects.filter(
                product=product,
                cart=cart,
                user=current_user if current_user.is_authenticated else None
            )

            if product_variations:
                # Filter cart items that have exactly the same variations
                # Annotate with count of variations, filter by count and variations
                variation_ids = [v.id for v in product_variations]
                cart_items = cart_items.filter(
                    variations__id__in=variation_ids
                ).annotate(
                    variation_count=Count('variations')
                ).filter(
                    variation_count=len(variation_ids)
                ).distinct()

            if cart_items.exists():
                item = cart_items.first()
                item.quantity += 1
                item.clean()
                item.save()
            else:
                item = CartItem.objects.create(
                    product=product,
                    quantity=1,
                    cart=cart,
                    user=current_user if current_user.is_authenticated else None
                )
                if product_variations:
                    item.variations.set(product_variations)

                item.clean()
                item.save()

            # Update cart activity timestamp
            cart.last_activity = timezone.now()
            cart.save()

            # Calculate total cart items count
            total_quantity = cart.cart_items.filter(is_active=True).aggregate(
                total=Sum('quantity')
            )['total'] or 0

            return JsonResponse({
                'status': 'success',
                'cart_count': total_quantity,
                'message': 'Product added to cart',
                'cart_total': str(cart.grand_total)
            })

    except (ValidationError, IntegrityError) as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=400)

    except Exception:
        return JsonResponse({
            'status': 'error',
            'message': 'Server error'
        }, status=500)


@ratelimit(key='ip', rate='30/m')
@csrf_protect
def add_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id, is_available=True)
    current_user = request.user

    # Process variations from POST data
    product_variations = []
    if request.method == 'POST':
        for key in request.POST:
            if key.startswith('variation_'):
                try:
                    variation = Variation.objects.get(
                        product=product,
                        variation_category=key.replace('variation_', ''),
                        variation_value=request.POST[key]
                    )
                    product_variations.append(variation)
                except Variation.DoesNotExist:
                    # Variation specified does not exist for this product, ignore or handle as needed
                    pass

    # Validate variation combination
    if product_variations:
        possible_combinations = VariationCombination.objects.filter(
            product=product,
            is_active=True,
            stock__gt=0
        )

        matching_combination = None
        for combination in possible_combinations:
            # Compare sets of variations for exact match
            if set(combination.variations.all()) == set(product_variations):
                matching_combination = combination
                break

        if not matching_combination:
            return JsonResponse({
                'status': 'error',
                'message': 'This combination is not available'
            }, status=400)

    cart = get_or_create_cart(request)

    try:
        with transaction.atomic():
            # Query for existing cart items with the same product and cart
            cart_items = CartItem.objects.filter(
                product=product,
                cart=cart,
                user=current_user if current_user.is_authenticated else None
            )

            if product_variations:
                # Filter cart items that have exactly the same variations
                # Annotate with count of variations, filter by count and variations
                variation_ids = [v.id for v in product_variations]
                cart_items = cart_items.filter(
                    variations__id__in=variation_ids
                ).annotate(
                    variation_count=Count('variations')
                ).filter(
                    variation_count=len(variation_ids)
                ).distinct()

            if cart_items.exists():
                item = cart_items.first()
                item.quantity += 1
                item.clean()
                item.save()
            else:
                item = CartItem.objects.create(
                    product=product,
                    quantity=1,
                    cart=cart,
                    user=current_user if current_user.is_authenticated else None
                )
                if product_variations:
                    item.variations.set(product_variations)

                item.clean()
                item.save()

            # Update cart activity timestamp
            cart.last_activity = timezone.now()
            cart.save()

            # Calculate total cart items count
            total_quantity = cart.cart_items.filter(is_active=True).aggregate(
                total=Sum('quantity')
            )['total'] or 0

            return JsonResponse({
                'status': 'success',
                'cart_count': total_quantity,
                'message': 'Product added to cart',
                'cart_total': str(cart.grand_total)
            })

    except (ValidationError, IntegrityError) as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=400)

    except Exception:
        return JsonResponse({
            'status': 'error',
            'message': 'Server error'
        }, status=500)


def remove_cart(request, product_id, cart_item_id):
    try:
        product = get_object_or_404(Product, id=product_id)
        cart = get_or_create_cart(request)
        
        if request.user.is_authenticated:
            cart_item = CartItem.objects.get(
                id=cart_item_id,
                product=product,
                user=request.user,
                cart=cart
            )
        else:
            cart_item = CartItem.objects.get(
                id=cart_item_id,
                product=product,
                cart=cart
            )
        
        if cart_item.quantity > 1:
            cart_item.quantity -= 1
            cart_item.save()
        else:
            cart_item.delete()
            
        # Update cart activity timestamp
        cart.last_activity = timezone.now()
        cart.save()
        
        return redirect('cart')
    
    except CartItem.DoesNotExist:
        messages.error(request, 'Cart item not found')
        return redirect('cart')

def remove_cart_item(request, product_id, cart_item_id):
    try:
        product = get_object_or_404(Product, id=product_id)
        cart = get_or_create_cart(request)
        
        if request.user.is_authenticated:
            cart_item = CartItem.objects.get(
                id=cart_item_id,
                product=product,
                user=request.user,
                cart=cart
            )
        else:
            cart_item = CartItem.objects.get(
                id=cart_item_id,
                product=product,
                cart=cart
            )
        
        cart_item.delete()
        
        # Update cart activity timestamp
        cart.last_activity = timezone.now()
        cart.save()
        
        return redirect('cart')
    
    except CartItem.DoesNotExist:
        messages.error(request, 'Cart item not found')
        return redirect('cart')

def update_cart_item(request, cart_item_id):
    if request.headers.get('x-requested-with') == 'XMLHttpRequest' and request.method == 'POST':
        try:
            quantity = int(request.POST.get('quantity', 1))
            coupon_code = request.POST.get('coupon_code', '')
            
            if quantity < 1:
                return JsonResponse({'status': 'error', 'message': 'Invalid quantity'}, status=400)
            
            if request.user.is_authenticated:
                cart_item = CartItem.objects.get(
                    id=cart_item_id,
                    user=request.user,
                    is_active=True
                )
            else:
                cart = get_or_create_cart(request)
                cart_item = CartItem.objects.get(
                    id=cart_item_id,
                    cart=cart,
                    is_active=True
                )
            
            # Check stock
            combination = cart_item.get_variation_combination()
            if combination and combination.stock < quantity:
                return JsonResponse({
                    'status': 'error',
                    'message': f'Only {combination.stock} available in stock'
                }, status=400)
            
            cart_item.quantity = quantity
            cart_item.clean()
            cart_item.save()
            
            cart = cart_item.cart
            
            # Apply coupon if valid
            discount_amount = Decimal('0.00')
            coupon = None
            if coupon_code:
                try:
                    coupon = Coupon.objects.get(
                        code__iexact=coupon_code,
                        active=True,
                        valid_from__lte=timezone.now(),
                        valid_to__gte=timezone.now()
                    )
                    if cart.is_eligible_for_discount(coupon):
                        cart.apply_coupon(coupon)
                        discount_amount = coupon.discount
                    else:
                        coupon = None
                except Coupon.DoesNotExist:
                    coupon = None
            
            # Update cart activity timestamp
            cart.last_activity = timezone.now()
            cart.save()
            
            return JsonResponse({
                'status': 'success',
                'subtotal': str(cart_item.sub_total),
                'discount': str(cart.discount),
                'shipping': str(cart.shipping_cost),
                'tax': str(cart.tax),
                'grand_total': str(cart.grand_total),
                'coupon_code': coupon.code if coupon else '',
                'discount_amount': str(discount_amount)
            })
        
        except (CartItem.DoesNotExist, ValueError) as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    
    return JsonResponse({'status': 'error'}, status=405)

def apply_coupon(request):
    if request.method == 'POST':
        coupon_code = request.POST.get('coupon_code', '').strip()
        cart = get_or_create_cart(request)
        
        try:
            coupon = Coupon.objects.get(
                code__iexact=coupon_code,
                active=True,
                valid_from__lte=timezone.now(),
                valid_to__gte=timezone.now()
            )
            
            if cart.is_eligible_for_discount(coupon):
                cart.apply_coupon(coupon)
                messages.success(request, f"Coupon '{coupon.code}' applied successfully!")
            else:
                messages.error(request, "This coupon is not valid for your cart")
                
        except Coupon.DoesNotExist:
            messages.error(request, "Invalid coupon code")
        
        # Update cart activity timestamp
        cart.last_activity = timezone.now()
        cart.save()
        
    return redirect('cart')

def remove_coupon(request):
    cart = get_or_create_cart(request)
    if cart.coupon:
        coupon_code = cart.coupon.code
        cart.remove_coupon()
        messages.success(request, f"Coupon '{coupon_code}' removed")
        
        # Update cart activity timestamp
        cart.last_activity = timezone.now()
        cart.save()
    
    return redirect('cart')

def cart(request):
    cart = get_or_create_cart(request)
    cart_items = cart.cart_items.filter(is_active=True).select_related('product').prefetch_related('variations')
    
    # Track cart abandonment time
    if not request.user.is_authenticated:
        abandonment_threshold = timezone.now() - timedelta(minutes=30)
        if cart.last_activity < abandonment_threshold:
            cart.log_abandonment()
    
    context = {
        'cart': cart,
        'cart_items': cart_items,
        'total': cart.total,
        'shipping_cost': cart.shipping_cost,
        'tax': cart.tax,
        'discount': cart.discount,
        'grand_total': cart.grand_total,
        'coupon_form': CouponForm(),
        'abandoned': cart.status == 'abandoned'
    }
    return render(request, 'store/cart.html', context)

@customer_required
def checkout(request):
    cart = get_or_create_cart(request)
    cart_items = cart.cart_items.filter(is_active=True).select_related('product').prefetch_related('variations')
    
    if not cart_items.exists():
        messages.warning(request, "Your cart is empty")
        return redirect('store')
    
    # Validate stock before checkout
    for item in cart_items:
        combination = item.get_variation_combination()
        stock = combination.stock if combination else item.product.stock
        if stock < item.quantity:
            messages.error(request, 
                f"Only {stock} available for {item.product.product_name}"
            )
            return redirect('cart')
    
    # Calculate shipping costs
    cart.calculate_shipping()
    cart.save()
    
    context = {
        'cart': cart,
        'cart_items': cart_items,
        'total': cart.total,
        'shipping_cost': cart.shipping_cost,
        'tax': cart.tax,
        'discount': cart.discount,
        'grand_total': cart.grand_total,
    }
    return render(request, 'store/checkout.html', context)

class CouponForm(forms.Form):
    code = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter coupon code'
        }),
        max_length=50,
        required=False
    )
