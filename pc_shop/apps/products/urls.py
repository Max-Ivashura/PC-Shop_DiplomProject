from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from .views import ProductListView, ProductDetailView, SearchView

urlpatterns = [
    # Каталог товаров
    path('catalog/', ProductListView.as_view(), name='product_list'),

    # Товары по категории (поддержка древовидных категорий)
    path('catalog/<path:category_slug>/', ProductListView.as_view(),
         name='product_list_by_category'),

    # Детальная страница товара
    path('product/<slug:product_slug>/', ProductDetailView.as_view(),
         name='product_detail'),

    # Поиск с поддержкой фильтров
    path('search/', SearchView.as_view(), name='product_search'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)