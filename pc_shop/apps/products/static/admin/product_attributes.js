document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('.dynamic-productattribute').forEach(row => {
        const attributeSelect = row.querySelector('select[name$="-attribute"]');
        const valueField = row.querySelector('.value-field');

        if (attributeSelect) {
            // Первоначальная настройка
            updateValueWidget(attributeSelect);

            // Обработчик изменения атрибута
            attributeSelect.addEventListener('change', function() {
                updateValueWidget(this);
            });
        }
    });

    function updateValueWidget(selectElement) {
        const row = selectElement.closest('.dynamic-productattribute');
        const valueContainer = row.querySelector('.value-field');
        const attributeId = selectElement.value;

        if (!attributeId) {
            valueContainer.innerHTML = '<input type="text" class="form-control">';
            return;
        }

        fetch(`/admin/products/attribute/${attributeId}/json/`)
            .then(response => response.json())
            .then(data => {
                let newField;
                switch(data.data_type) {
                    case 'bool':
                        newField = document.createElement('select');
                        newField.className = 'form-control';
                        newField.innerHTML = `
                            <option value="true">Да</option>
                            <option value="false">Нет</option>
                        `;
                        break;
                    case 'int':
                        newField = document.createElement('input');
                        newField.type = 'number';
                        newField.step = '1';
                        newField.className = 'form-control';
                        break;
                    case 'float':
                        newField = document.createElement('input');
                        newField.type = 'number';
                        newField.step = '0.01';
                        newField.className = 'form-control';
                        break;
                    default:
                        newField = document.createElement('input');
                        newField.type = 'text';
                        newField.className = 'form-control';
                }
                valueContainer.innerHTML = '';
                valueContainer.appendChild(newField);
            });
    }
});