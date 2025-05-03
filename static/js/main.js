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
    
    // Preset ticker lists
    const tickerListTextarea = document.getElementById('tickerList');
    
    // Check if the textarea exists before setting up the event handlers
    if (tickerListTextarea) {
        // Function to safely add click handlers
        function addClickHandler(elementId, tickerList) {
            const element = document.getElementById(elementId);
            if (element) {
                element.addEventListener('click', function(e) {
                    e.preventDefault();
                    tickerListTextarea.value = tickerList;
                });
            }
        }
        
        // Add handlers for all preset ticker lists
        addClickHandler('loadTechTickers', 'AAPL, MSFT, GOOGL, META, AMZN, TSLA, NVDA, AMD, INTC, ADBE');
        addClickHandler('loadFinanceTickers', 'JPM, BAC, WFC, C, GS, MS, BLK, AXP, V, MA');
        addClickHandler('loadHealthcareTickers', 'JNJ, PFE, MRK, ABBV, BMY, UNH, CVS, AMGN, GILD, BIIB');
        addClickHandler('loadETFs', 'SPY, QQQ, VTI, VEA, BND, VWO, GLD, IWM, VIG, VXUS');
        addClickHandler('loadDividendStocks', 'KO, JNJ, PG, XOM, MMM, WMT, ED, MCD, PEP, CVX');
        
        // International markets
        addClickHandler('loadEuropeanStocks', 'SAP.DE, ADS.DE, BAYN.DE, SIE.DE, ALV.DE, BNP.PA, MC.PA, SAN.MC, ITX.MC, ENEL.MI');
        addClickHandler('loadNorwegianStocks', 'EQNR.OL, DNB.OL, TEL.OL, ORK.OL, YAR.OL, NHY.OL, AKRBP.OL, MOWI.OL, AKSO.OL, SALM.OL');
        addClickHandler('loadAsianStocks', '9988.HK, 0700.HK, 9988.HK, 7203.T, 9984.T, 005930.KS, 000660.KS, 2330.TW, 3690.HK, 1398.HK');
    }
});
