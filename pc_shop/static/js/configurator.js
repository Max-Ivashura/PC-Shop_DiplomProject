document.addEventListener('DOMContentLoaded', function() {
    const componentCategory = document.getElementById('componentCategory');
    const componentList = document.getElementById('componentList');
    const totalPrice = document.getElementById('totalPrice');
    const compatibilityAlert = document.getElementById('compatibilityAlert');
    const compatibilityMessage = document.getElementById('compatibilityMessage');
    const compatibilityProgress = document.getElementById('compatibilityProgress');
    const saveBuildBtn = document.getElementById('saveBuildBtn');

    let selectedComponents = {};
    let componentPrices = {};

    // Инициализация тултипов
    const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');
    const tooltipList = [...tooltipTriggerList].map(tooltipTriggerEl => new bootstrap.Tooltip(tooltipTriggerEl));

    // Обработчик выбора категории
    componentCategory.addEventListener('change', function() {
        loadComponents(this.value);
    });

    // Обработчик выбора компонента
    componentList.addEventListener('click', function(e) {
        if (e.target.classList.contains('component-item')) {
            const type = e.target.dataset.componentType;
            const componentId = e.target.dataset.componentId;
            const componentName = e.target.dataset.componentName;
            const componentPrice = parseFloat(e.target.dataset.componentPrice);
            const componentImage = e.target.dataset.componentImage;

            // Обновляем слот
            const slot = document.querySelector(`[data-component="${type}"]`);
            slot.querySelector('.component-name').innerText = componentName;
            slot.querySelector('.component-icon').src = componentImage;
            slot.querySelector('.component-icon').setAttribute('data-bs-original-title', componentName);

            // Обновляем данные
            selectedComponents[type] = componentId;
            componentPrices[type] = componentPrice;

            // Обновляем интерфейс
            updateTotalPrice();
            checkCompatibility();
        }
    });

    // Обработчик кнопки проверки совместимости
    document.getElementById('checkCompatibilityBtn').addEventListener('click', checkCompatibility);

    // Обработчик сохранения сборки
    saveBuildBtn.addEventListener('click', saveBuild);

    // Загрузка компонентов
    function loadComponents(categorySlug) {
        fetch(`/api/components/${categorySlug}/`)
            .then(response => response.json())
            .then(data => {
                componentList.innerHTML = data.map(component => `
                    <div class="component-item p-3 rounded mb-2 cursor-pointer shadow-sm" 
                         data-component-type="${component.category_slug}"
                         data-component-id="${component.id}"
                         data-component-name="${component.name}"
                         data-component-price="${component.price}"
                         data-component-image="${component.image}">
                        <div class="d-flex justify-content-between">
                            <div>
                                <h6>${component.name}</h6>
                                <small class="text-muted">${component.attributes.socket || ''}</small>
                            </div>
                            <div class="text-end">
                                <span class="badge bg-primary">${component.price} ₽</span>
                            </div>
                        </div>
                    </div>
                `).join('');
            });
    }

    // Проверка совместимости
    function checkCompatibility() {
        if (Object.keys(selectedComponents).length === 0) {
            showAlert('Выберите хотя бы один компонент', 'warning');
            return;
        }

        fetch('/api/check-compatibility/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify(selectedComponents)
        })
        .then(response => response.json())
        .then(data => {
            if (data.errors.length > 0) {
                showAlert(data.errors.join('; '), 'danger');
                compatibilityProgress.style.width = '0%';
                compatibilityProgress.innerText = 'Совместимость: 0%';
            } else {
                showAlert('Все компоненты совместимы!', 'success');
                compatibilityProgress.style.width = '100%';
                compatibilityProgress.innerText = 'Совместимость: 100%';
            }
        });
    }

    // Обновление общей стоимости
    function updateTotalPrice() {
        const total = Object.values(componentPrices).reduce((sum, price) => sum + price, 0);
        totalPrice.innerText = total.toLocaleString() + ' ₽';
    }

    // Сохранение сборки
    function saveBuild() {
        if (Object.keys(selectedComponents).length === 0) {
            showAlert('Сначала выберите компоненты', 'warning');
            return;
        }

        fetch('/api/save-build/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({
                components: selectedComponents,
                total_price: componentPrices
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showAlert('Сборка сохранена!', 'success');
                setTimeout(() => window.location.href = '/community-builds/', 1500);
            } else {
                showAlert('Ошибка сохранения: ' + data.message, 'danger');
            }
        });
    }

    // Вспомогательная функция для показа уведомлений
    function showAlert(message, type = 'info') {
        compatibilityAlert.classList.remove('d-none');
        compatibilityMessage.innerText = message;
        compatibilityAlert.classList.add(`alert-${type}`);

        setTimeout(() => {
            compatibilityAlert.classList.add('d-none');
        }, 5000);
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
});