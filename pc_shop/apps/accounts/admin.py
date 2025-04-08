from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from .models import UserProfile, Wishlist, WishlistItem

# --- Инлайн для профиля пользователя ---
class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Профиль'
    readonly_fields = ('is_adult',)  # Метод из модели

    # Добавляем метод is_adult в поля инлайна
    def get_fields(self, request, obj=None):
        fields = super().get_fields(request, obj)
        return fields + ('is_adult',)

# --- Кастомизация админки User ---
class CustomUserAdmin(UserAdmin):
    inlines = (UserProfileInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'profile_info')
    list_select_related = ('userprofile',)  # Оптимизация запросов

    # Кастомное поле для отображения информации из профиля
    def profile_info(self, obj):
        return f"Телефон: {obj.userprofile.phone}, Адрес: {obj.userprofile.address}"
    profile_info.short_description = "Профиль"

# --- Админка для Wishlist ---
@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    list_display = ('user', 'created_at', 'updated_at', 'total_products')
    list_filter = ('created_at',)

    def total_products(self, obj):
        return obj.wishlistitem_set.count()

    total_products.short_description = "Количество товаров"

# --- Админка для WishlistItem ---
@admin.register(WishlistItem)
class WishlistItemAdmin(admin.ModelAdmin):
    list_display = ('wishlist', 'product', 'added_at')
    list_filter = ('added_at',)
    search_fields = ('wishlist__user__username', 'product__name')

# --- Регистрация моделей ---
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)