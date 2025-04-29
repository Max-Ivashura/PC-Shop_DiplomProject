function toggleFields(select) {
    const regexField = document.querySelector('[name="validation_regex"]').closest('.form-row');

    if (select.value === 'string') {
        regexField.style.display = 'block';
    } else {
        regexField.style.display = 'none';
    }
}