from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import UserProfile, Wishlist

@receiver(post_save, sender=User)
def create_user_related_objects(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)
        Wishlist.objects.create(user=instance)  # Создаем Wishlist