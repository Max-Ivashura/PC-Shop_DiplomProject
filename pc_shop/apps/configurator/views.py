import json
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from django.core.exceptions import ValidationError
from django.contrib.contenttypes.models import ContentType
from apps.catalog_config.models import Category
from apps.products.models import Product
from .models import Build, BuildComponent, ComponentType, CompatibilityRule


@login_required
@require_http_methods(["GET"])
def configurator(request):
    """Главная страница конфигуратора"""
    component_types = ComponentType.objects.all().order_by('order')
    return render(request, 'configurator/configurator.html', {
        'component_types': component_types
    })


@csrf_exempt
@login_required
@require_http_methods(["POST"])
def save_build_api(request):
    """API для сохранения сборки"""
    try:
        data = json.loads(request.body)
        with transaction.atomic():
            build = Build.objects.create(
                user=request.user,
                name=data.get('name', 'Новая сборка'),
                description=data.get('description', '')
            )

            for component_data in data.get('components', []):
                component_type = get_object_or_404(
                    ComponentType,
                    id=component_data['type_id']
                )
                product = get_object_or_404(
                    Product,
                    id=component_data['product_id']
                )

                BuildComponent.objects.create(
                    build=build,
                    component_type=component_type,
                    product=product
                )

            compatibility_result = build.check_compatibility()

            if not compatibility_result['is_valid']:
                build.delete()
                return JsonResponse({
                    'status': 'error',
                    'errors': compatibility_result['errors']
                }, status=400)

            return JsonResponse({
                'status': 'success',
                'build_id': build.id,
                'total_price': str(build.total_price)
            })

    except ValidationError as e:
        return JsonResponse({'status': 'error', 'errors': e.messages}, status=400)
    except Exception as e:
        return JsonResponse({'status': 'error', 'errors': [str(e)]}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def check_compatibility_api(request):
    """API для проверки совместимости компонентов"""
    try:
        data = json.loads(request.body)
        components = {}

        for item in data.get('components', []):
            component_type = get_object_or_404(
                ComponentType,
                id=item['type_id']
            )
            product = get_object_or_404(
                Product,
                id=item['product_id']
            )
            components[component_type] = product

        # Временная сборка для проверки
        temp_build = Build(user=request.user if request.user.is_authenticated else None)
        compatibility_result = temp_build.check_compatibility(components)

        return JsonResponse({
            'valid': compatibility_result['is_valid'],
            'errors': compatibility_result.get('errors', []),
            'warnings': compatibility_result.get('warnings', [])
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
def get_components_api(request, type_id):
    """Получение товаров для конкретного типа компонента"""
    try:
        component_type = get_object_or_404(ComponentType, id=type_id)
        products = Product.objects.filter(
            category=component_type.linked_category
        ).prefetch_related('attributes').values(
            'id',
            'name',
            'price',
            'image',
            'attributes__attribute__name',
            'attributes__value'
        )

        return JsonResponse(list(products), safe=False)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
def build_detail(request, build_id):
    """Детализация сборки"""
    build = get_object_or_404(Build, id=build_id, user=request.user)
    return render(request, 'configurator/build_detail.html', {
        'build': build,
        'compatibility': build.check_compatibility()
    })


@login_required
def delete_build(request, build_id):
    """Удаление сборки"""
    build = get_object_or_404(Build, id=build_id, user=request.user)
    build.delete()
    return JsonResponse({'status': 'success'})


@login_required
def community_builds(request):
    """Публичные сборки сообщества"""
    builds = Build.objects.filter(is_public=True).select_related(
        'user'
    ).prefetch_related(
        'components__product'
    )
    return render(request, 'configurator/community.html', {'builds': builds})


@login_required
def toggle_build_visibility(request, build_id):
    """Переключение видимости сборки"""
    build = get_object_or_404(Build, id=build_id, user=request.user)
    build.is_public = not build.is_public
    build.save()
    return JsonResponse({'status': 'success', 'is_public': build.is_public})
