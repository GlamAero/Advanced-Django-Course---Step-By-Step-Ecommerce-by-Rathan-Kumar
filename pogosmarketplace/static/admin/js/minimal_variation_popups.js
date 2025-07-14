document.addEventListener('DOMContentLoaded', function () {
    // Only run in Django pop-up windows
    if (!window.location.search.includes('_popup=1')) return;

    const hideFields = [
        'id_product_type',
        'id_product',
        'id_price',
        'id_stock',
        'id_is_active'
    ];

    hideFields.forEach(id => {
        const field = document.getElementById(id);
        if (field) {
            const wrapper = field.closest('.form-row, .form-group, .field-box');
            if (wrapper) wrapper.style.display = 'none';
        }
    });
});