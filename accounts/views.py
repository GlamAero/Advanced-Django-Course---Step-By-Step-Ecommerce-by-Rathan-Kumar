from django.shortcuts import render, redirect
from .forms import RegistrationForm
from .models import Account
from django.contrib import messages, auth
from django.contrib.auth.decorators import login_required
from carts.models import Cart, CartItem
from carts.views import _cart_id
import requests


# Verification email imports:
from django.contrib.sites.shortcuts import get_current_site
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import EmailMessage



# Create your views here.

def register(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)

        # 'form.is_valid()' checks if the form data is valid according to the validation rules defined in the form class.
        if form.is_valid():

            # 'form.cleaned_data' is a dictionary that contains the cleaned and validated data(when the user has filled in 'forms.py') from the form. It is used to access the individual fields of the form after validation.
            first_name = form.cleaned_data['first_name']
            last_name = form.cleaned_data['last_name']
            phone_number = form.cleaned_data['phone_number']
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']

            # USE EMAIL PREFIX AS USERNAME:
            # 'username' is created by splitting the email address at the '@' symbol and taking the first part[0], which is typically the user's name or identifier before the '@' in their email address.
            # 'username' is used as a unique identifier for the user in the system, and it is derived from the email address to ensure that it is unique and meaningful.
            username = email.split('@')[0]  
            

            # Create a new user instance using the custom user manager
            # 'Account.objects.create_user' is a method that creates a new user instance in the database using the custom user manager defined in 'models.py'. 
            # Note that phone number is not here. This is because in the 'models.py' file, in the function 'create_user', phone number is not a field. However, phone number is added separately.
            user = Account.objects.create_user(
                first_name=first_name,
                last_name=last_name,
                email=email,
                username = username,
                password=password
            )

            # Set additional user attributes
            # 'user.phone_number' is set to the phone number provided in the registration form. This allows the user to have a phone number associated with their account.
            # This is useful for account recovery, notifications, or any other purpose where a phone number might be needed.
            # However, it is important to note that the phone number field is optional, as indicated by the 'blank=True' attribute in the 'Account' model.
            user.phone_number = phone_number

            # Save the form data to the database
            user.save()


            # USER ACTIVATION AFTER REGISTRATION:

            # Get the current site domain
            current_site = get_current_site(request)
            mail_subject = "Please activate your account"

            # 'render_to_string' is a function that renders a template with the given context data and returns the rendered HTML as a string.
            message = render_to_string('accounts/account_verification_email.html', {
                'user': user,
                'domain': current_site,
                'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                'token': default_token_generator.make_token(user),
            })

            # 'to_email' is the email address which the activation email will be sent to.
            to_email = email
            send_email = EmailMessage(
                mail_subject, message, to=[to_email]
            )
            send_email.send()


            # '?command=verification&email='+email' is part of the content in the user's browser url after they registered and are sent the verification email.
            # this means the user has not yet verified themselves by checking their mail and has not clicked the link sent to them to verify.
            # to login and get authenticated, the user needs to click the link in their email. That link verifies them and redirects them to 'login' page to login. This is evident in the function 'activate' below

            # the below 'return redirect' sends the user to the 'login.html' page but a unique one with '?command=verification&email='+email', where '+email' concatenates as the email of the user the email is sent to as given above. This is evident in accounts/login.html page.
            return redirect('/accounts/login/?command=verification&email='+email)
            
    else:
        form = RegistrationForm()

    context = {
        'form' : form
    }
    return render(request, 'accounts/register.html', context)



