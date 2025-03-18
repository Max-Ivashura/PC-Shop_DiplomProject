from .models import Cart, CartItem

class CartHandler:
    def __init__(self, request):
        self.session = request.session
        cart_id = self.session.get('cart_id')
        user = request.user if request.user.is_authenticated else None

        if user:
            # Для авторизованных пользователей
            cart, created = Cart.objects.get_or_create(user=user)
            if cart_id and cart_id != str(cart.id):
                # Объединяем корзины при логине
                old_cart = Cart.objects.filter(id=cart_id).first()
                if old_cart:
                    old_cart.items.all().update(cart=cart)
                    old_cart.delete()
            self.cart = cart
        else:
            # Для гостей
            cart = Cart.objects.filter(session_key=self.session.session_key).first()
            if not cart:
                cart = Cart.objects.create(session_key=self.session.session_key)
            self.cart = cart
        self.session['cart_id'] = str(self.cart.id)
        self.session.modified = True

    def add(self, product, quantity=1):
        item = self.cart.items.filter(product=product).first()
        if item:
            item.quantity += quantity
            item.save()
        else:
            self.cart.items.create(product=product, quantity=quantity)

    def remove(self, product):
        self.cart.items.filter(product=product).delete()

    def clear(self):
        self.cart.items.all().delete()

    def get_cart_items(self):
        return self.cart.items.all()

    def get_total_price(self):
        return self.cart.get_total_price()