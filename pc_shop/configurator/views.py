import json

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Build, CompatibilityRule
from products.models import Product, Category
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from products.models import Product, Category


@login_required
def delete_build(request, build_id):
    build = get_object_or_404(Build, id=build_id, user=request.user)
    build.delete()
    return redirect('user_builds')


@login_required
def configurator(request):
    categories = Category.objects.filter(
        name__in=['Процессоры', 'Видеокарты', 'Материнские платы', 'Оперативная память', 'Блоки питания', 'Накопители',
                  'Системы охлаждения'])
    components = {category.name: category.products.all() for category in categories}

    if request.method == 'POST':
        # Логика сохранения сборки
        pass

    return render(request, 'configurator/configurator.html', {'components': components})


@login_required
def save_build(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        cpu_id = request.POST.get('cpu')
        motherboard_id = request.POST.get('motherboard')
        # ... другие компоненты

        build = Build.objects.create(
            user=request.user,
            name=name,
            cpu_id=cpu_id,
            motherboard_id=motherboard_id,
            # ... остальные поля
        )
        compatibility_errors = build.check_compatibility()
        if compatibility_errors:
            # Обработка ошибок
            pass
        return redirect('build_detail', build.id)
    return redirect('configurator')


def community_builds(request):
    builds = Build.objects.filter(is_public=True).exclude(user=request.user)
    return render(request, 'configurator/community_builds.html', {'builds': builds})


def build_detail(request, build_id):
    build = get_object_or_404(Build, id=build_id)
    return render(request, 'configurator/build_detail.html', {'build': build})


@csrf_exempt
def get_components(request, category_slug):
    category = get_object_or_404(Category, slug=category_slug)
    products = category.products.values('id', 'name', 'price', 'image')
    return JsonResponse(list(products), safe=False)


@csrf_exempt
def check_compatibility(request):
    if request.method == 'POST':
        selected = json.loads(request.body)
        errors = []

        # Пример проверки сокета CPU и материнской платы
        cpu = Product.objects.get(id=selected.get('processors'))
        motherboard = Product.objects.get(id=selected.get('motherboards'))

        cpu_socket = cpu.attributes.get(attribute__name='Сокет').value
        mb_socket = motherboard.attributes.get(attribute__name='Сокет').value

        if cpu_socket != mb_socket:
            errors.append('Сокет процессора не совместим с материнской платой')

        return JsonResponse({'errors': errors})
