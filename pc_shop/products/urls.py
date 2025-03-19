from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from .views import ProductListView, ProductDetailView
from . import views

urlpatterns = [
    path('catalog/', ProductListView.as_view(), name='product_list'),
    path('catalog/<category_slug>/', ProductListView.as_view(), name='product_list_by_category'),
    path('product/<product_slug>/', ProductDetailView.as_view(), name='product_detail'),
    path('search/', views.product_search, name='product_search'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
