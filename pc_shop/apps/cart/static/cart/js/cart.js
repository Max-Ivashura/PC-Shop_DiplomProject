// cart.js - Логика работы с корзиной
document.addEventListener('DOMContentLoaded', () => {
    const cartContainer = document.querySelector('.cart-container');

    // Обновление количества
    cartContainer.addEventListener('click', async (e) => {
        if (e.target.closest('.update-btn')) {
            const row = e.target.closest('tr');
            const productId = row.dataset.productId;
            const input = row.querySelector('.quantity-input');
            const newQuantity = parseInt(input.value);

            if (isNaN(newQuantity)) {
                Utils.showNotification('Некорректное количество', 'danger');
                input.value = input.dataset.oldValue;
                return;
            }

            try {
                const response = await fetch(`/cart/update/${productId}/`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': Utils.getCookie('csrftoken')
                    },
                    body: JSON.stringify({quantity: newQuantity})
                });

                const data = await response.json();

                if (data.success) {
                    updateCartUI(data);
                    Utils.showNotification('Корзина обновлена');
                    Utils.animateIcon('.navbar .fa-shopping-cart', 'pulse');
                } else {
                    input.value = data.old_quantity;
                    Utils.showNotification(data.error, 'danger');
                }
            } catch (error) {
                Utils.showNotification('Ошибка соединения', 'danger');
            }
        }
    });

    // Удаление товара
    cartContainer.addEventListener('click', async (e) => {
        if (e.target.closest('.remove-btn')) {
            const productId = e.target.dataset.productId;
            const productName = e.target.dataset.productName;

            if (!confirm(`Удалить "${productName}" из корзины?`)) return;

            try {
                const response = await fetch(`/cart/remove/${productId}/`, {
                    method: 'POST',
                    headers: {'X-CSRFToken': Utils.getCookie('csrftoken')}
                });

                const data = await response.json();

                if (data.success) {
                    updateCartUI(data);
                    Utils.showNotification('Товар удалён');
                    Utils.animateIcon('.navbar .fa-shopping-cart', 'shake');
                } else {
                    Utils.showNotification(data.error, 'danger');
                }
            } catch (error) {
                Utils.showNotification('Ошибка соединения', 'danger');
            }
        }
    });

    // Обновление интерфейса
    function updateCartUI(data) {
        // Обновление списка товаров
        if (data.cart_html) {
            document.getElementById('cart-items').innerHTML = data.cart_html;
        }

        // Обновление общей суммы
        if (data.cart_total) {
            document.getElementById('total-price').textContent =
                `${data.cart_total} ₽`;
        }

        // Обновление счетчика
        const counter = document.getElementById('cart-counter');
        if (counter && data.total_items !== undefined) {
            counter.textContent = data.total_items;
        }

        // Блокировка кнопки оформления
        const checkoutBtn = document.querySelector('.checkout-btn');
        if (checkoutBtn) {
            checkoutBtn.classList.toggle('disabled', !data.is_active);
        }
    }
});