def login(request):
    if request.method == 'POST':
        email = request.POST['email']
        password = request.POST['password']

        # Authenticate the user
        user = auth.authenticate(request, username=email, password=password)
        
        # If the user is found in the database:
        if user is not None:
            try:
                # get the cart objects and cart_items of the user whose accounts details is found in the database from the database
                cart = Cart.objects.get(cart_id=_cart_id(request))

                is_cart_item_exists = CartItem.objects.filter(cart=cart).exists()

                # BEFORE LOGGING A USER IN, CHECK IF THERE IS/ARE CART ITEMS ASSOCIATED WITH A CART OF A UNIQUE 'cart_id' AS ABOVE:
                if is_cart_item_exists:

                    # use the 'cart' alone to get the CartItem objects. 
                    # That is 'cart_item' here is all the items in a particular cart of a unique 'cart_id' (e.g AIR JORDAN of color: blue and size: medium;  RTX SHIRT of color: red and size: small;  VIVO JEANS of color: green and size: large etc.).
                    # This cart item is not yet linked to a user
                    cart_item = CartItem.objects.filter(cart=cart)


                    # GETTING THE PRODUCT VARIATION BY 'cart_id':

                    product_variation = []

                    # for each item(e.g Air Jordan of color: blue and size: medium of quantity: 3) in the particular cart of a unique cart_id
                    for item in cart_item:

                        # 'item.variations.all' here return all the variations of each product in the cart. (For example color: blue and size: medium  -- for RTX SHIRT)
                        variation = item.variations.all()
                        
                        product_variation.append(list(variation))


                    # FOR A USER WHO IS ABOUT TO LOG IN, GET THE Cart_Item OF THE USER TO ACCESS HIS PRODUCT VARIATION:
                    cart_item = CartItem.objects.filter(user=user) 

                    ex_var_list = [] # Stores variations of each cart item
                    id = [] # Stores IDs of cart items

                    # From the above, 'cart_item' is a collection (queryset) of CartItem objects (e.g Air Jordan of color: Black and size: Medium, Air Jordan of color: White and size: Medium, Air Jordan of color: Yellow and size: Large) that the user who is logging in has in their cart

                    # Here, 'item' represents each individual CartItem during iteration (e.g. Air Jordan of color: Black and size: Medium) that the user who is about logging in has in their cart
                    for item in cart_item:

                        # this means the all the variations of each item in the cart of the user about to log in(e.g color: black, size: red, etc of product ATX Shirt that was added to cart previously by the user in the previous cart_session)
                        existing_variation = item.variations.all()
                        
                        ex_var_list.append(list(existing_variation))

                        id.append(item.id)

                        # for each item variation in the list of variations in a given cart before log in:
                    for pr in product_variation:

                        # if an item variation(that is in the list of variations in a given cart before log in) is found in the list of item variations of a particular user(when they previously logged in and added to cart):
                        if pr in ex_var_list:

                            index = ex_var_list.index(pr)

                            item_id = id[index]

                            item = CartItem.objects.get(id  = item_id)

                            item.quantity += 1

                            item.user = user

                            item.save()

                            # if an item variation(that is in the list of variations in a given cart before log in) is not found in the list of item variations of a particular user(when they previously logged in and added to cart):
                        else:
                            cart_item = CartItem.objects.filter(cart=cart)

                            for item in cart_item:
                                item.user = user
                                item.save()  
                    
            except:
                pass

            # log them in
            auth.login(request, user)
            messages.success(request, "You are now logged in")

            # IF WE ARE VISITING ANY PAGE WHICH REQUIRES TO LOGIN FIRST TO VIEW THE PAGE:
            # the below will hold the url of any previous page was referring to(or was trying to get access to) which requires login(for example, if a user who is not logged in is trying to access the checkout page after adding to cart, he or she would be redirected to 'login' page and thereafter 'dashboard' page which 'login' page leads to. 
            # However, with this, this url now holds the original url(e.g checkout) which the user intended to go to
            url = request.META.get('HTTP_REFERER')

            try:
                
                query = requests.utils.urlparse(url).query # next=/cart/checkout/
                
                # the below converts the query above to a dictionary:
                params = dict(x.split('=') for x in query.split('&')) # {'next': '/cart/checkout/'}

                if 'next' in params:
                    nextPage = params['next']
                    return redirect(nextPage)

            except:
                return redirect('dashboard')
            
        else:
            messages.error(request, "Invalid login credentials")
            return redirect('login')
        
    return render(request, 'accounts/login.html')



@login_required(login_url = 'login')
def logout(request):
    auth.logout(request)
    messages.success(request, 'You are logged out.')
    return redirect('login')


# This function 'activate' is called in 'account_verification_email.html' as part of the url link the user clicks in order to activate their account.
def activate(request, uidb64, token):
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        # '_default_manager' here is 
        user = Account._default_manager.get(pk=uid)
    except (TypeError, ValueError, OverflowError, Account.DoesNotExist):
        user = None
    if user is not None and default_token_generator.check_token(user, token):
        user.is_active = True
        user.save()
        messages.success(request, 'Your account has been activated successfully.')
        return redirect('login')
    else:
        messages.error(request, 'Activation link is invalid!')
        return redirect('register')


@login_required(login_url='login')
def dashboard(request):
    
    return render(request, 'accounts/dashboard.html') 


def forgotPassword(request):
    if request.method == 'POST':
        email = request.POST['email']
        if Account.objects.filter(email=email).exists():


            # RESET PASSWORD EMAIL

            # '_exact' means the email should be case sensitive.
            # if it were '_iexact' it means the email should be case insensitive.
            user = Account.objects.get(email__exact=email)

            current_site = get_current_site(request)
            mail_subject = "Please reset your password"

            # 'render_to_string' is a function that renders a template with the given context data and returns the rendered HTML as a string.
            message = render_to_string('accounts/reset_password_email.html', {
                'user': user,
                'domain': current_site,
                'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                'token': default_token_generator.make_token(user),
            })

            # 'to_email' is the email address which the reset_password email will be sent to.
            to_email = email
            send_email = EmailMessage(
                mail_subject, message, to=[to_email]
            )
            send_email.send()

            messages.success(request, 'Password reset email has been sent to your email address')
            return redirect('login')

        else:
            messages.error(request, 'Account does not exist!')
            return redirect('forgotPassword')

    return render(request, 'accounts/forgotPassword.html')


def resetpassword_validate(request, uidb64, token):
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        # '_default_manager' here is 
        user = Account._default_manager.get(pk=uid)
    except (TypeError, ValueError, OverflowError, Account.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):

        # pass/save the 'uid' into request.session
        request.session['uid'] = uid
        messages.success(request, 'Please reset your password')

        return redirect('resetPassword')
    else:
        messages.error(request, 'This link is expired')
        return redirect('login')


def resetPassword(request):
    if request.method == 'POST':
        password = request.POST['password']
        confirm_password = request.POST['confirm_password']

        if password == confirm_password:

            # get/retrieve the 'uid' from the session in function- 'resetpassword_validate' and pass it as 'uid'
            uid = request.session.get('uid')
            user = Account.objects.get(pk=uid)

            # use django default function- 'set_password()' to set the password and save it in the hashed format
            user.set_password(password)
            
            user.save()
            messages.success(request, 'Password reset successful')
            return redirect('login')
        else:
            messages.error(request, 'Passwords do not match')
            return redirect('resetPassword')
    else:
        return render(request, 'accounts/resetPassword.html')


