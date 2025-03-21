from django.db import models
from django.contrib.auth import get_user_model
from products.models import Product

User = get_user_model()

class Wishlist(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    products = models.ManyToManyField(Product, blank=True, related_name='wishlists')

    def __str__(self):
        return f"Wishlist of {self.user.username}"