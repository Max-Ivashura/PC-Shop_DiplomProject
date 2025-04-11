import json
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.csrf import csrf_exempt
from django.contrib.contenttypes.models import ContentType
from apps.catalog_config.models import Category
from apps.configurator.models import Build, BuildComponent, CompatibilityRule
from apps.products.models import Product


@csrf_exempt
@login_required
def save_build_api(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Only POST method allowed'}, status=405)

    try:
        data = json.loads(request.body)
        components = data.get('components', [])
        name = data.get('name', 'Unnamed Build')

        # Валидация данных
        if not components:
            raise ValidationError("Components list is required")

        with transaction.atomic():
            build = Build.objects.create(
                user=request.user,
                name=name,
                description=data.get('description', '')
            )

            for component in components:
                content_type = ContentType.objects.get(id=component['component_type_id'])
                product = content_type.get_object_for_this_type(id=component['product_id'])

                BuildComponent.objects.create(
                    build=build,
                    component_type=content_type,
                    object_id=product.id,
                    selected_options=component.get('options', {})
                )

            # Проверка совместимости
            compatibility_errors = build.check_compatibility()

            return JsonResponse({
                'success': True,
                'build_id': build.id,
                'compatibility_errors': compatibility_errors
            })

    except ContentType.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Invalid component type'}, status=400)
    except Product.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Product not found'}, status=404)
    except ValidationError as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'Server error: {str(e)}'}, status=500)


@login_required
def configurator(request):
    categories = Category.objects.filter(
        name__in=['Процессоры', 'Видеокарты', 'Материнские платы',
                  'Оперативная память', 'Блоки питания', 'Накопители',
                  'Системы охлаждения']
    ).prefetch_related('products')

    component_types = ContentType.objects.filter(
        app_label='products',
        model__in=[cat.name.lower().replace(' ', '') for cat in categories]
    )

    return render(request, 'configurator/configurator.html', {
        'categories': categories,
        'component_types': component_types
    })


@login_required
def save_build(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            build = Build.objects.create(
                user=request.user,
                name=data.get('name', 'Новая сборка'),
                description=data.get('description', '')
            )

            for component in data.get('components', []):
                content_type = ContentType.objects.get(id=component['component_type_id'])
                BuildComponent.objects.create(
                    build=build,
                    component_type=content_type,
                    object_id=component['product_id'],
                    selected_options=component.get('options', {})
                )

            errors = build.check_compatibility()
            return JsonResponse({
                'success': True,
                'build_id': build.id,
                'errors': errors
            })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)
    return JsonResponse({'success': False}, status=405)


@csrf_exempt
def check_compatibility_api(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            components = {}
            for item in data.get('components', []):
                content_type = ContentType.objects.get(id=item['component_type_id'])
                components[content_type] = Product.objects.get(id=item['product_id'])

            # Здесь должна быть логика проверки совместимости
            # Возвращаем заглушку
            return JsonResponse({'errors': []})
        except Exception as e:
            return JsonResponse({'errors': [str(e)]}, status=400)


@login_required
def build_detail(request, build_id):
    build = get_object_or_404(Build, id=build_id)
    return render(request, 'configurator/build_detail.html', {
        'build': build,
        'compatibility_errors': build.check_compatibility()
    })


@login_required
def delete_build(request, build_id):
    build = get_object_or_404(Build, id=build_id, user=request.user)
    build.delete()
    return redirect('community_builds')


def community_builds(request):
    builds = Build.objects.filter(is_public=True).select_related('user').prefetch_related('components')
    return render(request, 'configurator/community_builds.html', {'builds': builds})


@csrf_exempt
def get_components_api(request, category_slug):
    if request.method == 'GET':
        category = get_object_or_404(Category, slug=category_slug)
        products = category.products.values('id', 'name', 'price', 'image')
        return JsonResponse(list(products), safe=False)
    return JsonResponse({'error': 'Method not allowed'}, status=405)
