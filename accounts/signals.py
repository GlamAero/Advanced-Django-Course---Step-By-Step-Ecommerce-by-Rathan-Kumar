from django.db.models.signals import post_save
from django.dispatch import receiver
from allauth.account.signals import user_signed_up
from .models import Account, VendorProfile, CustomerProfile
from django.db import transaction, IntegrityError


@receiver(user_signed_up)
def social_user_signed_up(request, user, **kwargs):
    social_account = user.socialaccount_set.first()
    extra_data = social_account.extra_data if social_account else {}
    company_name = extra_data.get('hd')
    dob = extra_data.get('birthday')

    if user.is_vendor():
        VendorProfile.objects.get_or_create(
            user=user,
            defaults={
                'company_name': company_name or user.first_name,
                'website': extra_data.get('website', '')
            }
        )
    else:
        CustomerProfile.objects.get_or_create(
            user=user,
            defaults={
                'date_of_birth': dob,
                'preferred_contact_method': 'email'
            }
        )


@receiver(post_save, sender=Account)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        try:
            with transaction.atomic():
                if instance.is_vendor():
                    VendorProfile.objects.get_or_create(
                        user=instance,
                        defaults={'company_name': instance.email}
                    )
                else:
                    CustomerProfile.objects.get_or_create(
                        user=instance,
                        defaults={'preferred_contact_method': 'email'}
                    )
        except IntegrityError:
            # Handle race condition gracefully
            pass
