from django.core.exceptions import ObjectDoesNotExist
from django.db.models import F
from .models import Cart, CartItem

class CartHandler:
    def __init__(self, request):
        """
        Инициализация корзины.
        """
        self.session = request.session
        cart_id = self.session.get('cart_id')
        user = request.user if request.user.is_authenticated else None

        # Для авторизованных пользователей
        if user:
            cart, created = Cart.objects.get_or_create(user=user)
            if cart_id and cart_id != str(cart.id):
                # Объединяем корзины при логине
                try:
                    old_cart = Cart.objects.filter(id=cart_id).first()
                    if old_cart:
                        old_cart.items.update(cart=cart)  # Переносим товары
                        old_cart.delete()  # Удаляем старую корзину
                except Exception as e:
                    # Логирование ошибки
                    print(f"Ошибка при объединении корзин: {e}")
            self.cart = cart
        else:
            # Для гостей
            session_key = self.session.session_key
            cart = Cart.objects.filter(session_key=session_key).first()
            if not cart:
                cart = Cart.objects.create(session_key=session_key)
            self.cart = cart

        # Сохраняем ID корзины в сессии
        self.session['cart_id'] = str(self.cart.id)
        self.session.modified = True

    def add(self, product, quantity=1):
        """
        Добавление товара в корзину.
        """
        if not product.is_available or product.quantity <= 0:
            raise ValueError("Товар недоступен или закончился")

        item = self.cart.items.filter(product=product).first()
        if item:
            # Проверка, чтобы общее количество не превышало доступное
            if item.quantity + quantity > product.quantity:
                raise ValueError("Недостаточно товара на складе")
            item.quantity += quantity
            item.save()
        else:
            self.cart.items.create(product=product, quantity=quantity)

    def remove(self, product):
        """
        Удаление товара из корзины.
        """
        self.cart.items.filter(product=product).delete()

    def clear(self):
        """
        Очистка корзины.
        """
        self.cart.items.all().delete()

    def get_cart_items(self):
        """
        Получение всех товаров в корзине с оптимизацией запросов.
        """
        return self.cart.items.select_related('product').all()

    def get_total_price(self):
        """
        Получение общей стоимости корзины.
        """
        return self.cart.get_total_price()

    def update_quantity(self, product, quantity):
        """
        Обновление количества товара в корзине.
        """
        if quantity < 1:
            raise ValueError("Количество не может быть меньше 1")

        item = self.cart.items.filter(product=product).first()
        if not item:
            raise ValueError("Товар не найден в корзине")

        if quantity > product.quantity:
            raise ValueError("Недостаточно товара на складе")

        item.quantity = quantity
        item.save()