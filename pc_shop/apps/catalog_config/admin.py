from django.contrib import admin
from django.db.models import Count
from django.http import HttpResponseRedirect
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from mptt.admin import DraggableMPTTAdmin

from .forms import AttributeGroupForm, AttributeForm
from .models import Category, AttributeGroup, Attribute, EnumOption, ProductAttributeValue


@admin.register(Category)
class CategoryAdmin(DraggableMPTTAdmin):
    list_display = ('tree_actions', 'indented_title', 'slug', 'attributes_count')
    list_display_links = ('indented_title',)
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name',)
    mptt_level_indent = 25
    actions = ['export_category_attributes']

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            _attributes_count=Count('attribute_groups__attributes', distinct=True)
        )

    def attributes_count(self, obj):
        return obj._attributes_count
    attributes_count.short_description = _('Атрибутов')

    def export_category_attributes(self, request, queryset):
        # Пример кастомного действия
        from django.http import HttpResponse
        import csv
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="attributes.csv"'
        writer = csv.writer(response)
        writer.writerow(['Attribute', 'Type', 'Groups'])
        for category in queryset:
            for attr in category.attributes.all():
                writer.writerow([
                    attr.name,
                    attr.get_data_type_display(),
                    ', '.join(str(g) for g in attr.groups.all())
                ])
        return response

    export_category_attributes.short_description = _("Экспорт атрибутов категории")


@admin.register(AttributeGroup)
class AttributeGroupAdmin(DraggableMPTTAdmin):
    list_display = ('tree_actions', 'indented_title', 'category_hierarchy')
    list_filter = ('category',)
    search_fields = ('name', 'category__name')
    mptt_level_indent = 20

    verbose_name = _("Группа атрибутов")
    verbose_name_plural = _("Группы атрибутов")

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

    category_hierarchy.short_description = _('Категория')


class EnumOptionInline(admin.TabularInline):
    model = EnumOption
    extra = 3
    max_num = 20
    verbose_name = _("Вариант значения")
    verbose_name_plural = _("Варианты значений")

    def get_max_num(self, request, obj=None, **kwargs):
        # Показываем 3 пустых поля для новых атрибутов
        return 3 if obj is None else 20


@admin.register(Attribute)
class AttributeAdmin(DraggableMPTTAdmin):
    form = AttributeForm
    list_display = ('tree_actions', 'indented_title', 'data_type_display', 'unit', 'is_required', 'groups_list')
    search_fields = ('name', 'groups__name')
    filter_horizontal = ('groups',)
    save_on_top = True
    inlines = [EnumOptionInline]
    actions = ['check_attributes_consistency']
    fieldsets = (
        (None, {
            'fields': ('name', 'data_type', 'groups', 'unit', 'is_required')
        }),
        (_('Валидация'), {
            'fields': ('validation_regex',),
            'classes': ('collapse',)
        }),
    )
    mptt_level_indent = 20

    verbose_name = _("Атрибут")
    verbose_name_plural = _("Атрибуты")

    def indented_title(self, instance):
        return format_html(
            '<div style="text-indent:{}px">{}</div>',
            instance._mpttfield('level') * self.mptt_level_indent,
            instance.name
        )

    def data_type_display(self, obj):
        return obj.get_data_type_display()

    data_type_display.short_description = _('Тип данных')

    def groups_list(self, obj):
        return format_html(
            '<ul style="margin:0">' +
            ''.join(f"<li>{g.category.name} → {g.name}</li>" for g in obj.groups.all()) +
            '</ul>'
        )

    groups_list.short_description = _('Группы')

    def check_attributes_consistency(self, request, queryset):
        # Пример кастомного действия проверки
        inconsistent = []
        for attr in queryset:
            if attr.data_type == 'enum' and not attr.enum_options.exists():
                inconsistent.append(attr)
        self.message_user(request, f"Найдено {len(inconsistent)} некорректных атрибутов")
        return HttpResponseRedirect(request.get_full_path())

    check_attributes_consistency.short_description = _("Проверить целостность")


class AttributeValueFilter(admin.SimpleListFilter):
    title = _('Тип значения')
    parameter_name = 'value_type'

    def lookups(self, request, model_admin):
        return Attribute.DATA_TYPES

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(attribute__data_type=self.value())
        return queryset


class ProductAttributeValueInline(admin.StackedInline):
    model = ProductAttributeValue
    extra = 0
    fields = ('attribute', 'value_widget')
    readonly_fields = ('value_widget',)
    can_delete = False
    template = 'admin/catalog_config/productattributevalue/stacked.html'

    def value_widget(self, obj):
        attr = obj.attribute
        if attr.data_type == 'enum':
            options = attr.enum_options.values_list('value', flat=True)
            return format_html(
                '<select disabled>{}</select>',
                ''.join(f'<option>{opt}</option>' for opt in options)
            )
        elif attr.data_type == 'boolean':
            return format_html('<input type="checkbox" disabled {}>',
                               'checked' if obj.value else '')
        return obj.value

    value_widget.short_description = _('Значение')
