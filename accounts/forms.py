from datetime import date
from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password
from django.utils.translation import gettext_lazy as _

from .models import VendorProfile, CustomerProfile, Account

# Conditional recaptcha imports with improved handling
RECAPTCHA_AVAILABLE = False
RecaptchaFieldClass = None
ReCaptchaV3 = None

try:
    from django_recaptcha.fields import ReCaptchaField
    from django_recaptcha.widgets import ReCaptchaV3 as V3Widget
    RecaptchaFieldClass = ReCaptchaField
    ReCaptchaV3 = V3Widget
    RECAPTCHA_AVAILABLE = True
except ImportError:
    pass

# Define a wrapper class for recaptcha
class ConditionalRecaptchaField(forms.Field):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.widget = ReCaptchaV3() if ReCaptchaV3 else None
        self.required = False

    def clean(self, value):
        if not RECAPTCHA_AVAILABLE or not RecaptchaFieldClass:
            return None
            
        if ReCaptchaV3:
            field = RecaptchaFieldClass(widget=ReCaptchaV3())
        else:
            field = RecaptchaFieldClass()
            
        return field.clean(value)

class VendorProfileAdminForm(forms.ModelForm):
    class Meta:
        model = VendorProfile
        fields = '__all__'
        widgets = {
            'business_license_expiry': forms.DateInput(attrs={'type': 'date'}),
        }

    def clean_business_license_number(self):
        license_num = self.cleaned_data.get('business_license_number')
        if license_num and not license_num.replace(' ', '').isalnum():
            raise ValidationError("License number must be alphanumeric")
        return license_num

    def clean_company_name(self):
        company_name = self.cleaned_data.get('company_name')
        if company_name:
            return company_name.strip()
        return company_name

    def clean(self):
        cleaned_data = super().clean()
        expiry = cleaned_data.get('business_license_expiry')
        if expiry and expiry < date.today():
            self.add_error('business_license_expiry', "License has expired")
        return cleaned_data

class CustomerProfileAdminForm(forms.ModelForm):
    class Meta:
        model = CustomerProfile
        fields = '__all__'
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
        }

    def clean_date_of_birth(self):
        dob = self.cleaned_data.get('date_of_birth')
        if dob:
            if dob > date.today():
                raise ValidationError("Date of birth cannot be in the future")
            if (date.today() - dob).days < 365 * 13:
                raise ValidationError("Must be at least 13 years old")
        return dob

class RegistrationForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'placeholder': _('Create strong password'),
            'class': 'form-control',
            'autocomplete': 'new-password'
        }),
        help_text=_("Minimum 12 characters with letters, numbers and symbols")
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'placeholder': _('Confirm password'),
            'class': 'form-control',
            'autocomplete': 'new-password'
        }),
        label=_("Confirm Password")
    )
    terms_agreed = forms.BooleanField(
        required=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label=_("I agree to the terms and privacy policy")
    )

    class Meta:
        model = Account
        fields = ['username', 'first_name', 'last_name', 'phone_number', 'email']
        widgets = {
            'username': forms.TextInput(attrs={'autocomplete': 'username'}),
            'first_name': forms.TextInput(attrs={'autocomplete': 'given-name'}),
            'last_name': forms.TextInput(attrs={'autocomplete': 'family-name'}),
            'phone_number': forms.TextInput(attrs={'autocomplete': 'tel'}),
            'email': forms.EmailInput(attrs={'autocomplete': 'email'}),
        }


    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if not field.widget.attrs.get('class'):
                field.widget.attrs['class'] = 'form-control'

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')

        if password and confirm_password and password != confirm_password:
            self.add_error('confirm_password', _("Passwords do not match"))

        if password:
            try:
                validate_password(password)
            except ValidationError as e:
                self.add_error('password', e)
                
        return cleaned_data

class VendorRegistrationForm(RegistrationForm):
    company_name = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={'placeholder': _('Your business name')}),
        help_text=_("Official registered business name")
    )
    business_license_number = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'placeholder': _('Business license # (optional)')})
    )
    captcha = ConditionalRecaptchaField(label='') if RECAPTCHA_AVAILABLE else None

    class Meta(RegistrationForm.Meta):
        fields = RegistrationForm.Meta.fields + ['company_name', 'business_license_number']

    def clean_company_name(self):
        name = self.cleaned_data['company_name'].strip()
        if VendorProfile.objects.filter(company_name__iexact=name).exists():
            raise ValidationError(_("A business with this name is already registered"))
        return name

