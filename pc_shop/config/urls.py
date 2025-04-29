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
    path('accounts/', include('accounts.urls')),
    path('cart/', include('cart.urls')),
    path('compare/', include('compare.urls')),
    path('configurator/', include('configurator.urls')),
    path('products/', include('products.urls')),

]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
