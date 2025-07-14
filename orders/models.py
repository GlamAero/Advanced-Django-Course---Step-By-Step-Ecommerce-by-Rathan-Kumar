from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator
from accounts.models import Account, VendorProfile
from store.models import Product, Variation
import uuid
from decimal import Decimal
from django.conf import settings



class Payment(models.Model):
    class PaymentMethods(models.TextChoices):
        PAYPAL = 'paypal', 'PayPal'
        STRIPE = 'stripe', 'Stripe'
        FLUTTERWAVE = 'flutterwave', 'Flutterwave'
        BANK_TRANSFER = 'bank_transfer', 'Bank Transfer'
        CASH_ON_DELIVERY = 'cash_on_delivery', 'Cash on Delivery'
        CRYPTO = 'cryptocurrency', 'Cryptocurrency'
        CARD = 'card', 'Card'
        CREDIT_CARD = 'credit_card', 'Credit Card'
        DEBIT_CARD = 'debit_card', 'Debit Card'

    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        COMPLETED = 'COMPLETED', 'Completed'
        FAILED = 'FAILED', 'Failed'
        REFUNDED = 'REFUNDED', 'Refunded'
        CANCELED = 'CANCELED', 'Canceled'

    user = models.ForeignKey(Account, on_delete=models.CASCADE, related_name="payments")
    payment_method = models.CharField(
        max_length=30,
        choices=PaymentMethods.choices,
        default=PaymentMethods.PAYPAL,
    )
    transaction_id = models.CharField(max_length=100, unique=True, null=True, blank=True)
    amount_paid = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Payment"
        verbose_name_plural = "Payments"
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['transaction_id']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.get_payment_method_display()} - {self.transaction_id or 'No ID'}"

class Order(models.Model):
    class Status(models.TextChoices):
        NEW = 'New', 'New'
        PENDING_PAYMENT = 'Pending Payment', 'Pending Payment'
        ACCEPTED = 'Accepted', 'Accepted'
        PROCESSING = 'Processing', 'Processing'
        SHIPPED = 'Shipped', 'Shipped'
        DELIVERED = 'Delivered', 'Delivered'
        CANCELLED = 'Cancelled', 'Cancelled'
        REFUNDED = 'Refunded', 'Refunded'
        RETURNED = 'Returned', 'Returned'

    user = models.ForeignKey(Account, on_delete=models.SET_NULL, null=True, related_name="orders")
    payment = models.OneToOneField(Payment, on_delete=models.SET_NULL, blank=True, null=True, related_name="order")
    order_number = models.CharField(max_length=50, unique=True, editable=False)
    order_key = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    is_ordered = models.BooleanField(default=False)
    
    # Gateway IDs
    paypal_order_id = models.CharField(max_length=255, blank=True, null=True)
    stripe_payment_intent = models.CharField(max_length=255, blank=True, null=True)
    flutterwave_tx_ref = models.CharField(max_length=255, blank=True, null=True)

    # Customer information
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20)
    email = models.EmailField(max_length=100)
    
    # Shipping address
    address_line_1 = models.CharField(max_length=255)
    address_line_2 = models.CharField(max_length=255, blank=True)
    country = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    city = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20, blank=True)
    
    # Order details
    order_note = models.TextField(blank=True, null=True)
    subtotal = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    tax = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    shipping = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    discount = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    total = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )

    coupon = models.ForeignKey(
        'coupons.Coupon', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='orders'
    )
    
    # Order status
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.NEW,
    )
    ip = models.GenericIPAddressField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Order"
        verbose_name_plural = "Orders"
        indexes = [
            models.Index(fields=['order_number']),
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return self.order_number

    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = f"ORD-{timezone.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
        super().save(*args, **kwargs)
    
    def get_vendor(self):
        """Get the primary vendor associated with this order"""
        if self.items.exists():
            return self.items.first().product.vendor
        return None
    
    def update_total(self):
        """Recalculate order total based on items"""
        self.subtotal = self.items.aggregate(
            total=models.Sum(models.F('price') * models.F('quantity'))
        )['total'] or Decimal('0.00')
        self.total = self.subtotal + self.tax + self.shipping - self.discount
        self.save(update_fields=['subtotal', 'total'])
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    @property
    def full_address(self):
        parts = [self.address_line_1, self.address_line_2]
        return ", ".join(filter(None, parts))

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='order_items')
    variations = models.ManyToManyField(Variation, blank=True)
    vendor = models.ForeignKey(VendorProfile, on_delete=models.SET_NULL, null=True, related_name='order_items')
    payout = models.ForeignKey('VendorPayout', on_delete=models.SET_NULL, null=True, blank=True, related_name='items')
    
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    ordered = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    refunded = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Order Item"
        verbose_name_plural = "Order Items"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['vendor']),
            models.Index(fields=['payout']),
        ]

    def __str__(self):
        return f"{self.product.product_name} x {self.quantity}"

    def save(self, *args, **kwargs):
        if not self.vendor:
            self.vendor = self.product.vendor
        super().save(*args, **kwargs)
    
    @property
    def total_price(self):
        return self.price * self.quantity
    
    @property
    def payment_method(self):
        return self.order.payment.payment_method if self.order.payment else None

