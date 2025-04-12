from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from apps.products.views import ProductListView, ProductDetailView, SearchView

urlpatterns = [
    # Каталог с поддержкой фильтров и сортировки
    path('catalog/', ProductListView.as_view(), name='product_list'),

    # Категории с древовидной структурой
    path(
        'catalog/<path:category_slug>/',
        ProductListView.as_view(),
        name='product_list_by_category'
    ),

    # Детальная страница с поддержкой SKU в метаданных
    path(
        'product/<slug:product_slug>/',
        ProductDetailView.as_view(),
        name='product_detail'
    ),

    # Улучшенный поиск с фильтрацией
    path('search/', SearchView.as_view(), name='product_search'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
