import os
from celery import Celery
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
app = Celery('config')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# Периодические задачи
app.conf.beat_schedule = {
    'cleanup-abandoned-carts': {
        'task': 'apps.cart.tasks.release_abandoned_carts',
        'schedule': 3600,  # Каждый час
    },
}