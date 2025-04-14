document.addEventListener('DOMContentLoaded', () => {
    const COMPARE = {
        init() {
            this.cacheElements();
            this.bindEvents();
            this.initLazyLoad();
        },

        cacheElements() {
            this.$table = document.querySelector('.compare-table');
            this.$controls = document.querySelector('.compare-controls');
            this.$container = document.querySelector('.compare-container');
        },

        bindEvents() {
            // Делегирование событий
            this.$container.addEventListener('click', e => {
                if (e.target.closest('.remove-btn')) this.handleRemoveProduct(e);
                if (e.target.closest('.btn-toggle')) this.toggleGroup(e);
                if (e.target.closest('.btn-highlight')) this.highlightDifferences(e);
                if (e.target.closest('.filter-checkbox')) this.filterAttributes(e);
            });

            // Сортировка
            document.querySelector('.sort-up')?.addEventListener('click', () => this.sortAttributes('asc'));
            document.querySelector('.sort-down')?.addEventListener('click', () => this.sortAttributes('desc'));
        },

        initLazyLoad() {
            const lazyImages = document.querySelectorAll('.product-image[loading="lazy"]');
            const observer = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        const img = entry.target;
                        img.src = img.dataset.src;
                        observer.unobserve(img);
                    }
                });
            });

            lazyImages.forEach(img => observer.observe(img));
        },

        async handleRemoveProduct(e) {
            const $btn = e.target.closest('.remove-btn');
            const productId = $btn.dataset.productId;

            if (!confirm('Удалить товар из сравнения?')) return;

            try {
                const response = await fetch(`/compare/api/remove/${productId}/`, {
                    method: 'DELETE',
                    headers: {
                        'X-Requested-With': 'XMLHttpRequest',
                        'X-CSRFToken': this.getCSRFToken()
                    }
                });

                const data = await response.json();

                if (data.success) {
                    if (data.is_empty) {
                        window.location.href = data.redirect;
                    } else {
                        this.updateUIAfterRemoval(productId);
                    }
                } else {
                    this.showError(data.message);
                }
            } catch (error) {
                this.showError('Ошибка соединения');
            }
        },

        updateUIAfterRemoval(productId) {
            // Удаляем колонку товара
            document.querySelectorAll(`[data-product-id="${productId}"]`).forEach(el => el.remove());

            // Обновляем счетчик
            const $badge = document.querySelector('.notification-badge');
            const count = parseInt($badge.textContent.split('/')[0]) - 1;
            $badge.textContent = `${count}/${this.MAX_PRODUCTS}`;

            // Анимация
            this.animateRemoval($badge);
        },

        toggleGroup(e) {
            const $btn = e.target.closest('.btn-toggle');
            const $groups = document.querySelectorAll('.group-row');
            const isCollapsed = $btn.classList.toggle('collapsed');

            $groups.forEach(group => {
                group.nextElementSibling.style.display = isCollapsed ? 'none' : '';
            });

            $btn.textContent = isCollapsed ? 'Развернуть все группы' : 'Свернуть все группы';
        },

        highlightDifferences() {
            const $rows = document.querySelectorAll('.attr-row');
            $rows.forEach(row => {
                const values = [...row.querySelectorAll('.attr-value')]
                    .map(td => td.textContent.trim());

                const isDifferent = new Set(values).size > 1;
                row.classList.toggle('highlight', isDifferent);
            });
        },

        filterAttributes(e) {
            const $checkbox = e.target.closest('.filter-checkbox');
            const filterType = $checkbox.dataset.type;
            const isChecked = $checkbox.checked;

            document.querySelectorAll('.attr-row').forEach(row => {
                const match = filterType === 'critical' ?
                    row.dataset.isCritical === 'true' :
                    row.dataset.attributeType === 'number';

                row.style.display = (isChecked && match) ? '' : 'none';
            });
        },

        sortAttributes(order) {
            const $tbody = this.$table.querySelector('tbody');
            const rows = Array.from($tbody.querySelectorAll('.attr-row'));

            rows.sort((a, b) => {
                const aVal = a.querySelector('.attr-value').textContent;
                const bVal = b.querySelector('.attr-value').textContent;
                return order === 'asc' ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
            });

            $tbody.append(...rows);
        },

        getCSRFToken() {
            return document.querySelector('[name=csrfmiddlewaretoken]').value;
        },

        animateRemoval(element) {
            element.animate([
                {transform: 'scale(1)', opacity: 1},
                {transform: 'scale(1.2)', opacity: 0.5},
                {transform: 'scale(1)', opacity: 1}
            ], 500);
        },

        showError(message) {
            const $error = document.createElement('div');
            $error.className = 'error-message';
            $error.textContent = message;

            this.$container.prepend($error);
            setTimeout(() => $error.remove(), 3000);
        }
    };

    COMPARE.init();
});