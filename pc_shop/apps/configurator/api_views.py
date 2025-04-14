import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.contrib.auth.models import User
from apps.products.models import Product
from apps.catalog_config.models import Category
from apps.configurator.models import Build

# Словарь соответствия слагов категорий полям модели Build
CATEGORY_FIELD_MAP = {
    'processors': 'cpu',
    'motherboards': 'motherboard',
    'graphics-cards': 'gpu',
    'ram': 'ram',
    'power-supplies': 'psu',
    'storage': 'storage',
    'cooling-systems': 'cooler',
    'cases': 'case',
}


@require_POST
def save_build(request):
    try:
        data = json.loads(request.body)
        components = data.get('components', {})
        total_price = data.get('total_price', 0)

        # Проверка минимальных требований
        required_components = ['cpu', 'motherboard', 'ram', 'psu']
        if not all(c in components.values() for c in required_components):
            return JsonResponse({
                'success': False,
                'message': 'Отсутствуют обязательные компоненты'
            }, status=400)

        # Получение пользователя
        user = request.user if request.user.is_authenticated else None

        # Создание объекта сборки
        build = Build.objects.create(
            user=user,
            name=f"Сборка от {user.username}" if user else "Анонимная сборка",
            total_price=total_price
        )

        # Добавление компонентов
        for category_slug, product_id in components.items():
            # Пропускаем пустые компоненты
            if not product_id:
                continue

            # Получаем продукт
            product = Product.objects.get(id=product_id)

            # Определяем поле в модели Build
            field_name = CATEGORY_FIELD_MAP.get(category_slug)

            if field_name:
                setattr(build, field_name, product)

        # Проверка совместимости перед сохранением
        compatibility_errors = build.check_compatibility()
        if compatibility_errors:
            build.delete()
            return JsonResponse({
                'success': False,
                'message': 'Несовместимые компоненты',
                'errors': compatibility_errors
            }, status=400)

        build.save()

        return JsonResponse({
            'success': True,
            'build_id': build.id,
            'redirect_url': f'/build/{build.id}/'
        })

    except Product.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Продукт не найден'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)
