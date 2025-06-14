from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager

# to create custom user model:

# here we use the model class:'Account' below to make this model class:'MyAccountManager' work:
class MyAccountManager(BaseUserManager):

    # creating a normal user:
    # only core fields are here, thus you will notice that 'phone_number' is not present here, since 'phone_number' is set to 'blank=True'(optional) in the Account class model below.
    def create_user(self, first_name, last_name, username, email, password=None):
        if not email: 
            raise ValueError('User must have an email address')
        
        if not username:
            raise ValueError('User must have a username')
        
        # in the below, 'self.normalize_email' is a method that normalizes the email address by converting it to lowercase and removing any leading or trailing whitespace:
        user = self.model(
            email=self.normalize_email(email),
            username=username,
            first_name=first_name,
            last_name=last_name
        )

        # change the password to the hashed version of the password:
        user.set_password(password)  
        user.save(using=self._db)
        return user


    # creating a superuser:
    def create_superuser(self, first_name, last_name, email, username, password):
        user = self.create_user(
            email=self.normalize_email(email),
            username=username,
            password=password,
            first_name=first_name,
            last_name=last_name
        )

        # set the superuser permissions:
        user.is_admin = True
        user.is_active = True
        user.is_staff = True 
        user.is_superadmin = True
        user.save(using=self._db)
        return user



# Create your models here:
class Account(AbstractBaseUser):
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)
    username = models.CharField(max_length=30, unique=True)
    email = models.EmailField(max_length=254, unique=True)

    # since 'phone_number' can be blank as set below, in the 'create_user' function above, 'phone number' is not there since it is optional and not a core field
    phone_number = models.CharField(max_length=15, blank=True)
    
    # Required fields
    date_joined = models.DateTimeField(auto_now_add=True)
    last_login = models.DateTimeField(auto_now_add=True)
    is_admin = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=False)
    is_superadmin = models.BooleanField(default=False)


    # 'USERNAME FIELD' here means to specify the content expected in the default 'USERNAME' field when 'logging in' to the admin. This overides the default 'USERNAME' field expected to be filled in, with 'EMAIL'.
    USERNAME_FIELD = 'email'

    # This is the required filled expected to be filled by the user when 'signing up' for access to the custom django user admin page:
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

    # telling this model 'Account', that it is being used in another model above called 'MyAccountManager':
    objects = MyAccountManager()

    def __str__(self):
        return self.email


    # This gives full permission to the admin to make modifications necessary in the page as he deems fit
    def has_perm(self, perm, obj=None):
        return self.is_admin
    
    def has_module_perms(self, add_label):
        return True

