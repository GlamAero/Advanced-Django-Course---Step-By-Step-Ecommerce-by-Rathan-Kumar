from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from decimal import Decimal
from django.db.models import Sum
from store.models import Product, Variation, VariationCombination
from accounts.models import Account
from coupons.models import Coupon
import uuid

def get_distance_from_nigeria(country_code):
    distances = {
        # West Africa
        'BJ': 875,   # Benin
        'BF': 1250,  # Burkina Faso
        'CV': 2600,  # Cape Verde
        'CI': 1080,  # Côte d'Ivoire
        'GM': 2660,  # Gambia
        'GH': 1075,  # Ghana
        'GN': 1550,  # Guinea
        'GW': 2628,  # Guinea-Bissau
        'LR': 1090,  # Liberia
        'ML': 1660,  # Mali
        'MR': 2300,  # Mauritania
        'NE': 850,   # Niger
        'NG': 0,     # Nigeria (domestic)
        'SN': 2200,  # Senegal
        'SL': 1550,  # Sierra Leone
        'TG': 700,   # Togo

        # East Africa
        'BI': 2730,  # Burundi
        'DJ': 3723,  # Djibouti
        'ER': 3449,  # Eritrea
        'ET': 3496,  # Ethiopia
        'KE': 3393,  # Kenya
        'RW': 2800,  # Rwanda (approximate)
        'SO': 3700,  # Somalia (approximate)
        'SS': 3200,  # South Sudan (approximate)
        'TZ': 3373,  # Tanzania
        'UG': 2751,  # Uganda
        'ZM': 3245,  # Zambia
        'ZW': 3800,  # Zimbabwe (approximate)

        # North Africa
        'DZ': 2223,  # Algeria
        'EG': 3047,  # Egypt
        'LY': 2800,  # Libya (approximate)
        'MA': 2996,  # Morocco
        'SD': 2390,  # Sudan
        'TN': 2800,  # Tunisia (approximate)

        # Central Africa
        'AO': 2464,  # Angola
        'CM': 1150,  # Cameroon (approximate)
        'CF': 1500,  # Central African Republic (approximate)
        'CG': 1500,  # Republic of the Congo (approximate)
        'CD': 2053,  # Democratic Republic of the Congo
        'GA': 1140,  # Gabon
        'GQ': 1300,  # Equatorial Guinea (approximate)
        'ST': 1600,  # São Tomé and Príncipe (approximate)

        # Southern Africa
        'BW': 3889,  # Botswana
        'LS': 4767,  # Lesotho
        'MW': 3758,  # Malawi
        'MZ': 4256,  # Mozambique
        'NA': 3702,  # Namibia
        'SZ': 4646,  # Eswatini
        'ZA': 4644,  # South Africa
        'ZM': 3245,  # Zambia
        'ZW': 3800,  # Zimbabwe

        # Europe (selected countries)
        'AL': 3730,  # Albania
        'AT': 4296,  # Austria
        'BE': 4500,  # Belgium (approximate)
        'BG': 4500,  # Bulgaria (approximate)
        'CH': 4183,  # Switzerland
        'CZ': 4560,  # Czechia
        'DE': 4669,  # Germany
        'DK': 5234,  # Denmark
        'ES': 3688,  # Spain
        'FI': 6027,  # Finland
        'FR': 4163,  # France
        'GB': 5245,  # United Kingdom
        'GR': 3572,  # Greece
        'HU': 4344,  # Hungary
        'IE': 5400,  # Ireland (approximate)
        'IT': 3653,  # Italy
        'NL': 4784,  # Netherlands
        'NO': 5702,  # Norway
        'PL': 4845,  # Poland
        'PT': 3756,  # Portugal
        'RO': 4372,  # Romania
        'RU': 9475,  # Russia (European part)
        'SE': 5725,  # Sweden
        'UA': 4840,  # Ukraine

        # North America
        'CA': 10666, # Canada
        'US': 10661, # United States
        'MX': 11726, # Mexico

        # Central and South America
        'AR': 9126,  # Argentina
        'BR': 7171,  # Brazil
        'CL': 9724,  # Chile
        'CO': 9168,  # Colombia
        'EC': 9705,  # Ecuador
        'GY': 7476,  # Guyana
        'PE': 9493,  # Peru
        'VE': 8294,  # Venezuela

        # Asia
        'AF': 6604,  # Afghanistan
        'BD': 8772,  # Bangladesh
        'BH': 4802,  # Bahrain
        'CN': 9920,  # China
        'IN': 7620,  # India
        'ID': 11708, # Indonesia
        'IR': 5297,  # Iran
        'IQ': 4475,  # Iraq
        'IL': 3642,  # Israel
        'JP': 12745, # Japan
        'MY': 10307, # Malaysia
        'PK': 6698,  # Pakistan
        'PH': 12249, # Philippines
        'QA': 4839,  # Qatar
        'SA': 4200,  # Saudi Arabia
        'SG': 10560, # Singapore
        'SY': 4200,  # Syria
        'TH': 9989,  # Thailand
        'TR': 4239,  # Turkey
        'AE': 5058,  # United Arab Emirates
        'VN': 10796, # Vietnam

        # Oceania / Australia
        'AU': 14200, # Australia (approximate)
        'FJ': 18720, # Fiji
        'PG': 15096, # Papua New Guinea
        'SB': 16904, # Solomon Islands
        'TO': 17000, # Tonga (approximate)
        'NZ': 16000, # New Zealand (approximate)

        # Other Oceanic / Island nations (approximate)
        'WS': 17000, # Samoa
        'VU': 16000, # Vanuatu

        # Default fallback for unknown countries
        'DEFAULT': 5000,
    }
    return distances.get(country_code.upper(), distances['DEFAULT'])


