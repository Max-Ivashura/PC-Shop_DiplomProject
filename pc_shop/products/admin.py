from django.contrib import admin
from django.http import JsonResponse, request
from django.urls import path

from .forms import ProductAttributeForm
from .models import Category, Product, AttributeGroup, Attribute, ProductAttribute, ProductImage
from mptt.admin import MPTTModelAdmin, DraggableMPTTAdmin
from django.utils.html import format_html
from mptt.forms import TreeNodeChoiceField
from django import forms
from django.db import models


@admin.register(Category)
class CategoryAdmin(DraggableMPTTAdmin):
    list_display = (
        'tree_actions',
        'indented_title_modified',
        'slug',
        'parent'
    )
    list_display_links = ('indented_title_modified',)
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name',)

    def indented_title_modified(self, instance):
        return format_html(
            '<div style="text-indent:{}px">{}</div>',
            instance.mptt_level * 30,  # Увеличиваем отступ для наглядности
            instance.name
        )

    indented_title_modified.short_description = 'Категория'

    def get_queryset(self, request):
        return super().get_queryset(request).order_by('tree_id', 'lft')


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    readonly_fields = ('preview_thumbnail',)
    fields = ('image', 'preview_thumbnail', 'is_main')

    def preview_thumbnail(self, obj):
        return obj.preview_thumbnail()

    preview_thumbnail.short_description = "Превью"


class ProductAttributeInline(admin.TabularInline):
    form = ProductAttributeForm
    model = ProductAttribute
    extra = 0
    fields = ('attribute', 'data_type_display', 'value', 'unit_display',)
    readonly_fields = ('attribute', 'data_type_display', 'unit_display')

    class Media:
        css = {
            'all': ('admin/custom.css',)
        }
        js = ('admin/product_attributes.js',)

    def data_type_display(self, obj):
        return obj.attribute.get_data_type_display()

    data_type_display.short_description = 'Тип данных'

    def unit_display(self, obj):
        return obj.attribute.unit or '—'

    unit_display.short_description = 'Ед. измерения'

    def get_queryset(self, request):
        # Оптимизируем запросы
        return super().get_queryset(request).select_related('attribute__group')

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        # Фильтруем характеристики по категории товара
        if db_field.name == "attribute" and hasattr(request, '_obj_'):
            kwargs["queryset"] = Attribute.objects.filter(
                group__category=request._obj_.category
            )
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def get_inline_instances(self, request, obj=None):
        # Группировка характеристик
        instances = super().get_inline_instances(request, obj)
        if obj and obj.category:
            setattr(self, 'grouped_attributes', self.get_grouped_attributes(obj))
        return instances


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        'main_image_preview',
        'name',
        'category',
        'price',
        'quantity_status',
        'is_available',
        'created_at'
    )
    list_filter = ('category', 'is_available', 'created_at')
    search_fields = ('name', 'description', 'category__name')
    readonly_fields = ('main_image_preview', 'created_at', 'updated_at')
    fieldsets = (
        ('Основная информация', {
            'fields': ('main_image_preview', 'category', 'name', 'price',)
        }),
        ('Инвентаризация', {
            'fields': ('quantity', 'is_available')
        }),
        ('Контент', {
            'fields': ('description',)
        }),
        ('Метаданные', {
            'fields': ('slug', 'created_at', 'updated_at')
        }),
    )
    prepopulated_fields = {'slug': ('name',)}
    inlines = [ProductImageInline, ProductAttributeInline]

    def main_image_preview(self, obj):
        main_image = obj.main_image
        if main_image:
            return format_html(
                '<img src="{}" style="max-height: 80px; max-width: 80px;" />',
                main_image.image.url
            )
        return "-"

    main_image_preview.short_description = "Главное изображение"

    def quantity_status(self, obj):
        if obj.quantity == 0:
            return format_html('<span style="color: red;">Нет в наличии</span>')
        elif obj.quantity < 10:
            return format_html(f'<span style="color: orange;">{obj.quantity} шт.</span>')
        return format_html(f'<span style="color: green;">{obj.quantity} шт.</span>')

    quantity_status.short_description = "Остаток"

    def get_form(self, request, obj=None, **kwargs):
        # Передаем объект товара в inline-формы
        request._obj_ = obj
        return super().get_form(request, obj, **kwargs)

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        product = form.instance
        # Создаем атрибуты только после сохранения продукта и выбора категории
        if product.category:
            attributes = Attribute.objects.filter(group__category=product.category)
            for attr in attributes:
                ProductAttribute.objects.get_or_create(
                    product=product,
                    attribute=attr,
                    defaults={'value': ''}
                )


