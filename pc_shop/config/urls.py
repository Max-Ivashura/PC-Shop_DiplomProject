from django.contrib import admin
from django.urls import path, include
from apps.core.views import home
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [
    # ADMIN
    path('admin/', admin.site.urls),
    # MAIN
    path('', home, name='home'),
    # APPS
    path('', include('products.urls')),
    path('accounts/', include('accounts.urls')),
    path('cart/', include('cart.urls')),
    path('', include('configurator.urls')),
    path('compare/', include('compare.urls')),

]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
