import time

from django.core.validators import RegexValidator, FileExtensionValidator
from django.db import models
from django.contrib.auth.models import User

from apps.products.models import Product
from django.core.files.storage import default_storage


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone = models.CharField(
        "Телефон",
        max_length=20,
        blank=True,
        validators=[
            RegexValidator(
                regex=r'^\+7\s\(\d{3}\)\s\d{3}-\d{2}-\d{2}$',
                message="Формат телефона: +7 (XXX) XXX-XX-XX"
            )
        ]
    )
    address = models.CharField("Адрес", max_length=255, blank=True)
    birth_date = models.DateField("Дата рождения", null=True, blank=True)

    def user_directory_path(instance, filename):
        ext = filename.split('.')[-1]
        return f'avatars/{instance.user.id}_{int(time.time())}.{ext}'

    avatar = models.ImageField(
        "Аватар",
        upload_to=user_directory_path,
        blank=True,
        validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png'])]
    )

    def save(self, *args, **kwargs):
        # Удаляем старую аватарку при обновлении
        try:
            old_instance = UserProfile.objects.get(id=self.id)
            if old_instance.avatar and old_instance.avatar != self.avatar:
                if default_storage.exists(old_instance.avatar.name):
                    default_storage.delete(old_instance.avatar.name)
        except UserProfile.DoesNotExist:
            pass

        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        # Удаляем аватарку при удалении профиля
        if self.avatar:
            if default_storage.exists(self.avatar.name):
                default_storage.delete(self.avatar.name)
        super().delete(*args, **kwargs)

    def __str__(self):
        return f"Профиль: {self.user.username}"

    @property
    def is_adult(self):
        """Проверка, является ли пользователь совершеннолетним."""
        if self.birth_date:
            from datetime import date
            today = date.today()
            age = today.year - self.birth_date.year - (
                    (today.month, today.day) < (self.birth_date.month, self.birth_date.day)
            )
            return age >= 18
        return False

    class Meta:
        verbose_name = "Профиль пользователя"
        verbose_name_plural = "Профили пользователей"


class Wishlist(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Wishlist of {self.user.username}"

    def add_product(self, product):
        """Добавление товара через промежуточную модель."""
        WishlistItem.objects.get_or_create(wishlist=self, product=product)

    def remove_product(self, product):
        """Удаление товара через промежуточную модель."""
        WishlistItem.objects.filter(wishlist=self, product=product).delete()

    def has_product(self, product):
        """Проверка наличия товара через промежуточную модель."""
        return WishlistItem.objects.filter(wishlist=self, product=product).exists()


class WishlistItem(models.Model):
    wishlist = models.ForeignKey(Wishlist, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-added_at']
        unique_together = ('wishlist', 'product')  # Запрет дубликатов
