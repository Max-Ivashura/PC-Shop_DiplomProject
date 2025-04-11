class Configurator {
  constructor(options) {
    this.categories = options.categories;
    this.componentTypes = options.componentTypes;
    this.compatibilityCheckUrl = options.compatibilityCheckUrl;
    this.saveBuildUrl = options.saveBuildUrl;
    this.componentListUrl = options.componentListUrl.replace('CATEGORY_SLUG', '');

    this.selectedComponents = {};
    this.compatibilityErrors = [];
    this.totalPrice = 0;

    this.initEventListeners();
    this.updateBuildVisualization();
  }

  initEventListeners() {
    document.getElementById('componentCategory').addEventListener('change', (e) => {
      this.loadComponents(e.target.value);
    });

    document.getElementById('componentList').addEventListener('click', (e) => {
      if (e.target.classList.contains('select-component')) {
        const componentData = JSON.parse(e.target.dataset.component);
        this.selectComponent(componentData);
      }
    });

    document.getElementById('checkCompatibilityBtn').addEventListener('click', () => {
      this.checkCompatibility();
    });

    document.getElementById('saveBuildBtn').addEventListener('click', () => {
      this.saveBuild();
    });
  }

  async loadComponents(categorySlug) {
    try {
      const response = await fetch(this.componentListUrl + categorySlug + '/');
      const components = await response.json();

      const list = document.getElementById('componentList');
      list.innerHTML = components.map(component => `
        <div class="card mb-2 component-item">
          <div class="card-body d-flex justify-content-between">
            <div>
              <h6>${component.name}</h6>
              <small>${component.specs}</small>
            </div>
            <div class="d-flex flex-column align-items-end">
              <span class="price">${component.price} ₽</span>
              <button class="btn btn-sm btn-primary select-component"
                      data-component='${JSON.stringify(component)}'>
                Выбрать
              </button>
            </div>
          </div>
        </div>
      `).join('');
    } catch (error) {
      console.error('Ошибка загрузки компонентов:', error);
    }
  }

  selectComponent(component) {
    const componentType = this.componentTypes.find(
      ct => ct.model.toLowerCase() === component.category.toLowerCase()
    );

    if (!componentType) {
      alert('Неизвестный тип компонента');
      return;
    }

    this.selectedComponents[componentType.id] = {
      component_type_id: componentType.id,
      product_id: component.id,
      options: {}
    };

    this.updateBuildVisualization();
    this.updateTotalPrice();
    this.checkCompatibility();
  }

  updateBuildVisualization() {
    const slots = document.querySelectorAll('.component-slot');
    slots.forEach(slot => {
      const type = slot.dataset.componentType;
      const componentType = this.componentTypes.find(ct => ct.model.toLowerCase() === type);

      if (componentType && this.selectedComponents[componentType.id]) {
        const component = this.selectedComponents[componentType.id];
        slot.querySelector('.component-name').textContent = component.name;
        slot.querySelector('.component-icon').src = component.image;
      }
    });
  }

  async checkCompatibility() {
    try {
      const response = await fetch(this.compatibilityCheckUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': this.getCookie('csrftoken')
        },
        body: JSON.stringify({
          components: Object.values(this.selectedComponents)
        })
      });

      const result = await response.json();
      this.compatibilityErrors = result.errors || [];
      this.updateCompatibilityStatus();
    } catch (error) {
      console.error('Ошибка проверки совместимости:', error);
    }
  }

  updateCompatibilityStatus() {
    const alert = document.getElementById('compatibilityAlert');
    const message = document.getElementById('compatibilityMessage');
    const progressBar = document.getElementById('compatibilityProgress');

    if (this.compatibilityErrors.length > 0) {
      message.innerHTML = this.compatibilityErrors.join('<br>');
      alert.classList.remove('d-none');
      progressBar.className = 'progress-bar bg-danger';
      progressBar.style.width = '33%';
      progressBar.textContent = 'Проблемы совместимости';
    } else {
      alert.classList.add('d-none');
      progressBar.className = 'progress-bar bg-success';
      progressBar.style.width = '100%';
      progressBar.textContent = 'Полная совместимость';
    }
  }

  updateTotalPrice() {
    this.totalPrice = Object.values(this.selectedComponents).reduce(
      (sum, component) => sum + component.price, 0
    );
    document.getElementById('totalPrice').textContent = `${this.totalPrice} ₽`;
  }

  async saveBuild() {
    try {
      const response = await fetch(this.saveBuildUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': this.getCookie('csrftoken')
        },
        body: JSON.stringify({
          name: prompt('Введите название сборки') || 'Новая сборка',
          components: Object.values(this.selectedComponents)
        })
      });

      const result = await response.json();
      if (result.success) {
        window.location.href = `/build/${result.build_id}/`;
      } else {
        alert(`Ошибка: ${result.error}`);
      }
    } catch (error) {
      console.error('Ошибка сохранения:', error);
    }
  }

  getCookie(name) {
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
}

// Инициализация при загрузке
document.addEventListener('DOMContentLoaded', () => {
  const configurator = new Configurator({
    categories: JSON.parse(document.getElementById('componentCategory').dataset.categories),
    componentTypes: JSON.parse(document.getElementById('componentCategory').dataset.componentTypes),
    compatibilityCheckUrl: '/api/check-compatibility/',
    saveBuildUrl: '/api/save-build/',
    componentListUrl: '/api/components/'
  });
});