// Изменение основного изображения
function changeMainImage(url) {
    document.getElementById('mainImage').src = url;
}

// Добавление в корзину
function addToCart(productId) {
    fetch(`/cart/add/${productId}/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify({quantity: 1})
    })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert('Товар добавлен в корзину');
                // Обновить счетчик корзины
                document.querySelector('.navbar .badge').textContent = data.cart_count;
            }
        });
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
            if (data.success) {
                alert('Товар добавлен в список желаний');
            }
        });
}

// Получение CSRF-токена
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
        if (data.success) {
            alert('Товар добавлен в сравнение');
            // Обновить счетчик сравнения (если есть)
        } else {
            alert('Ошибка: ' + data.message);
        }
    });
}