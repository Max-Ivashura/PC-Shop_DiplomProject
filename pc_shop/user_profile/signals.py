from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import UserProfile

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        try:
            instance.userprofile  # Проверка существования профиля
        except UserProfile.DoesNotExist:
            UserProfile.objects.create(user=instance)