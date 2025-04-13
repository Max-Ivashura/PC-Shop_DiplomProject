from celery import shared_task
from django.utils import timezone
from .models import Cart

@shared_task
def release_abandoned_carts():
    """Освобождение брони через 1 час неактивности"""
    expired = timezone.now() - timezone.timedelta(hours=1)
    carts = Cart.objects.filter(
        converted_order__isnull=True,
        updated_at__lt=expired
    )
    for cart in carts:
        cart.release_stock()