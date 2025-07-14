document.addEventListener('DOMContentLoaded', function () {
    // Only run inside Django popup
    if (!window.location.search.includes('_popup=1')) return;

    const unwantedFields = [
        'id_product_type',
        'id_product',
        'id_price',
        'id_stock',
        'id_is_active'
    ];

    unwantedFields.forEach(id => {
        const field = document.getElementById(id);
        if (field) {
            const container = field.closest('.form-row, .form-group, .field-box');
            if (container) {
                container.style.display = 'none';
            }
        }
    });
});



