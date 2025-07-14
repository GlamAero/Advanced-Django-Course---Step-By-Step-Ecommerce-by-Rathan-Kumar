document.addEventListener('DOMContentLoaded', function () {
    const typeSelect = document.getElementById('id_product_type');
    const productSelect = document.getElementById('id_product');
    const priceRow = document.querySelector('.form-row.field-price');
    const stockRow = document.querySelector('.form-row.field-stock');

    if (!typeSelect || !productSelect) return;

    const allOptions = Array.from(productSelect.options).map(option => option.cloneNode(true));

    function filterProducts() {
        const selectedType = typeSelect.value;
        productSelect.innerHTML = '';

        allOptions.forEach(option => {
            const type = option.getAttribute('data-product-type');
            const include =
                !option.value || selectedType === '' || type === selectedType;

            if (include) {
                productSelect.appendChild(option.cloneNode(true));
            }
        });

        toggleFieldVisibility();
    }

    function toggleFieldVisibility() {
        const selectedOption = productSelect.options[productSelect.selectedIndex];
        const type = selectedOption?.getAttribute('data-product-type') || typeSelect.value;

        const isCombination = type === 'combination';

        if (priceRow) priceRow.style.display = isCombination ? 'none' : 'block';
        if (stockRow) stockRow.style.display = isCombination ? 'none' : 'block';
    }

    typeSelect.addEventListener('change', filterProducts);
    productSelect.addEventListener('change', toggleFieldVisibility);

    filterProducts(); // Run once on load
});