document.addEventListener('DOMContentLoaded', function () {
    // Toast message logic
    function showToast(message, isSuccess = true) {
        const toast = document.createElement('div');
        toast.textContent = message;
        toast.style.position = 'fixed';
        toast.style.bottom = '20px';
        toast.style.right = '20px';
        toast.style.backgroundColor = isSuccess ? '#0c7b16' : '#b91c1c';
        toast.style.color = 'white';
        toast.style.padding = '12px 16px';
        toast.style.borderRadius = '6px';
        toast.style.boxShadow = '0 2px 6px rgba(0,0,0,0.2)';
        toast.style.fontSize = '14px';
        toast.style.zIndex = 9999;
        document.body.appendChild(toast);
        setTimeout(() => toast.remove(), 4000);
    }

    // Bulk stock update logic
    const actionSelect = document.querySelector('select[name="action"]');
    if (!actionSelect) return;

    actionSelect.addEventListener('change', function () {
        if (this.value === 'bulk_update_stock') {
            this.value = '';
            const selectedBoxes = Array.from(document.querySelectorAll('input.action-select:checked'));
            const selectedIds = selectedBoxes.map(box => box.value);

            if (selectedIds.length === 0) {
                showToast('Please select at least one combination.', false);
                return;
            }

            const stock = prompt("Enter new stock quantity for selected combinations:");
            if (stock === null) return;

            fetch('bulk-set-stock/', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': document.querySelector('input[name=csrfmiddlewaretoken]').value,
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: new URLSearchParams({
                    'ids[]': selectedIds,
                    'stock': stock,
                }),
            })
            .then(res => res.json())
            .then(data => {
                showToast(data.message, data.success);
                if (data.success) {
                    setTimeout(() => window.location.reload(), 1000);
                }
            })
            .catch(err => {
                showToast("Request failed: " + err, false);
            });
        }
    });
});



