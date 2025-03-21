from django.db import models
from django.contrib.auth.models import User
from configurator.models import Build # Если уже создана модель сборок
# from products.models import Review  # Если уже создана модель отзывов

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone = models.CharField("Телефон", max_length=20, blank=True)
    address = models.CharField("Адрес", max_length=255, blank=True)
    birth_date = models.DateField("Дата рождения", null=True, blank=True)


    def __str__(self):
        return f"Профиль: {self.user.username}"

    class Meta:
        verbose_name = "Профиль пользователя"
        verbose_name_plural = "Профили пользователей"