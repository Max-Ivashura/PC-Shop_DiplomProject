# core/views.py
from django.shortcuts import render
from products.models import Product

def home(request):
    bestsellers = Product.objects.order_by('-created_at')[:4]
    return render(request, 'home.html', {'bestsellers': bestsellers})