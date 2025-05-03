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
    
    // Top Tech Companies
    document.getElementById('loadTechTickers').addEventListener('click', function(e) {
        e.preventDefault();
        tickerListTextarea.value = 'AAPL, MSFT, GOOGL, META, AMZN, TSLA, NVDA, AMD, INTC, ADBE';
    });
    
    // Top Financial Companies
    document.getElementById('loadFinanceTickers').addEventListener('click', function(e) {
        e.preventDefault();
        tickerListTextarea.value = 'JPM, BAC, WFC, C, GS, MS, BLK, AXP, V, MA';
    });
    
    // Top Healthcare Companies
    document.getElementById('loadHealthcareTickers').addEventListener('click', function(e) {
        e.preventDefault();
        tickerListTextarea.value = 'JNJ, PFE, MRK, ABBV, BMY, UNH, CVS, AMGN, GILD, BIIB';
    });
    
    // Popular ETFs
    document.getElementById('loadETFs').addEventListener('click', function(e) {
        e.preventDefault();
        tickerListTextarea.value = 'SPY, QQQ, VTI, VEA, BND, VWO, GLD, IWM, VIG, VXUS';
    });
    
    // Dividend Aristocrats
    document.getElementById('loadDividendStocks').addEventListener('click', function(e) {
        e.preventDefault();
        tickerListTextarea.value = 'KO, JNJ, PG, XOM, MMM, WMT, ED, MCD, PEP, CVX';
    });
    
    // Top European Stocks
    document.getElementById('loadEuropeanStocks').addEventListener('click', function(e) {
        e.preventDefault();
        tickerListTextarea.value = 'SAP.DE, ADS.DE, BAYN.DE, SIE.DE, ALV.DE, BNP.PA, MC.PA, SAN.MC, ITX.MC, ENEL.MI';
    });
    
    // Top Norwegian Stocks
    document.getElementById('loadNorwegianStocks').addEventListener('click', function(e) {
        e.preventDefault();
        tickerListTextarea.value = 'EQNR.OL, DNB.OL, TEL.OL, ORK.OL, YAR.OL, NHY.OL, AKRBP.OL, MOWI.OL, AKSO.OL, SALM.OL';
    });
    
    // Top Asian Stocks
    document.getElementById('loadAsianStocks').addEventListener('click', function(e) {
        e.preventDefault();
        tickerListTextarea.value = '9988.HK, 0700.HK, 9988.HK, 7203.T, 9984.T, 005930.KS, 000660.KS, 2330.TW, 3690.HK, 1398.HK';
    });
});
