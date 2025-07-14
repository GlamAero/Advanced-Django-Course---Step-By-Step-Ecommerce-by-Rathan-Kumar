from django.db.models.signals import pre_save
from django.dispatch import receiver
from .models import Payment

@receiver(pre_save, sender=Payment)
def update_order_status_on_payment_change(sender, instance, **kwargs):
    """
    Update order status when payment status changes
    """
    if instance.pk:
        try:
            original = Payment.objects.get(pk=instance.pk)
            if original.status != instance.status:
                if instance.status == 'COMPLETED' and instance.order:
                    instance.order.status = 'Processing'
                    instance.order.save()
                elif instance.status == 'FAILED' and instance.order:
                    instance.order.status = 'Pending Payment'
                    instance.order.save()
        except Payment.DoesNotExist:
            # Handle case where payment was deleted
            pass
        