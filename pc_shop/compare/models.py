from django.db import models
from products.models import Product

class Comparison(models.Model):
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    products = models.ManyToManyField(Product)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Сравнение {self.user.username} - {self.products.count()} товаров"