document.addEventListener('DOMContentLoaded', function() {
    // Check if we have result data
    if (typeof resultData !== 'undefined') {
        // Create the ratios chart
        createRatiosChart();
        
        // Create the capital structure chart
        createCapitalStructureChart();
    }
});

function createRatiosChart() {
    const ctx = document.getElementById('ratiosChart').getContext('2d');
    
    // Define the data for the chart
    const data = {
        labels: ['Earnings Yield', 'Return on Capital', 'Dividend Yield', '5-Year Avg Dividend Yield'],
        datasets: [{
            label: `${resultData.ticker} Ratios (%)`,
            data: [
                resultData.earningsYield,
                resultData.returnOnCapital,
                resultData.dividendYield,
                resultData.fiveYearAvgDividendYield
            ],
            backgroundColor: [
                'rgba(75, 192, 192, 0.6)',
                'rgba(54, 162, 235, 0.6)',
                'rgba(255, 206, 86, 0.6)',
                'rgba(255, 159, 64, 0.6)'
            ],
            borderColor: [
                'rgba(75, 192, 192, 1)',
                'rgba(54, 162, 235, 1)',
                'rgba(255, 206, 86, 1)',
                'rgba(255, 159, 64, 1)'
            ],
            borderWidth: 1
        }]
    };
    
    // Filter out null values
    const filteredLabels = [];
    const filteredData = [];
    const filteredBackgroundColor = [];
    const filteredBorderColor = [];
    
    for (let i = 0; i < data.datasets[0].data.length; i++) {
        if (data.datasets[0].data[i] !== null) {
            filteredLabels.push(data.labels[i]);
            filteredData.push(data.datasets[0].data[i]);
            filteredBackgroundColor.push(data.datasets[0].backgroundColor[i]);
            filteredBorderColor.push(data.datasets[0].borderColor[i]);
        }
    }
    
    data.labels = filteredLabels;
    data.datasets[0].data = filteredData;
    data.datasets[0].backgroundColor = filteredBackgroundColor;
    data.datasets[0].borderColor = filteredBorderColor;
    
    // Create the chart
    if (data.labels.length > 0) {
        const ratiosChart = new Chart(ctx, {
            type: 'bar',
            data: data,
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Percentage (%)'
                        }
                    }
                },
                plugins: {
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                let label = context.dataset.label || '';
                                if (label) {
                                    label += ': ';
                                }
                                if (context.parsed.y !== null) {
                                    label += new Intl.NumberFormat('en-US', { 
                                        style: 'decimal', 
                                        minimumFractionDigits: 2,
                                        maximumFractionDigits: 2
                                    }).format(context.parsed.y) + '%';
                                }
                                return label;
                            }
                        }
                    }
                }
            }
        });
    } else {
        // Show a message if no data is available
        document.getElementById('ratiosChart').parentNode.innerHTML = '<div class="alert alert-info">No ratio data available for this stock.</div>';
    }
}

function createCapitalStructureChart() {
    const ctx = document.getElementById('capitalStructureChart').getContext('2d');
    
    // Only create the chart if we have the required data
    if (resultData.marketCap !== null && resultData.totalDebt !== null) {
        // Define the market cap and debt values
        const marketCap = resultData.marketCap || 0;
        const totalDebt = resultData.totalDebt || 0;
        const cash = resultData.cash || 0;
        
        // Format the values for labels (in billions)
        const formatValue = (value) => {
            if (value >= 1_000_000_000) {
                return (value / 1_000_000_000).toFixed(2) + 'B';
            } else if (value >= 1_000_000) {
                return (value / 1_000_000).toFixed(2) + 'M';
            } else {
                return value.toFixed(2);
            }
        };
        
        // Create the pie chart
        const capitalStructureChart = new Chart(ctx, {
            type: 'pie',
            data: {
                labels: ['Market Cap', 'Total Debt', 'Cash'],
                datasets: [{
                    data: [marketCap, totalDebt, cash],
                    backgroundColor: [
                        'rgba(54, 162, 235, 0.6)',
                        'rgba(255, 99, 132, 0.6)',
                        'rgba(75, 192, 192, 0.6)'
                    ],
                    borderColor: [
                        'rgba(54, 162, 235, 1)',
                        'rgba(255, 99, 132, 1)',
                        'rgba(75, 192, 192, 1)'
                    ],
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'right',
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const label = context.label || '';
                                const value = context.raw;
                                return `${label}: ${formatValue(value)} (${((value / (marketCap + totalDebt + cash)) * 100).toFixed(1)}%)`;
                            }
                        }
                    }
                }
            }
        });
    } else {
        // Show a message if no data is available
        document.getElementById('capitalStructureChart').parentNode.innerHTML = '<div class="alert alert-info">No capital structure data available for this stock.</div>';
    }
}
