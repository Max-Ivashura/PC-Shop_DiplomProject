// Общие обработчики (не связанные с корзиной)
// ===========================================
const GlobalHandlers = {
    initWishlist() {
        document.body.addEventListener('click', async (e) => {
            const btn = e.target.closest('.add-to-wishlist');
            if (!btn) return;

            e.preventDefault();
            try {
                const response = await fetch(`/wishlist/add/${btn.dataset.productId}/`, {
                    method: 'POST',
                    headers: {'X-CSRFToken': Utils.getCookie('csrftoken')}
                });

                const data = await response.json();
                Utils.showNotification(data.message, data.success ? 'success' : 'danger');
            } catch (error) {
                Utils.showNotification('Ошибка соединения', 'danger');
            }
        });
    },

    initCompare() {
        document.body.addEventListener('click', async (e) => {
            const btn = e.target.closest('.add-to-compare');
            if (!btn) return;

            e.preventDefault();
            try {
                const response = await fetch(`/compare/add/${btn.dataset.productId}/`, {
                    method: 'POST',
                    headers: {'X-CSRFToken': Utils.getCookie('csrftoken')}
                });

                const data = await response.json();
                Utils.showNotification(data.message, data.success ? 'success' : 'danger');
            } catch (error) {
                Utils.showNotification('Ошибка соединения', 'danger');
            }
        });
    }
};

// Инициализация
// =============
document.addEventListener('DOMContentLoaded', () => {
    GlobalHandlers.initWishlist();
    GlobalHandlers.initCompare();
});