from django.shortcuts import render, redirect
from django.http import HttpResponse
from carts.models import CartItem
from .forms import OrderForm
from .models import Order, Payment
import datetime
from django.contrib.auth.decorators import login_required
from orders.models import OrderProduct
# from store.models import VariationCombination

# for paypal:
import json, requests
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_protect, csrf_exempt
from django.db import transaction



# Create your views here.

# Dedicated Payment View - Displays user's payments
@login_required
def payments(request):
    payments = Payment.objects.filter(user=request.user).order_by("-created_at")
    return render(request, "orders/payments.html", {"payments": payments})


# To Move Cart Items To OrderProduct Table:
# The below function('move_cart_items_to_order') is called in function 'capture_paypal_order' to transfers Cart items to OrderProduct table after successful payment
def move_cart_items_to_order(user, order):
    """
    Transfers CartItems to OrderProduct table after successful payment and ensures proper deletion.
    """
    cart_items = CartItem.objects.filter(user=user)

    if cart_items.exists():
        for item in cart_items:
            order_product = OrderProduct.objects.create(
                order=order,
                user=user,
                product=item.product,
                quantity=item.quantity,
                product_price=item.product.price,
                ordered=True,
            )
            order_product.variations.set(item.variations.all())  # Assign chosen variations
            
            item.is_active = False  # Mark item as inactive before deletion
            item.save()  # Ensure update is committed before removing
            
            item.delete()  # Explicitly delete item after moving

    return True  # Indicates successful transfer


def place_order(request, total=0, quantity=0):
    # here 'request.user' simply means the 'user' making a request in the frontend whether logged in or not. However, in here, this 'user' is logged in because to get to 'checkout' which preceeds the 'place_order', login is required.
    current_user = request.user

    cart_items = CartItem.objects.filter(user=current_user)
    cart_count = cart_items.count()

    # if the cart_count is less than or equal to zero(0), redirect the user to the 'store' page
    if cart_count <= 0:
        return redirect('store')
    
    
    grand_total = 0
    tax = 0

    for cart_item in cart_items:
        total += (cart_item.product.price * cart_item.quantity)
        quantity += cart_item.quantity
    
    tax = (total * 0.02) # '0.02' is the tax rate used here(2/100)
    grand_total = total + tax

    
    if request.method == 'POST':
        form = OrderForm(request.POST)

        if form.is_valid():
            # store all the billing information inside order table:
            data = Order()
            data.user = current_user
            data.first_name = form.cleaned_data['first_name']
            data.last_name = form.cleaned_data['last_name']
            data.phone = form.cleaned_data['phone']
            data.email = form.cleaned_data['email']
            data.address_line_1 = form.cleaned_data['address_line_1']
            data.address_line_2 = form.cleaned_data['address_line_2']
            data.country = form.cleaned_data['country']
            data.state = form.cleaned_data['state']
            data.city = form.cleaned_data['city']
            data.order_note = form.cleaned_data['order_note']
            data.order_total = grand_total
            data.tax = tax
            data.ip = request.META.get('REMOTE_ADDR')
            data.save()

            # generate order number using the current date as follows:

            # yr = int(datetime.date.today().strftime('%Y'))
            # dt = int(datetime.date.today().strftime('%d'))
            # mt = int(datetime.date.today().strftime('%m'))
            # d = datetime.date(yr, mt,dt)
            # current_date = d.strftime("%Y%m%d") # e.g '2021-03-05'

            # another way to write the code I commented above:
            # generate order number using the current date as follows:
            current_date = datetime.date.today().strftime("%Y%m%d")

            order_number = current_date + str(data.id) # e.g '202103051' where  '2021' is year, '03' is month, '05' is day and 1 is the data.id

            data.order_number = order_number
            data.save()

            order = Order.objects.filter(user=current_user, is_ordered=False, order_number=data.order_number).first()

            if not order:
                print("Order was not found before creating PayPal order.")  # Debugging
                return JsonResponse({"error": "Order not found in database."}, status=404)

            context = {
                'order': order,
                'cart_items': cart_items,
                'total': total,
                'tax': tax,
                'grand_total': grand_total,
                'paypal_client_id': settings.PAYPAL_CLIENT_ID  # PAYPAL(go to 'settings.py' file of 'POGOSMARKETPLACE' and search for 'PAYPAL_CLIENT_ID')
            }

            return render(request, 'orders/payments.html', context)
        else:
            return HttpResponse("Something went wrong.")
    else:
        return redirect('checkout')
            

# --------------------------------------------------------PAYPAL VIEWS START HERE, there is also 'paypal_client_id' above-----------------------------------------------------#

def get_paypal_access_token():
    response = requests.post(
        f"{settings.PAYPAL_API_BASE}/v1/oauth2/token",
        headers={"Accept": "application/json"},
        data={"grant_type": "client_credentials"},
        auth=(settings.PAYPAL_CLIENT_ID, settings.PAYPAL_SECRET), # PAYPAL(go to 'settings.py' file of 'POGOSMARKETPLACE' and search for 'PAYPAL_CLIENT_ID')
    )
    return response.json().get("access_token")


