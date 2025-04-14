class ConfiguratorApp {
    constructor(config) {
        this.api = config.api;
        this.componentTypes = config.componentTypes;
        this.selectedComponents = new Map();
        this.currentType = null;

        this.initDOMReferences();
        this.initEventListeners();
        this.loadInitialData();
    }

    initDOMReferences() {
        this.dom = {
            componentSlots: document.getElementById('componentSlots'),
            componentList: document.getElementById('componentList'),
            componentSearch: document.getElementById('componentSearch'),
            totalPrice: document.querySelector('.total-price'),
            compatibilityScore: document.getElementById('compatibilityScore'),
            saveModal: new bootstrap.Modal('#saveModal')
        };
    }

    initEventListeners() {
        // Выбор типа компонента
        document.getElementById('componentTypeSelect').addEventListener('change', e => {
            this.currentType = this.componentTypes.find(t => t.id == e.target.value);
            this.loadComponents();
        });

        // Поиск компонентов
        this.dom.componentSearch.addEventListener('input', () => this.loadComponents());

        // Выбор компонента
        this.dom.componentList.addEventListener('click', e => {
            if (e.target.closest('.component-item')) {
                const productId = e.target.dataset.productId;
                this.selectComponent(productId);
            }
        });

        // Сохранение сборки
        document.getElementById('confirmSave').addEventListener('click', () => this.saveBuild());
    }

    async loadInitialData() {
        // Загрузка первого типа компонентов
        this.currentType = this.componentTypes[0];
        document.getElementById('componentTypeSelect').value = this.currentType.id;
        await this.loadComponents();
    }

    async loadComponents() {
        try {
            const url = this.api.components
                    .replace('0', this.currentType.id)
                + `?search=${encodeURIComponent(this.dom.componentSearch.value)}`;

            const response = await fetch(url);
            const components = await response.json();

            this.renderComponentList(components);
        } catch (error) {
            console.error('Ошибка загрузки компонентов:', error);
        }
    }

    renderComponentList(components) {
        this.dom.componentList.innerHTML = components.map(component => `
      <div class="component-item card mb-2">
        <div class="card-body">
          <div class="d-flex justify-content-between align-items-start">
            <div>
              <h6 class="mb-1">${component.name}</h6>
              ${component.attributes.map(attr => `
                <div class="text-muted small">
                  <span>${attr.name}:</span>
                  <strong>${attr.value} ${attr.unit || ''}</strong>
                </div>
              `).join('')}
            </div>
            <button class="btn btn-sm btn-primary" 
                    data-product-id="${component.id}">
              Выбрать
            </button>
          </div>
        </div>
      </div>
    `).join('');
    }

    async selectComponent(productId) {
        try {
            const response = await fetch(`/api/products/${productId}/`);
            const product = await response.json();

            this.selectedComponents.set(this.currentType.id, {
                type: this.currentType,
                product: product
            });

            this.updateUI();
            this.checkCompatibility();
        } catch (error) {
            console.error('Ошибка выбора компонента:', error);
        }
    }

    updateUI() {
        // Обновление слотов
        this.dom.componentSlots.innerHTML = this.componentTypes.map(type => {
            const component = this.selectedComponents.get(type.id);
            return `
        <div class="component-slot ${type.required ? 'required' : ''}" 
             data-type-id="${type.id}">
          <div class="slot-header">
            <i class="fas fa-${type.icon} me-2"></i>
            ${type.name}
            ${type.required ? '<span class="required-badge">Обязательно</span>' : ''}
          </div>
          <div class="slot-body">
            ${component ? `
              <div class="selected-component">
                <div class="name">${component.product.name}</div>
                <div class="price">${component.product.price.toLocaleString()} ₽</div>
              </div>
            ` : '<div class="empty-slot">Не выбрано</div>'}
          </div>
        </div>
      `;
        }).join('');

        // Общая стоимость
        const total = Array.from(this.selectedComponents.values())
            .reduce((sum, c) => sum + c.product.price, 0);

        this.dom.totalPrice.textContent = `${total.toLocaleString()} ₽`;
    }

    async checkCompatibility() {
        try {
            const components = Array.from(this.selectedComponents.values())
                .map(c => ({type_id: c.type.id, product_id: c.product.id}));

            const response = await fetch(this.api.check, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({components})
            });

            const result = await response.json();
            this.updateCompatibilityUI(result);
        } catch (error) {
            console.error('Ошибка проверки совместимости:', error);
        }
    }

    updateCompatibilityUI(result) {
        const score = result.is_valid ? 100 : Math.max(100 - result.errors.length * 20, 0);
        this.dom.compatibilityScore.textContent = `Совместимость: ${score}%`;

        // Подсветка проблемных слотов
        document.querySelectorAll('.component-slot').forEach(slot => {
            const typeId = parseInt(slot.dataset.typeId);
            const hasError = result.errors.some(e => e.component_type === typeId);
            slot.classList.toggle('has-error', hasError);
        });
    }

    async saveBuild() {
        try {
            const formData = {
                name: document.getElementById('saveForm').elements.name.value,
                description: document.getElementById('saveForm').elements.description.value,
                is_public: document.getElementById('saveForm').elements.is_public.checked,
                components: Array.from(this.selectedComponents.values()).map(c => ({
                    component_type: c.type.id,
                    product: c.product.id
                }))
            };

            const response = await fetch(this.api.save, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify(formData)
            });

            const result = await response.json();

            if (result.success) {
                window.location.href = `/configurator/build/${result.build_id}/`;
            } else {
                alert(`Ошибка: ${result.error}`);
            }
        } catch (error) {
            console.error('Ошибка сохранения:', error);
        }
    }

    getCSRFToken() {
        return document.querySelector('[name=csrfmiddlewaretoken]').value;
    }
}