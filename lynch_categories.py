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

The module also implements Lynch's investment checklist from Chapter 15 of "One Up on Wall Street" 
to provide tailored recommendations based on the stock's category.
"""

import logging
import numpy as np
from typing import Dict, List, Any, Optional, Union

logger = logging.getLogger(__name__)

# Define Lynch's investment checklist for each category
LYNCH_CHECKLISTS = {
    "Slow Grower": [
        "Focus on dividend yield and stability",
        "Ensure the company isn't accumulating excessive debt",
        "Monitor for signs of industry disruption"
    ],
    "Stalwart": [
        "Look for reasonable P/E ratios relative to growth rate",
        "Monitor for signs of overexpansion",
        "Watch for declining profit margins",
        "Consider buying during temporary setbacks"
    ],
    "Fast Grower": [
        "Look for companies expanding within a sustainable niche market",
        "Be cautious of companies growing too rapidly without solid fundamentals",
        "Prefer a reasonable P/E ratio relative to growth rate (PEG ratio)",
        "Check if the company is still in the early stages of growth"
    ],
    "Cyclical": [
        "Invest during industry downturns and sell during upswings",
        "Watch for inventory levels and capacity utilization as indicators",
        "Compare current P/E ratio to historical cycle lows and highs",
        "Monitor economic indicators that affect the industry"
    ],
    "Turnaround": [
        "Identify specific catalysts for recovery (new management, product lines)",
        "Ensure the company has sufficient cash flow to sustain operations during recovery",
        "Monitor debt levels and repayment capabilities",
        "Look for signs of improved efficiency or cost-cutting measures"
    ],
    "Asset Play": [
        "Assess the true value of assets like real estate, patents, or subsidiaries",
        "Consider the impact of debt on asset value",
        "Look for catalysts that might unlock the hidden value",
        "Verify that the market is significantly undervaluing the assets"
    ],
    "General": [
        "Assess P/E ratio relative to company's historical P/E and industry peers",
        "Check for lower institutional ownership (may indicate undiscovered potential)",
        "Look for insider buying and company share buybacks as positive signals",
        "Verify consistent and sustainable earnings growth"
    ]
}

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
    
    # Get Lynch's specific recommendations for this category
    if category in LYNCH_CHECKLISTS:
        recommendations = LYNCH_CHECKLISTS[category]
    else:
        recommendations = LYNCH_CHECKLISTS["General"]
    
    # Include additional category-specific metrics that were calculated
    return {
        "category": category,
        "description": category_description,
        "key_metrics": key_metrics,
        "recommendations": recommendations
    }


def evaluate_stock_against_checklist(data: Dict[str, Any], category: str) -> Dict[str, Any]:
    """
    Evaluates a stock against Peter Lynch's checklist for its specific category.
    
    Args:
        data (dict): Stock financial data and metrics
        category (str): Lynch category of the stock
        
    Returns:
        dict: Evaluation results including checklist items and scores
    """
    # Get the appropriate checklist for this category
    checklist = LYNCH_CHECKLISTS.get(category, LYNCH_CHECKLISTS["General"])
    
    # Initialize evaluation results
    evaluation = {
        "checklist_items": checklist,
        "meets_criteria": [],
        "needs_attention": [],
        "overall_score": 0
    }
    
    # Extract key metrics
    pe_ratio = data.get('pe_ratio')
    peg_ratio = data.get('peg_ratio')
    dividend_yield = data.get('dividend_yield')
    debt_to_equity = data.get('debt_to_equity')
    price_to_book = data.get('price_to_book')
    assets_to_ev = data.get('assets_to_ev')
    revenue_growth = data.get('revenue_growth')
    earnings_growth = data.get('earnings_growth')
    price_change_percent = data.get('price_change_percent')
    
    # Category-specific evaluations
    if category == "Slow Grower":
        # Evaluate for Slow Growers
        if dividend_yield is not None and dividend_yield > 2.0:
            evaluation["meets_criteria"].append("Good dividend yield (>2%)")
            evaluation["overall_score"] += 1
        else:
            evaluation["needs_attention"].append("Dividend yield could be higher")
        
        if debt_to_equity is not None and debt_to_equity < 0.8:
            evaluation["meets_criteria"].append("Reasonable debt levels")
            evaluation["overall_score"] += 1
        else:
            evaluation["needs_attention"].append("Monitor debt levels")
            
    elif category == "Stalwart":
        # Evaluate for Stalwarts
        if pe_ratio is not None and earnings_growth is not None:
            if pe_ratio < (earnings_growth * 1.5):
                evaluation["meets_criteria"].append("Good P/E ratio relative to growth")
                evaluation["overall_score"] += 1
            else:
                evaluation["needs_attention"].append("P/E ratio may be too high relative to growth")
        
        if price_change_percent is not None and price_change_percent < -10:
            evaluation["meets_criteria"].append("Currently experiencing a temporary setback (potential buying opportunity)")
            evaluation["overall_score"] += 1
            
    elif category == "Fast Grower":
        # Evaluate for Fast Growers
        if revenue_growth is not None:
            if revenue_growth > 25:
                evaluation["meets_criteria"].append("Exceptional revenue growth (>25%)")
                evaluation["overall_score"] += 1.5
            elif revenue_growth > 20:
                evaluation["meets_criteria"].append("Strong revenue growth (>20%)")
                evaluation["overall_score"] += 1
            elif revenue_growth > 15:
                evaluation["meets_criteria"].append("Good revenue growth (>15%)")
                evaluation["overall_score"] += 0.5
            else:
                evaluation["needs_attention"].append("Revenue growth may be insufficient for a Fast Grower")
        
        # Lynch emphasized that Fast Growers should be reasonably priced relative to growth
        if peg_ratio is not None:
            if peg_ratio < 0.8:
                evaluation["meets_criteria"].append("Excellent PEG ratio (<0.8)")
                evaluation["overall_score"] += 1.5
            elif peg_ratio < 1.2:
                evaluation["meets_criteria"].append("Attractive PEG ratio (<1.2)")
                evaluation["overall_score"] += 1
            elif peg_ratio < 1.5:
                evaluation["meets_criteria"].append("Acceptable PEG ratio (<1.5)")
                evaluation["overall_score"] += 0.5
            else:
                evaluation["needs_attention"].append("PEG ratio may be too high for growth rate")
                
        # Lynch favored companies that could expand nationally/internationally
        industry = data.get('industry')
        if industry in ["Retail", "Restaurants", "Consumer Services", "Technology"]:
            evaluation["meets_criteria"].append("Industry with strong expansion potential")
            evaluation["overall_score"] += 0.5
            
    elif category == "Cyclical":
        # Evaluate for Cyclicals
        # Lynch emphasized buying cyclicals during downturns (when P/E is low) and selling during booms
        if pe_ratio is not None:
            # Simplistic assessment - ideally would compare to historical cycle
            if pe_ratio < 8:
                evaluation["meets_criteria"].append("Very low P/E ratio (strong buying opportunity)")
                evaluation["overall_score"] += 1.5
            elif pe_ratio < 12:
                evaluation["meets_criteria"].append("Low P/E ratio (potential buying opportunity)")
                evaluation["overall_score"] += 1
            elif pe_ratio > 25:
                evaluation["needs_attention"].append("Very high P/E ratio (consider taking profits)")
            elif pe_ratio > 18:
                evaluation["needs_attention"].append("High P/E ratio (approaching peak valuation)")
        
        # Price movement assessment
        if price_change_percent is not None:
            if price_change_percent < -30:
                evaluation["meets_criteria"].append("Significant downturn (strong buying opportunity)")
                evaluation["overall_score"] += 1.5
            elif price_change_percent < -20:
                evaluation["meets_criteria"].append("Currently in a downturn (potential buying opportunity)")
                evaluation["overall_score"] += 1
            elif price_change_percent > 50:
                evaluation["needs_attention"].append("Significant upturn (consider taking profits)")
        
        # Industry assessment
        industry = data.get('industry')
        cyclical_industries = ["Automotive", "Steel", "Chemicals", "Construction", 
                              "Manufacturing", "Airlines", "Hotels", "Energy"]
        if industry in cyclical_industries:
            evaluation["meets_criteria"].append(f"Confirmed cyclical industry: {industry}")
            evaluation["overall_score"] += 0.5
            
    elif category == "Turnaround":
        # Evaluate for Turnarounds
        if debt_to_equity is not None:
            if debt_to_equity < 2.0:
                evaluation["meets_criteria"].append("Manageable debt level for recovery")
                evaluation["overall_score"] += 1
            else:
                evaluation["needs_attention"].append("High debt level may impede recovery")
        
        # A positive price change after a big drop could indicate recovery in progress
        if price_change_percent is not None and price_change_percent > 10:
            evaluation["meets_criteria"].append("Shows signs of recovery in share price")
            evaluation["overall_score"] += 1
            
    elif category == "Asset Play":
        # Evaluate for Asset Plays
        if price_to_book is not None:
            if price_to_book < 1.0:
                evaluation["meets_criteria"].append("Trading below book value")
                evaluation["overall_score"] += 1
            elif price_to_book < 1.3:
                evaluation["meets_criteria"].append("Trading at reasonable price-to-book ratio")
                evaluation["overall_score"] += 0.5
            else:
                evaluation["needs_attention"].append("Price to book ratio may be too high for an Asset Play")
        
        if assets_to_ev is not None:
            if assets_to_ev > 1.2:
                evaluation["meets_criteria"].append("Assets worth more than enterprise value")
                evaluation["overall_score"] += 1
            elif assets_to_ev > 0.8:
                evaluation["meets_criteria"].append("Assets represent significant portion of enterprise value")
                evaluation["overall_score"] += 0.5
            else:
                evaluation["needs_attention"].append("Enterprise value significantly higher than asset value")
                
        # Check if company has property/real estate that might be undervalued
        if data.get('sector') in ['Real Estate', 'Consumer Discretionary', 'Energy']:
            evaluation["meets_criteria"].append("Operates in sector likely to have valuable physical assets")
            evaluation["overall_score"] += 0.5
    
    # Normalize score to 0-5 range
    if evaluation["overall_score"] > 0:
        evaluation["overall_score"] = min(5, evaluation["overall_score"])
    
    return evaluation