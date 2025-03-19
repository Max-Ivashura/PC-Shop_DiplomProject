from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required
from products.models import Product
from .models import Wishlist

@login_required
def add_to_wishlist(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    wishlist, _ = Wishlist.objects.get_or_create(user=request.user)
    wishlist.products.add(product)
    return redirect('product_detail', product_slug=product.slug)

@login_required
def remove_from_wishlist(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    wishlist = request.user.wishlist
    wishlist.products.remove(product)
    return redirect('wishlist_view')

@login_required
def wishlist_view(request):
    wishlist = request.user.wishlist
    return render(request, 'wishlist/wishlist.html', {'wishlist': wishlist})