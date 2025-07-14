document.addEventListener('DOMContentLoaded', function () {
    const typeSelect = document.getElementById('id_product_type_selector');
    const productSelect = document.getElementById('id_product');

    if (!typeSelect || !productSelect) return;

    function filterProducts() {
        const selectedType = typeSelect.value;

        Array.from(productSelect.options).forEach(option => {
            if (!option.value) return; // skip blank
            const label = option.textContent.toLowerCase();
            const isVariation = label.includes('[variation]');
            const isCombination = label.includes('[combination]');

            const shouldShow =
                selectedType === '' ||
                (selectedType === 'variation' && isVariation) ||
                (selectedType === 'combination' && isCombination);

            option.style.display = shouldShow ? '' : 'none';
        });
    }

    typeSelect.addEventListener('change', filterProducts);
    filterProducts(); // Run once on page load
});