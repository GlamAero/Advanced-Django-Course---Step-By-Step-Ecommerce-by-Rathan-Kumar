// THIS STATIC FILE DID NOT COME WITH THE TEMPLATE USED FOR THIS PROJECT

// used to toggle between single product, product variation and product variation combination at creation of product in product table of admin page
document.addEventListener('DOMContentLoaded', function () {
    const productTypeSelect = document.querySelector('#id_product_type');
    const priceFieldRow = document.querySelector('.form-row.field-price');

    function togglePriceField() {
        if (!productTypeSelect || !priceFieldRow) return;
        const selected = productTypeSelect.value;
        priceFieldRow.style.display = selected === 'simple' ? 'block' : 'none';
    }

    if (productTypeSelect) {
        togglePriceField(); // Initialize on page load
        productTypeSelect.addEventListener('change', togglePriceField); // React to changes
    }
});