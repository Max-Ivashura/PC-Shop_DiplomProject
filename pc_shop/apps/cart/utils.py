from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import transaction
from django.utils import timezone
from apps.cart.models import Cart, CartItem
from apps.products.models import Product


class CartHandler:
    def __init__(self, request):
        self.request = request
        self.session = request.session
        self._cart = None
        self._initialize_cart()

    @property
    def cart(self):
        """Основное свойство для доступа к текущей корзине"""
        if not self._cart or not self._cart.is_active:
            self._initialize_cart()
        return self._cart

    def _initialize_cart(self):
        """Инициализация/получение корзины с блокировкой"""
        with transaction.atomic():
            user = self.request.user if self.request.user.is_authenticated else None
            session_key = self.session.session_key or self.session.create()

            # Для авторизованных пользователей
            if user:
                self._cart = Cart.objects.select_for_update().filter(
                    user=user,
                    converted_order__isnull=True
                ).first()

                # Слияние корзин при необходимости
                session_cart = Cart.objects.filter(
                    session_key=session_key,
                    converted_order__isnull=True
                ).first()

                if session_cart and session_cart != self._cart:
                    self._merge_carts(session_cart)

                if not self._cart:
                    self._cart = Cart.objects.create(user=user)

            # Для гостей
            else:
                self._cart = Cart.objects.select_for_update().filter(
                    session_key=session_key,
                    converted_order__isnull=True
                ).first()

                if not self._cart:
                    self._cart = Cart.objects.create(session_key=session_key)

            self._update_session(session_key)

    def _merge_carts(self, source_cart):
        """Атомарное слияние корзин"""
        try:
            with transaction.atomic():
                for item in source_cart.items.select_related('product').select_for_update():
                    try:
                        self._cart.add_product(item.product, item.quantity)
                    except ValidationError:
                        continue
                source_cart.delete()
        except Exception as e:
            # Логирование ошибки слияния
            pass

    def _update_session(self, session_key):
        """Обновление данных сессии"""
        if not self.request.user.is_authenticated:
            self._cart.session_key = session_key
            self._cart.save(update_fields=['session_key'])

        self.session['cart_id'] = str(self._cart.id)
        self.session.modified = True

    def add_product(self, product_id, quantity=1):
        """Добавление товара с резервированием"""
        try:
            with transaction.atomic():
                product = Product.objects.select_for_update().get(
                    pk=product_id,
                    is_available=True
                )

                if not self.cart.is_active:
                    raise ValidationError("Корзина завершена. Создайте новую")

                self.cart.add_product(product, quantity)
                return {
                    'success': True,
                    'new_quantity': self.get_product_quantity(product),
                    'reserved': product.quantity
                }

        except (Product.DoesNotExist, ValidationError) as e:
            return {'error': str(e)}

    def remove_product(self, product_id):
        """Удаление товара с возвратом резерва"""
        try:
            with transaction.atomic():
                product = Product.objects.select_for_update().get(pk=product_id)
                item = self.cart.items.select_for_update().get(product=product)

                product.quantity += item.quantity
                product.save(update_fields=['quantity'])

                item.delete()
                return {'success': True}

        except (CartItem.DoesNotExist, Product.DoesNotExist):
            return {'error': 'Товар не найден в корзине'}

    def update_quantity(self, product_id, new_quantity):
        """Обновление количества с коррекцией резерва"""
        try:
            with transaction.atomic():
                product = Product.objects.select_for_update().get(
                    pk=product_id,
                    is_available=True
                )

                item = self.cart.items.select_for_update().get(product=product)
                delta = new_quantity - item.quantity

                if product.quantity < delta:
                    raise ValidationError(
                        f"Доступно только {product.quantity + item.quantity} шт."
                    )

                product.quantity -= delta
                product.save(update_fields=['quantity'])

                item.quantity = new_quantity
                item.save()

                return {
                    'success': True,
                    'new_quantity': new_quantity,
                    'reserved': product.quantity
                }

        except (CartItem.DoesNotExist, ValidationError) as e:
            return {'error': str(e)}

    def get_product_quantity(self, product):
        """Получение количества конкретного товара"""
        try:
            return self.cart.items.get(product=product).quantity
        except CartItem.DoesNotExist:
            return 0

    def get_total_data(self):
        """Полные данные корзины"""
        return {
            'total_items': self.cart.items.count(),
            'total_price': self.cart.get_total_price(),
            'is_active': self.cart.is_active,
            'items': [
                {
                    'product_id': item.product.id,
                    'quantity': item.quantity,
                    'price': item.product.price,
                    'available': item.product.quantity + item.quantity
                } for item in self.cart.items.select_related('product')
            ]
        }

    def validate_cart(self):
        """Проверка доступности всех товаров"""
        problems = []
        with transaction.atomic():
            items = self.cart.items.select_related('product').select_for_update()
            for item in items:
                if item.quantity > (item.product.quantity + item.quantity):
                    problems.append({
                        'product_id': item.product.id,
                        'requested': item.quantity,
                        'available': item.product.quantity
                    })
            return problems

    def clear_inactive(self):
        """Очистка неактивных корзин"""
        if not self.cart.is_active:
            self.cart.release_stock()
            self._cart = None
            self._initialize_cart()
