from django.db import models
from products.models import Product
from django.contrib.auth import get_user_model

class Comparison(models.Model):
    user = models.ForeignKey(
        get_user_model(),
        on_delete=models.CASCADE,
        related_name='comparisons'  # ← Должно быть именно 'comparisons'
    )
    products = models.ManyToManyField(Product)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Сравнение {self.user.username} - {self.products.count()} товаров"