class Cart(models.Model):
    STATUS_CHOICES = (
        ('active', 'Active'),
        ('abandoned', 'Abandoned'),
        ('completed', 'Completed'),
        ('expired', 'Expired'),
    )
    
    cart_id = models.CharField(max_length=250, unique=True, default=uuid.uuid4)
    user = models.ForeignKey(
        Account, 
        on_delete=models.CASCADE, 
        null=True,
        blank=True,
        related_name='carts'
    )
    date_added = models.DateTimeField(auto_now_add=True)
    last_activity = models.DateTimeField(auto_now=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='active'
    )
    coupon = models.ForeignKey(
        Coupon, 
        on_delete=models.SET_NULL, 
        null=True,
        blank=True,
        related_name='carts'
    )
    discount = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    shipping_cost = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    shipping_method = models.CharField(
        max_length=20, 
        choices=[('standard', 'Standard'), ('express', 'Express')],
        default='standard'
    )
    
    class Meta:
        ordering = ['-date_added']
        verbose_name = 'Cart'
        verbose_name_plural = 'Carts'
        indexes = [
            models.Index(fields=['last_activity']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"Cart {self.cart_id} ({self.user.email if self.user else 'Anonymous'})"
    
    @property
    def total(self):
        return sum(item.sub_total for item in self.cart_items.filter(is_active=True))
    
    @property
    def tax(self):
        return (self.total - self.discount) * Decimal('0.02')  # 2% tax
    
    @property
    def grand_total(self):
        return (self.total - self.discount) + self.shipping_cost + self.tax
    
    def calculate_shipping(self):
        """
        Calculate shipping cost:
        - $0.01 per km per kg
        - Shipping discount for very long distances or delayed carts
        """
        total_weight = sum(
            item.product.weight * item.quantity
            for item in self.cart_items.filter(is_active=True)
        ) or 0
        
        if total_weight == 0:
            # No items, no shipping cost
            self.shipping_cost = Decimal('0.00')
            return self.shipping_cost

        is_international = False
        distance_km = 0
        if self.user and hasattr(self.user, 'shipping_address') and self.user.shipping_address:
            is_international = self.user.shipping_address.country != "Nigeria"
            if is_international:
                country_code = getattr(self.user.shipping_address, 'country_code', None)
                if country_code:
                    distance_km = get_distance_from_nigeria(country_code)
                else:
                    distance_km = get_distance_from_nigeria('DEFAULT')
        
        # Domestic shipping flat fee
        if not is_international:
            shipping_fee = Decimal('5.00')
        else:
            # $0.01 per km per kg
            shipping_fee = Decimal('0.01') * Decimal(distance_km) * Decimal(total_weight)
        
        # Expedited shipping premium
        expedited_cost = Decimal('10.00') if self.shipping_method == 'express' else Decimal('0.00')
        shipping_fee += expedited_cost
        
        # Shipping discount for delays and very long distances
        discount = Decimal('0.00')
        from datetime import timedelta
        
        if self.last_activity < timezone.now() - timedelta(days=7):
            discount += shipping_fee * Decimal('0.10')  # 10% discount for delay
        
        if distance_km > 10000:
            discount += shipping_fee * Decimal('0.15')  # 15% discount for very long distance
        
        discount = min(discount, shipping_fee)
        
        self.shipping_cost = shipping_fee - discount
        return self.shipping_cost
    
    def apply_coupon(self, coupon):
        """Apply coupon discount to cart"""
        if self.is_eligible_for_discount(coupon):
            self.coupon = coupon
            
            if coupon.discount_type == 'percentage':
                self.discount = min(
                    self.total * (coupon.discount / Decimal('100.00')),
                    coupon.max_discount or Decimal('100000.00')  # No limit if None
                )
            else:  # fixed amount
                self.discount = min(
                    coupon.discount,
                    self.total
                )
            self.save()
    
    def remove_coupon(self):
        """Remove coupon from cart"""
        self.coupon = None
        self.discount = Decimal('0.00')
        self.save()
    
    def is_eligible_for_discount(self, coupon):
        """Check if cart qualifies for coupon"""
        if coupon.min_purchase and self.total < coupon.min_purchase:
            return False
        
        if coupon.applies_to == 'products':
            product_ids = coupon.products.values_list('id', flat=True)
            if not self.cart_items.filter(product_id__in=product_ids).exists():
                return False
        
        if coupon.applies_to == 'categories':
            category_ids = coupon.categories.values_list('id', flat=True)
            if not self.cart_items.filter(product__category_id__in=category_ids).exists():
                return False
        
        return True
    
    def log_abandonment(self):
        """Mark cart as abandoned"""
        self.status = 'abandoned'
        self.save()
        print(f"Cart {self.cart_id} abandoned")


class CartItem(models.Model):
    user = models.ForeignKey(
        Account, 
        on_delete=models.CASCADE, 
        null=True,
        blank=True,
        related_name='cart_items'
    )
    product = models.ForeignKey(
        Product, 
        on_delete=models.CASCADE,
        related_name='cart_items'
    )
    variations = models.ManyToManyField(
        Variation, 
        blank=True,
        related_name='cart_items'
    )
    cart = models.ForeignKey(
        Cart, 
        on_delete=models.CASCADE, 
        null=True,
        blank=True,
        related_name='cart_items'
    )
    quantity = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('user', 'product', 'cart')
        ordering = ['-created_at']
        verbose_name = 'Cart Item'
        verbose_name_plural = 'Cart Items'
        indexes = [
            models.Index(fields=['is_active']),
        ]

    @property
    def sub_total(self):
        return self.product.price * self.quantity
    
    def get_variation_combination(self):
        if not self.variations.exists():
            return None
        variations = self.variations.all().order_by('variation_category')
        try:
            return VariationCombination.objects.get(
                product=self.product,
                variations=variations
            )
        except VariationCombination.DoesNotExist:
            return None
    
    def clean(self):
        combination = self.get_variation_combination()
        if combination:
            if combination.stock < self.quantity:
                raise ValidationError(
                    f"Only {combination.stock} available in stock for this combination"
                )
        elif self.product.stock < self.quantity:
            raise ValidationError(
                f"Only {self.product.stock} available in stock"
            )
    
    def __str__(self):
        return f"{self.quantity}x {self.product.product_name} ({self.user.email if self.user else 'Anonymous'})"
