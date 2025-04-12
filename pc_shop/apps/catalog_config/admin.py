from django.contrib import admin
from django.db.models import Count, Prefetch
from django.http import HttpResponse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from mptt.admin import DraggableMPTTAdmin
import csv

from .forms import AttributeGroupForm, AttributeForm
from .models import (
    Category,
    AttributeGroup,
    Attribute,
    EnumOption,
    ProductAttributeValue,
    AttributeGroupLink
)


class AttributeGroupLinkInline(admin.TabularInline):
    model = AttributeGroupLink
    extra = 1
    verbose_name = _("Связь с группой")
    verbose_name_plural = _("Связи с группами")
    autocomplete_fields = ['group']


@admin.register(Category)
class CategoryAdmin(DraggableMPTTAdmin):
    list_display = (
        'tree_actions',
        'indented_title',
        'slug',
        'attributes_count',
        'product_count'
    )
    list_display_links = ('indented_title',)
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name', 'path')
    mptt_level_indent = 25
    actions = ['export_category_attributes']

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            _attributes_count=Count('attribute_groups__attributes', distinct=True),
            _product_count=Count('products', distinct=True)
        ).prefetch_related(
            Prefetch(
                'attribute_groups__attributes',
                queryset=Attribute.objects.select_related('parent')
            )
        )

    def attributes_count(self, obj):
        return obj._attributes_count

    attributes_count.short_description = _('Атрибутов')

    def product_count(self, obj):
        return obj._product_count

    product_count.short_description = _('Товаров')

    def export_category_attributes(self, request, queryset):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="attributes_export.csv"'

        writer = csv.writer(response)
        writer.writerow([
            _('Категория'),
            _('Группа'),
            _('Атрибут'),
            _('Тип данных'),
            _('Обязательный')
        ])

        for category in queryset.prefetch_related(
                'attribute_groups__attributes'
        ):
            for group in category.attribute_groups.all():
                for attr in group.attributes.all():
                    writer.writerow([
                        category.path,
                        group.name,
                        attr.name,
                        attr.get_data_type_display(),
                        _('Да') if attr.is_required else _('Нет')
                    ])
        return response

    export_category_attributes.short_description = _("Экспорт атрибутов категории")


@admin.register(AttributeGroup)
class AttributeGroupAdmin(DraggableMPTTAdmin):
    list_display = (
        'tree_actions',
        'indented_title',
        'category_hierarchy',
        'attributes_count'
    )
    list_filter = ('category',)
    search_fields = ('name', 'category__name')
    mptt_level_indent = 20
    form = AttributeGroupForm

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            _attributes_count=Count('attributes', distinct=True)
        ).select_related('category')

    def attributes_count(self, obj):
        return obj._attributes_count

    attributes_count.short_description = _('Атрибутов')

    def indented_title(self, instance):
        return format_html(
            '<div style="text-indent:{}px">{}</div>',
            instance._mpttfield('level') * self.mptt_level_indent,
            instance.name
        )

    def category_hierarchy(self, obj):
        return format_html(
            '<ul style="margin:0; padding-left:20px">' +
            ''.join(f"<li>{cat.name}</li>" for cat in obj.category.get_ancestors(include_self=True)) +
            '</ul>'
        )

    category_hierarchy.short_description = _('Иерархия категорий')


class EnumOptionInline(admin.StackedInline):
    model = EnumOption
    extra = 3
    max_num = 20
    verbose_name = _("Вариант значения")
    verbose_name_plural = _("Варианты значений")

    def get_max_num(self, request, obj=None, **kwargs):
        return 3 if obj is None else 20


@admin.register(Attribute)
class AttributeAdmin(DraggableMPTTAdmin):
    form = AttributeForm
    list_display = (
        'tree_actions',
        'indented_title',
        'get_data_type_display',
        'unit',
        'is_required',
        'compatibility_status',
        'groups_list'
    )
    list_filter = ('data_type', 'is_required', 'compatibility_critical')
    search_fields = ('name', 'groups__group__name')
    inlines = [AttributeGroupLinkInline, EnumOptionInline]
    actions = ['check_attributes_consistency']
    fieldsets = (
        (None, {
            'fields': (
                'name',
                'parent',
                'data_type',
                'unit',
                'is_required',
                'compatibility_critical'
            )
        }),
        (_('Валидация'), {
            'fields': ('validation_regex',),
            'classes': ('collapse',)
        }),
    )
    mptt_level_indent = 20

    class Media:
        js = ('admin/js/attribute_form.js',)

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related(
            Prefetch(
                'groups__group__category',
                queryset=Category.objects.only('name')
            )
        )

    @admin.display(description=_('Тип данных'))
    def get_data_type_display(self, obj):
        return obj.get_data_type_display()

    def compatibility_status(self, obj):
        color = 'red' if obj.compatibility_critical else 'green'
        text = _('Критично') if obj.compatibility_critical else _('Некритично')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            text
        )

    compatibility_status.short_description = _('Статус совместимости')

    def groups_list(self, obj):
        return format_html(
            '<ul style="margin:0">' +
            ''.join(
                f"<li>{g.group.category.name} → {g.group.name}</li>"
                for g in obj.attributegrouplink_set.select_related('group__category')
            ) +
            '</ul>'
        )

    groups_list.short_description = _('Группы')

    def check_attributes_consistency(self, request, queryset):
        inconsistent = []
        for attr in queryset:
            if attr.data_type == 'enum' and not attr.enum_options.exists():
                inconsistent.append(attr.name)

        if inconsistent:
            self.message_user(
                request,
                _("Найдены некорректные атрибуты: ") + ", ".join(inconsistent),
                level='ERROR'
            )
        else:
            self.message_user(request, _("Все атрибуты корректны"))

    check_attributes_consistency.short_description = _("Проверить целостность")