class CustomerRegistrationForm(RegistrationForm):
    date_of_birth = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control',
            'max': date.today().isoformat()
        }),
        label=_("Date of Birth")
    )
    marketing_consent = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label=_("Send me product updates and offers")
    )
    captcha = ConditionalRecaptchaField(label='') if RECAPTCHA_AVAILABLE else None

    class Meta(RegistrationForm.Meta):
        fields = RegistrationForm.Meta.fields + ['date_of_birth']

    def clean_date_of_birth(self):
        dob = self.cleaned_data.get('date_of_birth')
        if dob:
            if dob > date.today():
                raise ValidationError("Date of birth cannot be in the future")
            if (date.today() - dob).days < 365 * 13:
                raise ValidationError("You must be at least 13 years old to register")
        return dob

class VendorLoginForm(forms.Form):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': _('business@example.com'),
            'autocomplete': 'email',
            'inputmode': 'email'
        }),
        label=_("Business Email")
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': '••••••••',
            'autocomplete': 'current-password'
        }),
        label=_("Password")
    )
    remember_me = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label=_("Keep me logged in")
    )
    captcha = ConditionalRecaptchaField(label='') if RECAPTCHA_AVAILABLE else None

class CustomerLoginForm(forms.Form):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': _('you@example.com'),
            'autocomplete': 'email',
            'inputmode': 'email'
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': '••••••••',
            'autocomplete': 'current-password'
        })
    )
    remember_me = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label=_("Remember me")
    )
    captcha = ConditionalRecaptchaField(label='') if RECAPTCHA_AVAILABLE else None

class VendorProfileForm(forms.ModelForm):
    class Meta:
        model = VendorProfile
        exclude = ['user', 'created_at', 'updated_at', 'is_verified']
        widgets = {
            'business_license_expiry': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'
        self.fields['business_license_file'].widget.attrs['accept'] = '.pdf,.jpg,.png'
        self.fields['profile_image'].widget.attrs['accept'] = '.jpg,.jpeg,.png'

    def clean_business_license_file(self):
        file = self.cleaned_data.get('business_license_file')
        if file:
            if file.size > 5 * 1024 * 1024:  # 5MB limit
                raise ValidationError(_("File too large (max 5MB)"))
            if not file.name.lower().endswith(('.pdf', '.jpg', '.jpeg', '.png')):
                raise ValidationError(_("Unsupported file format"))
        return file

class CustomerProfileForm(forms.ModelForm):
    class Meta:
        model = CustomerProfile
        exclude = ['user', 'created_at', 'updated_at']
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
            'shipping_address': forms.Textarea(attrs={'rows': 3}),
            'billing_address': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'
        self.fields['profile_picture'].widget.attrs['accept'] = '.jpg,.jpeg,.png'

    def clean_profile_picture(self):
        image = self.cleaned_data.get('profile_picture')
        if image:
            if image.size > 2 * 1024 * 1024:  # 2MB limit
                raise ValidationError(_("Image too large (max 2MB)"))
            if not image.name.lower().endswith(('.jpg', '.jpeg', '.png')):
                raise ValidationError(_("Unsupported image format"))
        return image

class PasswordResetForm(forms.Form):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': _('your@email.com'),
            'autocomplete': 'email'
        })
    )
    captcha = ConditionalRecaptchaField(label='') if RECAPTCHA_AVAILABLE else None

class SetPasswordForm(forms.Form):
    new_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': _('New password'),
            'autocomplete': 'new-password'
        }),
        label=_("New Password")
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': _('Confirm new password'),
            'autocomplete': 'new-password'
        }),
        label=_("Confirm Password")
    )

    def clean(self):
        cleaned_data = super().clean()
        new_password = cleaned_data.get('new_password')
        confirm_password = cleaned_data.get('confirm_password')
        
        if new_password and confirm_password and new_password != confirm_password:
            self.add_error('confirm_password', _("Passwords do not match"))
            
        if new_password:
            try:
                validate_password(new_password)
            except ValidationError as e:
                self.add_error('new_password', e)
                
        return cleaned_data

class PasswordChangeForm(forms.Form):
    old_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': _('Current password'),
            'autocomplete': 'current-password'
        }),
        label=_("Current Password")
    )
    new_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': _('New password'),
            'autocomplete': 'new-password'
        }),
        label=_("New Password")
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': _('Confirm new password'),
            'autocomplete': 'new-password'
        }),
        label=_("Confirm Password")
    )

    def clean(self):
        cleaned_data = super().clean()
        new_password = cleaned_data.get('new_password')
        confirm_password = cleaned_data.get('confirm_password')
        
        if new_password and confirm_password and new_password != confirm_password:
            self.add_error('confirm_password', _("Passwords do not match"))
            
        if new_password:
            try:
                validate_password(new_password)
            except ValidationError as e:
                self.add_error('new_password', e)
                
        return cleaned_data