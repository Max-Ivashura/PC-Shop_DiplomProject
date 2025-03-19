from django.contrib import admin
from django.urls import path, include
from core.views import home

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', home, name='home'),
    path('', include('products.urls')),
    path('accounts/', include('accounts.urls')),
    path('cart/', include('cart.urls')),
    path('profile/', include('user_profile.urls')),
    path('', include('configurator.urls')),
    path('wishlist/', include('wishlist.urls')),
    path('compare/', include('compare.urls')),

]