class Refund(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('completed', 'Completed'),
    ]

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='refunds')
    items = models.ManyToManyField(OrderItem, related_name='refunds')
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    transaction_id = models.CharField(max_length=100, blank=True, null=True)
    requested_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-requested_at"]
        verbose_name = "Refund"
        verbose_name_plural = "Refunds"
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['requested_at']),
        ]

    def __str__(self):
        return f"Refund #{self.id} for {self.order.order_number}"

    def save(self, *args, **kwargs):
        if not self.amount or self.amount == Decimal('0.00'):
            self.amount = sum(item.total_price for item in self.items.all())
        super().save(*args, **kwargs)
        
    def get_refund_amount(self):
        return self.amount

class Dispute(models.Model):
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('under_review', 'Under Review'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
    ]
    
    RESOLUTION_CHOICES = [
        ('refund_full', 'Full Refund'),
        ('refund_partial', 'Partial Refund'),
        ('return_product', 'Return Product'),
        ('close_no_action', 'Close Without Action'),
    ]

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='disputes')
    item = models.ForeignKey(OrderItem, on_delete=models.CASCADE, related_name='disputes')
    initiated_by = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='disputes')
    reason = models.CharField(max_length=255)
    details = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    resolution = models.CharField(max_length=20, choices=RESOLUTION_CHOICES, blank=True, null=True)
    resolved_by = models.ForeignKey(
        Account, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='resolved_disputes'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Dispute"
        verbose_name_plural = "Disputes"
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"Dispute #{self.id} for {self.order.order_number}"

class DisputeEvidence(models.Model):
    dispute = models.ForeignKey(Dispute, on_delete=models.CASCADE, related_name='evidence')
    file = models.FileField(upload_to='disputes/evidence/%Y/%m/%d/')
    description = models.CharField(max_length=255, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    original_filename = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name = "Dispute Evidence"
        verbose_name_plural = "Dispute Evidence"
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"Evidence #{self.id} for Dispute {self.dispute.id}"

class VendorPayout(models.Model):
    vendor = models.ForeignKey(VendorProfile, on_delete=models.CASCADE, related_name='payouts')
    amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    fee = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    net_amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    method = models.CharField(max_length=50)
    reference = models.CharField(max_length=255, blank=True, null=True)
    status = models.CharField(
        max_length=20,
        choices=[('pending', 'Pending'), ('completed', 'Completed'), ('failed', 'Failed')],
        default='pending'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Vendor Payout"
        verbose_name_plural = "Vendor Payouts"
        indexes = [
            models.Index(fields=['vendor']),
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"Payout #{self.id} to {self.vendor.company_name}"

    def save(self, *args, **kwargs):
        self.net_amount = self.amount - self.fee
        super().save(*args, **kwargs)


class Review(models.Model):
    product = models.ForeignKey(Product, related_name='reviews', on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    rating = models.PositiveIntegerField()
    comment = models.TextField(blank=True)
    is_approved = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Review by {self.user.email} on {self.product}'