@csrf_exempt
def create_paypal_order(request):

    current_user = request.user

    try:
        order = Order.objects.filter(user=current_user, is_ordered=False).latest("created_at")  # Specify a date field

        grand_total = order.order_total
    except Order.DoesNotExist:
        return JsonResponse({'error': 'Order not found'}, status=404)

    token = get_paypal_access_token()
    
    order_data = {
        "intent": "CAPTURE",
        "purchase_units": [{
            "amount": {
                "currency_code": "USD",
                "value": f"{grand_total:.2f}"  #'.2f' means 2 points after the decimal point. It is '2 floating point'. 
            }
        }]
    }

    # the below sends/'post' the order_data(above) to PayPal’s API to create the order
    response = requests.post(   
        f"{settings.PAYPAL_API_BASE}/v2/checkout/orders", # To get the value of 'settings.PAYPAL_API_BASE', go to 'settings.py' file of 'POGOSMARKETPLACE' and search for 'PAYPAL_API_BASE'
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        },
        json=order_data
    )

    response_data = response.json()

    # Extract PayPal Order ID
    if response.status_code == 201:
        paypal_order_id = response_data["id"]  # Extracted PayPal Order ID

        # Save PayPal Order ID in your database
        order = Order.objects.filter(user=request.user, is_ordered=False).latest("created_at")  #This ensures only one order is fetched

        order.paypal_order_id = paypal_order_id  # Save PayPal Order ID

        order.save()

        return JsonResponse({"paypal_order_id": paypal_order_id})
    else:
        return JsonResponse({"error": "Failed to create PayPal order", "details": response_data}, status=400)


@csrf_exempt
def capture_paypal_order(request, order_id):
    token = get_paypal_access_token()
    if not token:
        return JsonResponse({"error": "Failed to authenticate with PayPal"}, status=500)

    response = requests.post(
        f"{settings.PAYPAL_API_BASE}/v2/checkout/orders/{order_id}/capture",
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"}
    )

    response_data = response.json()
    if response.status_code == 201:
        captures = response_data.get("purchase_units", [{}])[0].get("payments", {}).get("captures", [])
        if captures:
            payment_id = captures[0].get("id", "UNKNOWN")
            payment_status = response_data.get("status", "FAILED")
            amount_paid = captures[0].get("amount", {}).get("value", 0)

            order = Order.objects.filter(paypal_order_id=order_id).first()

            if not order:
                print(f"Order with PayPal ID {order_id} not found.")  # Debugging
                return JsonResponse({"error": "Order not found in the database."}, status=404)

            with transaction.atomic():  # Ensures atomic update
                order.transaction_id = payment_id

                # Automate status update when payment is completed
                if payment_status == "COMPLETED":
                    order.status = "Completed"
                    order.is_ordered = True

                    # Transfer cart items only after successful payment
                    move_cart_items_to_order(order.user, order)

                    # Reduce stock for the full variation combination
                    order_products = OrderProduct.objects.filter(order=order)
                    # for order_product in order_products:
                    #     variation_combination = VariationCombination.objects.filter(
                    #         product=order_product.product,
                    #         variations__in=order_product.variations.all()
                    #     ).first()

                    #     if variation_combination:
                    #         for variation in order_product.variations.all():
                    #             category = variation.variation_category
                    #             variation_combination.reduce_stock(category, order_product.quantity)  # Deduct stock for selected category



                    # Ensure session cart is cleared properly
                    if request.session.get("cart_id"):
                        del request.session["cart_id"]
                        request.session.modified = True  # Confirms session change

                # Create and link Payment record to Order
                payment = Payment.objects.create(
                    user=order.user,
                    paypal_order_id=order.paypal_order_id,
                    transaction_id=payment_id,
                    payment_method="PayPal",
                    order_total=order.order_total,
                    amount_paid=amount_paid,
                    status=payment_status
                )

                # Assign Payment to OrderProduct entries
                order_products.update(payment=payment)  # Direct bulk update for efficiency

                # Ensure variations are correctly transferred to the OrderProduct table
                for order_product in order_products:
                    cart_item = CartItem.objects.filter(user=order.user, product=order_product.product).first()
                    if cart_item:
                        order_product.variations.set(cart_item.variations.all())  # Assign chosen variations

                # Associate the Payment record with the Order
                order.payment = payment
                order.save()

            return JsonResponse({
                "message": "Payment captured successfully!",
                "order_id": order_id,
                "status": payment_status,
                "payment_id": payment_id
            })

        return JsonResponse({"error": "Payment ID not found in PayPal response."}, status=500)

    return JsonResponse({"error": "Failed to capture PayPal order", "details": response_data}, status=response.status_code)

# -----------------------------------------------------------------------PAYPAL VIEWS ENDS HERE--------------------------------------------------------------------------#


def success(request):
    return render(request, "orders/success.html")
