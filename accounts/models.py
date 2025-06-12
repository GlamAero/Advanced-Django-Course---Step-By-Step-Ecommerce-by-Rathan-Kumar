from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin

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
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin, Group, Permission


# (Your existing MyAccountManager stays the same)


class Account(AbstractBaseUser, PermissionsMixin):
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)
    username = models.CharField(max_length=30, unique=True)
    email = models.EmailField(max_length=254, unique=True)
    phone_number = models.CharField(max_length=15, blank=True)

    date_joined = models.DateTimeField(auto_now_add=True)
    last_login = models.DateTimeField(auto_now_add=True)
    is_admin = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=False)
    is_superadmin = models.BooleanField(default=False)

    # Add these two fields to avoid clash with Vendor model
    groups = models.ManyToManyField(
        Group,
        related_name='account_user_set',
        blank=True,
        help_text='The groups this user belongs to.',
        verbose_name='groups'
    )
    user_permissions = models.ManyToManyField(
        Permission,
        related_name='account_user_permissions',
        blank=True,
        help_text='Specific permissions for this user.',
        verbose_name='user permissions'
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

    objects = MyAccountManager()

    def __str__(self):
        return self.email

    def has_perm(self, perm, obj=None):
        return self.is_admin

    def has_module_perms(self, add_label):
        return True
