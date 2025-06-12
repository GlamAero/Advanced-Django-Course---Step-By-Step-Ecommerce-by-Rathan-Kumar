from .models import Payment, Order  # ✅ Import Payment model

@csrf_exempt
def capture_paypal_order(request, order_id):
    token = get_paypal_access_token()

    response = requests.post(
        f"{settings.PAYPAL_API_BASE}/v2/checkout/orders/{order_id}/capture",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        }
    )

    response_data = response.json()
    print("Full PayPal Capture Response:", json.dumps(response_data, indent=4))  # ✅ Debugging step

    if response.status_code == 201:  # ✅ Transaction successfully captured
        captures = response_data.get("purchase_units", [{}])[0].get("payments", {}).get("captures", [])

        if not captures:  # ✅ Prevents errors if captures is empty
            print("No Captures Found in PayPal Response!")
            return JsonResponse({"error": "Payment ID not found in PayPal response."}, status=500)

        payment_id = captures[0].get("id", "UNKNOWN")  # ✅ Extracts safely
        payment_status = response_data.get("status", "FAILED")  # ✅ Extract status
        amount_paid = captures[0].get("amount", {}).get("value", 0)  # ✅ Get actual paid amount

        print("Extracted Payment ID:", payment_id)  # ✅ Debugging step

        # ✅ Locate the order in the database
        order = Order.objects.filter(paypal_order_id=order_id).first()

        if order:
            print(f"Before Save - Order: {order.order_number}, transaction_id: {order.transaction_id}")

            # ✅ Save order details
            order.transaction_id = payment_id
            order.is_ordered = True
            order.save()
            order.refresh_from_db()  # ✅ Ensure the change is committed

            print(f"After Save - Order: {order.order_number}, transaction_id: {order.transaction_id}")

            # ✅ Save payment details in Payment model
            payment = Payment(
                user=order.user,
                paypal_order_id=order.paypal_order_id,
                transaction_id=payment_id,
                payment_method="PayPal",
                order_total=order.order_total,
                amount_paid=amount_paid,  # ✅ Stores actual payment amount
                status=payment_status
            )
            payment.save()

            print("Payment details successfully saved in Payment model!")

            return JsonResponse({
                "message": "Payment captured successfully!",
                "order_id": order_id,
                "status": payment_status,
                "payment_id": payment.transaction_id  # ✅ Ensure it's returned correctly
            })
        else:
            print(f"Order not found for PayPal ID: {order_id}")
            return JsonResponse({"error": "Order not found in the database."}, status=404)
    else:
        return JsonResponse({"error": "Failed to capture PayPal order", "details": response_data}, status=response.status_code)