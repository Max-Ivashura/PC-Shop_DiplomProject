// Общие функции
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// Уведомления с анимацией
function showNotification(message, type = 'success') {
    const notification = document.createElement('div');
    notification.className = `notification alert alert-${type}`;
    notification.textContent = message;
    notification.style.position = 'fixed';
    notification.style.top = '20px';
    notification.style.right = '20px';
    notification.style.zIndex = '1000';
    document.body.appendChild(notification);

    setTimeout(() => {
        notification.remove();
    }, 3000);
}

// Добавление в корзину
function addToCart(productId, quantity = 1) {
    fetch(`/cart/add/${productId}/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify({quantity})
    })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showNotification('Товар добавлен в корзину');
                updateCartCounter(data.cart_count);

                // Анимация иконки корзины
                const cartIcon = document.querySelector('.navbar .fa-shopping-cart');
                if (cartIcon) {
                    cartIcon.style.transform = 'scale(1.2)';
                    setTimeout(() => cartIcon.style.transform = 'scale(1)', 200);
                }
            } else {
                showNotification('Ошибка: ' + data.message, 'danger');
            }
        });
}

// Обновление счетчика корзины
function updateCartCounter(count) {
    const badge = document.querySelector('.navbar .badge');
    if (badge) badge.textContent = count;
}

// Добавление в список желаний
function addToWishlist(productId) {
    fetch(`/wishlist/add/${productId}/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCookie('csrftoken')
        }
    })
        .then(response => response.json())
        .then(data => {
            showNotification(data.message, data.success ? 'success' : 'danger');
        });
}

// Добавление в сравнение
function addToCompare(productId) {
    fetch(`/compare/add/${productId}/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCookie('csrftoken')
        }
    })
        .then(response => response.json())
        .then(data => {
            showNotification(data.message, data.success ? 'success' : 'danger');
        });
}

// Обработчики событий
document.addEventListener('DOMContentLoaded', () => {
    // Добавление в корзину (для всех кнопок с классом .add-to-cart)
    document.body.addEventListener('click', (e) => {
        if (e.target.closest('.add-to-cart')) {
            e.preventDefault();
            const productId = e.target.closest('.add-to-cart').dataset.productId;
            addToCart(productId);
        }
    });

    // Добавление в список желаний
    document.body.addEventListener('click', (e) => {
        if (e.target.closest('.add-to-wishlist')) {
            e.preventDefault();
            const productId = e.target.closest('.add-to-wishlist').dataset.productId;
            addToWishlist(productId);
        }
    });

    // Добавление в сравнение
    document.body.addEventListener('click', (e) => {
        if (e.target.closest('.add-to-compare')) {
            e.preventDefault();
            const productId = e.target.closest('.add-to-compare').dataset.productId;
            addToCompare(productId);
        }
    });

    // Обновление количества товара
    document.body.addEventListener('click', (e) => {
        if (e.target.closest('.update-cart-btn')) {
            e.preventDefault();

            const input = e.target.closest('td').querySelector('.quantity-input');
            const productId = input.dataset.productId;
            const currentQuantity = parseInt(input.value, 10);

            // Валидация
            if (isNaN(currentQuantity) || currentQuantity < 1) {
                input.value = 1;
                showNotification('Количество должно быть ≥1', 'danger');
                return;
            }

            fetch(`/cart/update/${productId}/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: JSON.stringify({quantity: currentQuantity})
            })
                .then(response => {
                    if (!response.ok) {
                        return response.json().then(err => {
                            throw new Error(err.message || 'Ошибка сервера');
                        });
                    }
                    return response.json();
                })
                .then(data => {
                    if (data.success) {
                        showNotification('Корзина обновлена');
                        updateCartCounter(data.cart_count);
                        updateCartTable(data.cart_html);
                    } else {
                        // Восстанавливаем старое значение
                        input.value = data.old_quantity || 1;
                        showNotification(data.message, 'danger');
                    }
                })
                .catch(error => {
                    console.error('Ошибка:', error);
                    showNotification(`Ошибка: ${error.message}`, 'danger');
                    input.value = 1; // Сброс при критической ошибке
                });
        }
    });
});

// Обновление таблицы корзины
function updateCartTable(html) {
    const tableContainer = document.querySelector('.table-responsive');
    if (tableContainer) {
        tableContainer.innerHTML = html;
    }
}