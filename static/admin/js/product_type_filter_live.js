document.addEventListener('DOMContentLoaded', function () {
    const typeSelect = document.getElementById('id_product_type');
    const productSelect = document.getElementById('id_product');
    const priceRow = document.querySelector('.form-row.field-price');

    if (!typeSelect || !productSelect) return;

    // Store all original product options
    const allOptions = Array.from(productSelect.options);

    function filterProductsAndTogglePrice() {
        const selectedType = typeSelect.value;

        // Filter the product dropdown
        productSelect.innerHTML = '';

        const filtered = allOptions.filter(option => {
            if (!option.value) return true; // Keep placeholder
            const label = option.textContent.toLowerCase();
            return selectedType === '' ||
                   (selectedType === 'variation' && label.includes('[variation]')) ||
                   (selectedType === 'combination' && label.includes('[combination]'));
        });

        filtered.forEach(option => productSelect.appendChild(option.cloneNode(true)));

        // Automatically hide price field if 'combination' is selected
        if (priceRow) {
            priceRow.style.display = selectedType === 'combination' ? 'none' : 'block';
        }
    }

    // React when product_type changes
    typeSelect.addEventListener('change', filterProductsAndTogglePrice);

    // Also listen when a product is selected — optional fallback
    productSelect.addEventListener('change', () => {
        const selectedOption = productSelect.options[productSelect.selectedIndex];
        const label = selectedOption?.textContent?.toLowerCase();
        const isCombination = label && label.includes('[combination]');
        if (priceRow) priceRow.style.display = isCombination ? 'none' : 'block';
    });

    filterProductsAndTogglePrice(); // Initial run
});