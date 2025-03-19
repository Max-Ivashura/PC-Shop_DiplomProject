// static/js/catalog.js
document.addEventListener('DOMContentLoaded', function () {
    // AJAX-добавление в корзину
    document.querySelectorAll('.add-to-cart').forEach(button => {
        button.addEventListener('click', function (e) {
            e.preventDefault();
            const productId = this.dataset.productId;
            fetch(`/cart/add/${productId}/`, {
                method: 'POST',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
                },
                body: JSON.stringify({quantity: 1})
            })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        // Анимация добавления в корзину
                        const cartIcon = document.querySelector('.navbar .fa-shopping-cart');
                        const clone = cartIcon.cloneNode(true);
                        clone.style.position = 'absolute';
                        clone.style.left = `${cartIcon.offsetLeft}px`;
                        clone.style.top = `${cartIcon.offsetTop}px`;
                        document.body.appendChild(clone);

                        clone.animate([
                            {transform: 'translateY(0)'},
                            {transform: 'translateY(-100px) scale(0.5)'}
                        ], {
                            duration: 500,
                            easing: 'ease-out'
                        });

                        setTimeout(() => clone.remove(), 500);
                    }
                });
        });
    });
});