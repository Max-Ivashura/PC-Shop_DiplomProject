from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.urls import reverse
from django.utils.html import format_html
from apps.configurator.models import ComponentType, CompatibilityRule, BuildComponent, Build


@admin.register(ComponentType)
class ComponentTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'required', 'order', 'attributes_list')
    list_editable = ('order', 'required')
    list_filter = ('required',)
    search_fields = ('name', 'slug')
    filter_horizontal = ('compatibility_attributes',)

    def attributes_list(self, obj):
        return ", ".join([attr.name for attr in obj.compatibility_attributes.all()])

    attributes_list.short_description = _("Критические атрибуты")


@admin.register(CompatibilityRule)
class CompatibilityRuleAdmin(admin.ModelAdmin):
    list_display = ('source_type', 'source_attribute', 'target_type', 'target_attribute', 'rule_type')
    list_filter = ('rule_type', 'source_type', 'target_type')
    search_fields = (
        'source_type__name',
        'target_type__name',
        'source_attribute__name',
        'target_attribute__name'
    )
    raw_id_fields = ('source_type', 'target_type', 'source_attribute', 'target_attribute')


class BuildComponentInline(admin.TabularInline):
    model = BuildComponent
    extra = 0
    fields = ('component_type', 'product_link', 'product_attributes')
    readonly_fields = ('product_link', 'product_attributes')

    def product_link(self, obj):
        url = reverse('admin:products_product_change', args=[obj.product.id])
        return format_html('<a href="{}">{}</a>', url, obj.product.name)

    product_link.short_description = _("Товар")

    def product_attributes(self, obj):
        attrs = obj.product.attributes.filter(
            attribute__in=obj.component_type.compatibility_attributes.all()
        )
        return ", ".join([f"{a.attribute.name}: {a.value}" for a in attrs])

    product_attributes.short_description = _("Характеристики")


@admin.register(Build)
class BuildAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'user',
        'created_at',
        'updated_at',
        'total_price',
        'compatibility_status',
        'components_count'
    )
    list_filter = ('user', 'created_at')
    search_fields = ('name', 'user__username', 'components__product__name')
    inlines = (BuildComponentInline,)
    readonly_fields = ('compatibility_status', 'total_price', 'created_at', 'updated_at')
    actions = ('check_compatibility_action',)

    def components_count(self, obj):
        return obj.components.count()

    components_count.short_description = _("Компонентов")

    def compatibility_status(self, obj):
        result = obj.check_compatibility()
        if result['is_valid']:
            return format_html('<span style="color: green;">{}</span>', _("Совместимо"))
        return format_html(
            '<span style="color: red;">{} ({})</span>',
            _("Ошибки"),
            len(result['errors'])
        )

    compatibility_status.short_description = _("Совместимость")

    def check_compatibility_action(self, request, queryset):
        for build in queryset:
            result = build.check_compatibility()
            if not result['is_valid']:
                self.message_user(
                    request,
                    _("Сборка {}: {} ошибок").format(build.name, len(result['errors'])),
                    level='ERROR'
                )
            else:
                self.message_user(
                    request,
                    _("Сборка {} совместима").format(build.name),
                    level='SUCCESS'
                )

    check_compatibility_action.short_description = _("Проверить совместимость выбранных сборок")


@admin.register(BuildComponent)
class BuildComponentAdmin(admin.ModelAdmin):
    list_display = ('build', 'component_type', 'product_link', 'attributes_summary')
    list_filter = ('component_type', 'build__user')
    search_fields = ('build__name', 'product__name')
    raw_id_fields = ('build', 'product')

    def product_link(self, obj):
        url = reverse('admin:products_product_change', args=[obj.product.id])
        return format_html('<a href="{}">{}</a>', url, obj.product.name)

    product_link.short_description = _("Товар")

    def attributes_summary(self, obj):
        attrs = obj.product.attributes.filter(
            attribute__in=obj.component_type.compatibility_attributes.all()
        )
        return ", ".join([f"{a.attribute.name}: {a.value}" for a in attrs])

    attributes_summary.short_description = _("Критические атрибуты")
