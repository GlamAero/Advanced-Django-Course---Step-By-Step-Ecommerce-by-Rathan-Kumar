# orders/forms.py
from django import forms
from .models import Order, Refund, Dispute, OrderItem
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator

class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True

class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            result = [single_file_clean(d, initial) for d in data]
        else:
            result = single_file_clean(data, initial)
        return result

class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = [
            'first_name', 'last_name', 'phone', 'email', 
            'address_line_1', 'address_line_2', 'country', 
            'state', 'city', 'postal_code', 'order_note'
        ]
        
        widgets = {
            'order_note': forms.Textarea(attrs={
                'rows': 3, 
                'placeholder': 'Any special instructions or notes about your order'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            self.fields[field].widget.attrs.update({
                'class': 'form-control',
                'autocomplete': 'on'
            })
            if field in ['first_name', 'last_name']:
                self.fields[field].widget.attrs['autocomplete'] = 'name'
            elif field == 'email':
                self.fields[field].widget.attrs['autocomplete'] = 'email'
            elif field == 'phone':
                self.fields[field].widget.attrs['autocomplete'] = 'tel'

class RefundRequestForm(forms.ModelForm):
    products = forms.ModelMultipleChoiceField(
        queryset=OrderItem.objects.none(),
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        required=True,
        label="Products to Refund"
    )
    additional_info = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
        required=False,
        label="Additional Information"
    )

    class Meta:
        model = Refund
        fields = ['reason', 'additional_info', 'products']
        widgets = {
            'reason': forms.Textarea(attrs={
                'rows': 4,
                'class': 'form-control',
                'placeholder': 'Please explain why you are requesting a refund'
            }),
        }

    def __init__(self, *args, **kwargs):
        order = kwargs.pop('order', None)
        super().__init__(*args, **kwargs)
        if order:
            self.fields['products'].queryset = order.items.filter(
                refunded=False
            )

class DisputeForm(forms.ModelForm):
    evidence_files = MultipleFileField(
        required=False,
        label="Upload Evidence Files",
        help_text="Max 5 files (images, documents, etc.), 5MB each",
        widget=MultipleFileInput(attrs={'class': 'form-control'})
    )

    class Meta:
        model = Dispute
        fields = ['reason', 'details']
        widgets = {
            'reason': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Brief reason for dispute'
            }),
            'details': forms.Textarea(attrs={
                'rows': 5, 
                'class': 'form-control',
                'placeholder': 'Detailed description of the issue'
            }),
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['reason'].help_text = "e.g. Item not received, Wrong item shipped, Damaged product"
        self.fields['details'].help_text = "Please provide as much detail as possible including dates, times, and communications"

    def clean_evidence_files(self):
        files = self.cleaned_data.get('evidence_files')
        if files:
            if len(files) > 5:
                raise ValidationError("You can upload up to 5 files")
            for file in files:
                if file.size > 5 * 1024 * 1024:  # 5MB limit
                    raise ValidationError("File too large (max 5MB)")
                ext = file.name.split('.')[-1].lower()
                if ext not in ['jpg', 'jpeg', 'png', 'pdf', 'doc', 'docx']:
                    raise ValidationError("Unsupported file format")
        return files