class AttributeGroupForm(forms.ModelForm):
    category = TreeNodeChoiceField(
        queryset=Category.objects.all(),
        level_indicator="---",
        label="Категория"
    )


@admin.register(AttributeGroup)
class AttributeGroupAdmin(admin.ModelAdmin):
    change_list_template = 'admin/products/attributegroup/change_list.html'
    form = AttributeGroupForm
    list_display = ('name', 'indented_category', 'category')
    list_filter = ('category',)
    search_fields = ('category__name', 'name')

    def changelist_view(self, request, extra_context=None):
        # Используем annotate для подсчета групп
        categories = Category.objects.annotate(
            num_groups=models.Count('attribute_groups')
        ).prefetch_related('attribute_groups').order_by('tree_id', 'lft')

        grouped_data = []
        for category in categories:
            # Проверяем, есть ли группы через аннотацию
            if category.num_groups > 0:
                grouped_data.append({
                    'id': category.id,
                    'name': category.name,
                    'attribute_groups': category.attribute_groups.all()
                })

        extra_context = extra_context or {}
        extra_context['categories'] = grouped_data

        return super().changelist_view(request, extra_context=extra_context)

    def indented_category(self, obj):
        return self.format_hierarchy(obj.category)

    indented_category.short_description = 'Иерархия категории'

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        # Для поля category используем кастомный виджет с иерархией
        if db_field.name == "category":
            kwargs["queryset"] = Category.objects.all().order_by('tree_id', 'lft')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    @staticmethod
    def format_hierarchy(category):
        if not category:
            return ""
        ancestors = category.get_ancestors(include_self=True)
        return " → ".join([c.name for c in ancestors])


from django.contrib import admin
from .models import Attribute


@admin.register(Attribute)
class AttributeAdmin(admin.ModelAdmin):
    list_display = ('name', 'group', 'category', 'data_type', 'unit_display')
    list_filter = ('group__category', 'data_type')
    change_list_template = 'admin/products/attribute/change_list.html'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('group__category')

    def category(self, obj):
        return obj.group.category.name

    category.short_description = "Категория"

    def unit_display(self, obj):
        return obj.unit if obj.unit else '—'

    unit_display.short_description = 'Единица измерения'

    def changelist_view(self, request, extra_context=None):
        from .models import Category
        categories = Category.objects.prefetch_related(
            'attribute_groups__attributes'
        ).order_by('tree_id', 'lft')

        grouped_data = []
        for category in categories:
            groups = []
            for group in category.attribute_groups.all():
                attributes = group.attributes.all()
                if attributes:
                    groups.append({
                        'id': group.id,
                        'name': group.name,
                        'attributes': attributes
                    })
            if groups:
                grouped_data.append({
                    'id': category.id,
                    'name': category.name,
                    'groups': groups
                })

        extra_context = extra_context or {}
        extra_context['categories'] = grouped_data

        return super().changelist_view(request, extra_context=extra_context)

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('<path:object_id>/json/',
                 self.admin_site.admin_view(self.attribute_json),
                 name='products_attribute_json')
        ]
        return custom_urls + urls

    def attribute_json(self, request, object_id):
        attribute = Attribute.objects.get(id=object_id)
        return JsonResponse({
            'data_type': attribute.data_type,
            'unit': attribute.unit
        })


admin.site.register(ProductAttribute)
