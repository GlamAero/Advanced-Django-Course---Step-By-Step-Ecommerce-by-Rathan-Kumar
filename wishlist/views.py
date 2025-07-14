from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from .models import Wishlist, WishlistItem
from store.models import Product

@login_required
def wishlist_view(request):
    wishlist, created = Wishlist.objects.get_or_create(user=request.user)
    items = wishlist.items.select_related(
        'product',
        'product__vendor'
    ).prefetch_related(
        'product__images'
    ).order_by('-added_at')
    
    context = {
        'wishlist': wishlist,
        'items': items
    }
    return render(request, 'wishlist/wishlist.html', context)

@login_required
@require_POST
def add_to_wishlist(request):
    product_id = request.POST.get('product_id')
    if not product_id:
        return JsonResponse({'success': False, 'message': 'Product ID missing'})
    
    try:
        product = Product.objects.get(id=product_id, is_available=True)
    except Product.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Product not available'})
    
    wishlist, created = Wishlist.objects.get_or_create(user=request.user)
    
    try:
        wishlist.add_item(product)
        return JsonResponse({
            'success': True,
            'message': 'Added to wishlist',
            'wishlist_count': wishlist.item_count
        })
    except ValidationError as e:
        return JsonResponse({'success': False, 'message': str(e)})

@login_required
@require_POST
def remove_from_wishlist(request):
    product_id = request.POST.get('product_id')
    if not product_id:
        return JsonResponse({'success': False, 'message': 'Product ID missing'})
    
    wishlist = get_object_or_404(Wishlist, user=request.user)
    
    if wishlist.remove_item(product_id):
        return JsonResponse({
            'success': True,
            'message': 'Removed from wishlist',
            'wishlist_count': wishlist.item_count
        })
    return JsonResponse({'success': False, 'message': 'Item not in wishlist'})

@login_required
@require_POST
def move_to_cart(request):
    product_id = request.POST.get('product_id')
    quantity = request.POST.get('quantity', 1)
    
    if not product_id:
        return JsonResponse({'success': False, 'message': 'Product ID missing'})
    
    try:
        wishlist_item = WishlistItem.objects.get(
            wishlist__user=request.user,
            product_id=product_id
        )
        return wishlist_item.move_to_cart(request, quantity)
    except WishlistItem.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Product not in wishlist'
        })


        