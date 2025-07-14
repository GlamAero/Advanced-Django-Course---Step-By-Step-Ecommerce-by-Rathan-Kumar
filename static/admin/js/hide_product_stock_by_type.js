document.addEventListener('DOMContentLoaded', function () {
    const typeSelect = document.getElementById('id_product_type');
    const stockRow = document.querySelector('.form-row.field-stock');

    if (!typeSelect || !stockRow) return;

    function toggleStockVisibility() {
        const selected = typeSelect.value;
        const shouldHide = selected === 'variation' || selected === 'combination';

        stockRow.style.display = shouldHide ? 'none' : 'block';
    }

    typeSelect.addEventListener('change', toggleStockVisibility);
    toggleStockVisibility(); // Run on load
});

