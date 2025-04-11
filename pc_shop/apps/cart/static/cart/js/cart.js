document.addEventListener('DOMContentLoaded', function () {
    // Обновление количества товара
    document.querySelectorAll('.update-quantity').forEach(button => {
        button.addEventListener('click', function () {
            const productId = this.dataset.productId;
            const quantity = this.closest('tr').querySelector('.quantity-input').value;

            fetch(`/cart/update/${productId}/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: JSON.stringify({ quantity: quantity })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    document.getElementById('cart-items').innerHTML = data.cart_html;
                    document.getElementById('total-price').innerText = `${data.total_price} руб.`;
                } else {
                    alert(data.message);
                }
            });
        });
    });

    // Удаление товара
    document.querySelectorAll('.remove-item').forEach(button => {
        button.addEventListener('click', function () {
            const productId = this.dataset.productId;
            const modal = new bootstrap.Modal(document.getElementById('confirmRemoveModal'));
            const confirmButton = document.getElementById('confirm-remove');

            confirmButton.onclick = function () {
                fetch(`/cart/remove/${productId}/`, {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': getCookie('csrftoken')
                    }
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        location.reload(); // Перезагружаем страницу после удаления
                    } else {
                        alert(data.message);
                    }
                });
                modal.hide();
            };

            modal.show();
        });
    });
});

// Функция для получения CSRF-токена
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