"""
Lynch Categories Module

This module implements Peter Lynch's stock categorization system from 'One Up on Wall Street'.
It classifies stocks into six categories:
1. Slow Growers - large, mature companies with modest growth (<10% annually)
2. Stalwarts - large, established companies with moderate growth (10-12% annually)
3. Fast Growers - small, aggressive companies with high growth potential (>20% annually)
4. Cyclicals - companies whose performance is tied to economic cycles
5. Turnarounds - companies recovering from poor performance
6. Asset Plays - companies with valuable assets not reflected in the stock price
"""

import logging
import numpy as np

logger = logging.getLogger(__name__)

def categorize_stock(data):
    """
    Categorize a stock according to Peter Lynch's six categories.
    
    Args:
        data (dict): Stock financial data and metrics
        
    Returns:
        dict: Category information including name, description, key metrics, and recommendations
    """
    # Extract key metrics needed for categorization
    market_cap = data.get('market_cap')
    earnings_growth = data.get('earnings_growth')
    industry = data.get('industry', '').lower()
    sector = data.get('sector', '').lower()
    revenue_growth = data.get('revenue_growth')
    price_change = data.get('price_change_percent')
    book_value_per_share = data.get('book_value_per_share')
    current_price = data.get('current_price')
    total_assets = data.get('total_assets')
    enterprise_value = data.get('enterprise_value')
    
    # Default to None for category
    category = None
    category_description = ""
    key_metrics = []
    recommendations = []
    
    # Identify cyclical industries
    cyclical_industries = ['automotive', 'airline', 'mining', 'steel', 'construction', 
                          'semiconductor', 'energy', 'oil', 'gas', 'housing', 'travel']
    
    cyclical_sectors = ['materials', 'energy', 'industrials', 'consumer discretionary']
    
    # Check if the company is in a cyclical industry
    is_cyclical = any(industry in industry for industry in cyclical_industries) or \
                 any(sector in sector for sector in cyclical_sectors)
    
    # Determine if it's potentially a turnaround situation
    is_potential_turnaround = price_change is not None and price_change < -30
    
    # Determine if it's potentially an asset play
    price_to_book = None
    if current_price is not None and book_value_per_share is not None and book_value_per_share > 0:
        price_to_book = current_price / book_value_per_share
    
    is_asset_play = price_to_book is not None and price_to_book < 1.0
    
    # Assets to EV ratio to identify hidden asset value
    assets_to_ev = None
    if total_assets is not None and enterprise_value is not None and enterprise_value > 0:
        assets_to_ev = total_assets / enterprise_value
        
    if assets_to_ev is not None and assets_to_ev > 1.2:
        is_asset_play = True
    
    # Categorize based on the most distinct characteristics
    
    # First check for special cases
    if is_asset_play:
        category = "Asset Play"
        category_description = "Companies with valuable assets not reflected in the stock price"
        key_metrics = [
            f"Price-to-Book: {price_to_book:.2f}" if price_to_book else "Price-to-Book: N/A",
            f"Assets to Enterprise Value: {assets_to_ev:.2f}" if assets_to_ev else "Assets to EV: N/A"
        ]
        recommendations = [
            "Focus on the true value of assets (real estate, patents, subsidiaries)",
            "Consider the impact of debt on asset value",
            "Look for catalysts that might unlock the hidden value"
        ]
    
    elif is_potential_turnaround:
        category = "Turnaround"
        category_description = "Companies recovering from poor performance"
        key_metrics = [
            f"1-Year Price Change: {price_change:.2f}%" if price_change else "Price Change: N/A",
            f"Debt-to-Equity: {data.get('debt_to_equity'):.2f}" if data.get('debt_to_equity') else "Debt-to-Equity: N/A"
        ]
        recommendations = [
            "Identify specific catalysts for recovery (new management, product lines)",
            "Ensure sufficient cash flow to sustain operations during recovery",
            "Monitor debt levels and repayment capabilities"
        ]
    
    elif is_cyclical:
        category = "Cyclical"
        category_description = "Companies whose performance is tied to economic cycles"
        key_metrics = [
            f"Industry: {industry}",
            f"P/E Ratio: {data.get('pe_ratio'):.2f}" if data.get('pe_ratio') else "P/E Ratio: N/A"
        ]
        recommendations = [
            "Compare current P/E ratio to historical cycle lows and highs",
            "Monitor industry inventory levels and capacity utilization",
            "Consider where we are in the economic cycle"
        ]
        
    # Then check for growth categories
    elif earnings_growth is not None:
        # Convert earnings_growth to percentage if it's in decimal form
        growth_rate = earnings_growth
        if isinstance(growth_rate, (int, float)) and growth_rate < 1:
            growth_rate = growth_rate * 100
            
        if market_cap is not None and market_cap > 100_000_000_000 and growth_rate < 10:  # $100B+
            category = "Slow Grower"
            category_description = "Large, mature companies with modest growth (less than 10% annually)"
            key_metrics = [
                f"Dividend Yield: {data.get('dividend_yield'):.2f}%" if data.get('dividend_yield') else "Dividend Yield: N/A",
                f"Growth Rate: {growth_rate:.2f}%" if growth_rate is not None else "Growth Rate: N/A"
            ]
            recommendations = [
                "Focus on dividend yield and stability",
                "Watch for excessive debt accumulation",
                "Monitor for signs of industry disruption"
            ]
            
        elif market_cap is not None and market_cap > 10_000_000_000 and 10 <= growth_rate <= 20:  # $10B+
            category = "Stalwart"
            category_description = "Large, established companies with solid financials and moderate growth (10-20% annually)"
            key_metrics = [
                f"Growth Rate: {growth_rate:.2f}%" if growth_rate is not None else "Growth Rate: N/A",
                f"P/E Ratio: {data.get('pe_ratio'):.2f}" if data.get('pe_ratio') else "P/E Ratio: N/A"
            ]
            recommendations = [
                "Look for reasonable P/E ratios relative to growth rate",
                "Monitor for signs of overexpansion",
                "Watch for declining profit margins"
            ]
            
        elif growth_rate > 20:
            category = "Fast Grower"
            category_description = "Companies with high growth (more than 20% annually)"
            key_metrics = [
                f"Growth Rate: {growth_rate:.2f}%" if growth_rate is not None else "Growth Rate: N/A",
                f"PEG Ratio: {data.get('peg_ratio'):.2f}" if data.get('peg_ratio') else "PEG Ratio: N/A"
            ]
            recommendations = [
                "Ensure the company is expanding within a sustainable niche",
                "Be cautious of high P/E ratios, but focus on the PEG ratio",
                "Watch for signs of growth that's too rapid without solid fundamentals"
            ]
    
    # Default categorization if no specific category is determined
    if category is None:
        if market_cap is not None and market_cap > 50_000_000_000:  # $50B+
            category = "Stalwart"
            category_description = "Large, established companies with solid financials"
            key_metrics = [
                f"P/E Ratio: {data.get('pe_ratio'):.2f}" if data.get('pe_ratio') else "P/E Ratio: N/A",
                f"Dividend Yield: {data.get('dividend_yield'):.2f}%" if data.get('dividend_yield') else "Dividend Yield: N/A"
            ]
            recommendations = [
                "Look for reasonable P/E ratios relative to growth rate",
                "Monitor for signs of overexpansion",
                "Watch for declining profit margins"
            ]
        else:
            category = "Unknown"
            category_description = "Unable to categorize with available data"
            key_metrics = []
            recommendations = [
                "Gather more information about the company's growth trajectory",
                "Investigate industry dynamics and competitive position",
                "Review recent quarterly reports for trends"
            ]
    
    logger.debug(f"Categorized {data.get('ticker')} as {category}")
    
    return {
        "category": category,
        "description": category_description,
        "key_metrics": key_metrics,
        "recommendations": recommendations
    }