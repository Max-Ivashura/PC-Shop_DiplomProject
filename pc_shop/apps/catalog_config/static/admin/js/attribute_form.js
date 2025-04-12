function toggleFields(select) {
    const regexField = document.querySelector('[name="validation_regex"]').closest('.form-row');
    const unitField = document.querySelector('[name="unit"]').closest('.form-row');

    if (select.value === 'string') {
        regexField.style.display = 'block';
        unitField.style.display = 'none';
    } else if (select.value === 'enum') {
        regexField.style.display = 'none';
        unitField.style.display = 'block';
    } else {
        regexField.style.display = 'none';
        unitField.style.display = 'none';
    }
}