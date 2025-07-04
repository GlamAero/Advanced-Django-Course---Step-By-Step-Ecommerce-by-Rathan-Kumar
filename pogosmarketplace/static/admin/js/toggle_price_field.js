document.addEventListener('DOMContentLoaded', function () {
    const productSelect = document.getElementById('id_product');
    const priceRow = document.querySelector('.form-row.field-price');

    if (!productSelect || !priceRow) return;

    const togglePriceVisibility = () => {
        const selectedOption = productSelect.options[productSelect.selectedIndex];
        const label = selectedOption?.textContent?.toLowerCase() || '';
        const isCombination = label.includes('[combination]');

        priceRow.style.display = isCombination ? 'none' : 'block';
    };

    togglePriceVisibility(); // Run once on load
    productSelect.addEventListener('change', togglePriceVisibility); // React to user input
});