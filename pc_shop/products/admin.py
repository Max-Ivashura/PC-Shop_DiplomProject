from django.contrib import admin
from .models import Category, Product, AttributeGroup, Attribute, ProductAttribute

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'parent')
    prepopulated_fields = {'slug': ('name',)}

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'price')
    prepopulated_fields = {'slug': ('name',)}

admin.site.register(AttributeGroup)
admin.site.register(Attribute)
admin.site.register(ProductAttribute)