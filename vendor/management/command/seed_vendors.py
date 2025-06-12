from django.core.management.base import BaseCommand
from vendor.models import Vendor

class Command(BaseCommand):
    help = "Seed initial vendor data"

    def handle(self, *args, **kwargs):
        Vendor.objects.create_vendor(
            email="vendor1@example.com",
            business_name="Store A",
            password="strongpass123",
            is_staff=False  # no admin access
        )

        Vendor.objects.create_vendor(
            email="adminvendor@example.com",
            business_name="Store Admin",
            password="adminpass456",
            is_staff=True  # admin panel access
        )

        self.stdout.write(self.style.SUCCESS("Successfully created vendors."))
