from django import forms
from .models import Account


# 'RegistrationForm' is a subclass of 'forms.ModelForm', which means it inherits from the Django ModelForm class.
class RegistrationForm(forms.ModelForm):

    password = forms.CharField(widget=forms.PasswordInput(attrs={ 'placeholder': 'Enter Password'
    }))
    confirm_password = forms.CharField(widget=forms.PasswordInput(attrs={
        'placeholder': 'Confirm Password'
    }))
    

    class Meta:
        model = Account
        fields = ['first_name', 'last_name', 'phone_number', 'email', 'password']

    
    
    def __init__(self, *args, **kwargs):

        # 'super' is used to call the parent class's constructor, which initializes the form with the provided arguments.
        # This allows the form to inherit the behavior and attributes of the parent class while also allowing for customization in the child class.
        # '__init__' is a special method in Python that is called when an instance of the class is created. It is used to initialize the attributes of the class.
        super(RegistrationForm, self).__init__(*args, **kwargs)

        self.fields['first_name'].widget.attrs['placeholder'] = 'Enter First Name'
        self.fields['last_name'].widget.attrs['placeholder'] = 'Enter Last Name'
        self.fields['phone_number'].widget.attrs['placeholder'] = 'Enter Phone Number'
        self.fields['email'].widget.attrs['placeholder'] = 'Enter Email Address'

        # for each of the above, give it a bootstrap class of 'form-control':
        for field in self.fields:
            self.fields[field].widget.attrs['class'] = 'form-control'

    
    # TO ENSURE PASSWORDS MATCH WHEN REGISTERING AND TO ENSURE THAT PASSWORD IS AT LEAST 8 CHARACTERS LONG, WE OVERIDE THE 'clean' METHOD:
    
    def clean(self):

        # The 'clean' method is a built-in method in Django forms that is used to perform custom validation on the form data.
        # 'clean' method is called to validate the form data and perform any additional checks or transformations before saving the data to the database.
        cleaned_data = super(RegistrationForm, self).clean()

        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')

        # Check if there is 'password' and 'confirm_password' and if they do not match
        # The below is a 'non field error'(errors across multiple fields(in this case 'password' and 'confirm_password' fields) in a form) that we raised when the passwords do not match.
        if password and confirm_password and password != confirm_password:
            raise forms.ValidationError("Passwords do not match! Please try again.")

        # Ensure the password is at least 8 characters long
        if password and len(password) < 8:
            raise forms.ValidationError("Password must be at least 8 characters long")
        
        # 'cleaned_data' is a dictionary containing the form data that has been validated and cleaned. It is used to access the individual fields of the form after validation. 
        # In this case, it contains the cleaned data for the 'password' and 'confirm_password' fields.
        return cleaned_data

        