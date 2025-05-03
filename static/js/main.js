document.addEventListener('DOMContentLoaded', function() {
    // Handle the form submission to show loading indicator
    const stockForm = document.getElementById('stockForm');
    const loadingIndicator = document.getElementById('loading');
    
    if (stockForm) {
        stockForm.addEventListener('submit', function() {
            // Show loading indicator
            loadingIndicator.classList.remove('d-none');
            
            // Disable the submit button to prevent double submissions
            const submitBtn = document.getElementById('submitBtn');
            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Loading...';
            }
        });
    }
    
    // Handle tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl)
    });
    
    // Add event listeners for quick example tickers
    const exampleTickers = document.querySelectorAll('.example-ticker');
    exampleTickers.forEach(function(ticker) {
        ticker.addEventListener('click', function(e) {
            e.preventDefault();
            document.getElementById('ticker').value = this.dataset.ticker;
            stockForm.submit();
        });
    });
    
    // Auto-focus the ticker input field
    const tickerInput = document.getElementById('ticker');
    if (tickerInput) {
        tickerInput.focus();
    }
});
