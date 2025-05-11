import os
import logging
import time
import random
import re
import requests
import pandas as pd
import numpy as np
import yfinance as yf
from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from stock_predictor import predict_price_movement
from lynch_categories import categorize_stock

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key")

# Configure database
database_url = os.environ.get("DATABASE_URL")
if database_url and database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_pre_ping": True,
    "pool_recycle": 300,
}

# Initialize the database
from models import db, TickerList
db.init_app(app)

with app.app_context():
    try:
        db.create_all()
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error creating database tables: {str(e)}")

# Sample data for major stocks to use when API is rate limited
SAMPLE_DATA = {
    "AAPL": {
        "market_cap": 2800000000000,
        "ebit": 126000000000,
        "total_debt": 119000000000,
        "cash": 62000000000,
        "current_assets": 135000000000,
        "current_liabilities": 125000000000,
        "net_fixed_assets": 43000000000,
        "company_name": "Apple Inc.",
        "industry": "Consumer Electronics",
        "sector": "Technology",
        "country": "United States",
        "currency": "USD",
        "current_price": 173.50,
        "previous_close": 172.40,
        "dividend_rate": 0.96,
        "dividend_yield": 0.55,
        "ex_dividend_date": "2023-08-11",
        "five_year_avg_dividend_yield": 0.65,
        "total_assets": 350000000000,
        "total_equity": 180000000000,
        "book_value_per_share": 11.50,
        "net_income": 100000000000
    },
    "MSFT": {
        "market_cap": 2600000000000,
        "ebit": 88000000000,
        "total_debt": 82000000000,
        "cash": 93000000000,
        "current_assets": 169000000000,
        "current_liabilities": 95000000000,
        "net_fixed_assets": 70000000000,
        "company_name": "Microsoft Corporation",
        "industry": "Software—Infrastructure",
        "sector": "Technology",
        "country": "United States",
        "currency": "USD",
        "current_price": 349.50,
        "previous_close": 347.80,
        "dividend_rate": 3.00,
        "dividend_yield": 0.86,
        "ex_dividend_date": "2023-08-16",
        "five_year_avg_dividend_yield": 0.92,
        "total_assets": 390000000000,
        "total_equity": 210000000000,
        "net_income": 72000000000,
        "book_value_per_share": 28.15
    }
}

# Function to fetch financial data from Yahoo Finance with fallback to sample data
def fetch_financial_data(ticker):
    logger.debug(f"Fetching data for ticker: {ticker}")
    
    # Check if we're being rate limited for common tickers
    use_sample_data = False
    
    # Add rate limiting protection
    
    # Small delay to avoid rate limiting (reduced to prevent timeout)
    delay = 0.1 + random.random() * 0.2
    logger.debug(f"Adding delay of {delay:.2f} seconds before API request")
    time.sleep(delay)
    
    # Try to get real data first
    if not use_sample_data:
        try:
            # Create Ticker object
            stock = yf.Ticker(ticker)
            
            # Use session object for better control over requests
            session = requests.Session()
            user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            session.headers.update({'User-Agent': user_agent})
            
            # Fetch data one at a time with error handling for each
            try:
                info = stock.info
                logger.debug(f"Retrieved info data for {ticker}")
            except Exception as e:
                logger.error(f"Error fetching info for {ticker}: {str(e)}")
                if "Too Many Requests" in str(e) and ticker.upper() in SAMPLE_DATA:
                    use_sample_data = True
                    logger.warning(f"Using sample data for {ticker} due to rate limiting")
                info = {}
                
            if not use_sample_data:
                try:
                    # Use annual financials
                    financials = stock.financials.T
                    logger.debug(f"Retrieved annual financials data for {ticker}")
                except Exception as e:
                    logger.error(f"Error fetching financials for {ticker}: {str(e)}")
                    if "Too Many Requests" in str(e) and ticker.upper() in SAMPLE_DATA:
                        use_sample_data = True
                        logger.warning(f"Using sample data for {ticker} due to rate limiting")
                    financials = pd.DataFrame()
                    
            if not use_sample_data:
                try:
                    # Use annual balance sheet
                    balance_sheet = stock.balance_sheet.T
                    logger.debug(f"Retrieved annual balance sheet data for {ticker}")
                except Exception as e:
                    logger.error(f"Error fetching balance sheet for {ticker}: {str(e)}")
                    if "Too Many Requests" in str(e) and ticker.upper() in SAMPLE_DATA:
                        use_sample_data = True
                        logger.warning(f"Using sample data for {ticker} due to rate limiting")
                    balance_sheet = pd.DataFrame()
            
            # Fetch dividend information
            if not use_sample_data:
                try:
                    dividend_data = stock.dividends
                    dividend_rate = info.get('dividendRate', None)
                    dividend_yield = info.get('dividendYield', None)
                    # Note: yfinance returns dividend_yield as a decimal (e.g., 0.076 for 7.6%)
                    # Already automatically multiplied by 100 when used in formatted_dividend_yield
                    ex_dividend_date = info.get('exDividendDate', None)
                    if ex_dividend_date:
                        ex_dividend_date = pd.to_datetime(ex_dividend_date, unit='s').strftime('%Y-%m-%d')
                    five_year_avg_dividend_yield = info.get('fiveYearAvgDividendYield', None)
                    logger.debug(f"Retrieved dividend data for {ticker}")
                except Exception as e:
                    logger.error(f"Error fetching dividend data for {ticker}: {str(e)}")
                    dividend_rate = None
                    dividend_yield = None
                    ex_dividend_date = None
                    five_year_avg_dividend_yield = None
            
            # Get earnings per share and growth data
            trailing_eps = None
            forward_eps = None
            earnings_growth = None
            
            if not use_sample_data:
                # Get EPS data from info
                trailing_eps = info.get('trailingEPS', None)
                forward_eps = info.get('forwardEps', None)
                earnings_growth = info.get('earningsGrowth', None)
                
                # If we don't have annual growth, try quarterly as fallback
                if earnings_growth is None:
                    earnings_growth = info.get('earningsQuarterlyGrowth', None)
                
                # Default growth rate if none available (for Graham formula)
                if earnings_growth is None:
                    earnings_growth = 0.05  # 5% growth
                elif isinstance(earnings_growth, (int, float)):
                    # Ensure growth is in decimal format (not percentage)
                    if earnings_growth > 1:
                        earnings_growth = earnings_growth / 100
            
            if not use_sample_data:
                # Market Cap (from info, not financials)
                market_cap = info.get('marketCap', None)
                logger.debug(f"Market Cap: {market_cap}")

                # EBIT (Operating Income)
                ebit = None
                if not financials.empty:
                    ebit = financials.get('Total Operating Income As Reported', [None])[0]
                    if ebit is None:
                        ebit = financials.get('Operating Income', [None])[0]
                logger.debug(f"EBIT: {ebit}")
                
                # Net Income
                net_income = None
                if not financials.empty:
                    net_income = financials.get('Net Income From Continuing Operation Net Minority Interest', [None])[0]
                    if net_income is None:
                        net_income = financials.get('Net Income', [None])[0]
                logger.debug(f"Net Income: {net_income}")
                
                # Debt (Total Debt)
                total_debt = None
                if not balance_sheet.empty:
                    total_debt = balance_sheet.get('Total Debt', [None])[0]
                    if total_debt is None:
                        # Try to compute from short-term and long-term debt
                        short_term_debt = balance_sheet.get('Short Term Debt', [0])[0] or 0
                        long_term_debt = balance_sheet.get('Long Term Debt', [0])[0] or 0
                        total_debt = short_term_debt + long_term_debt
                logger.debug(f"Total Debt: {total_debt}")
                
                # Cash (Cash and Cash Equivalents)
                cash = None
                if not balance_sheet.empty:
                    cash = balance_sheet.get('Cash And Cash Equivalents', [None])[0]
                    if cash is None:
                        cash = balance_sheet.get('Cash', [None])[0]
                logger.debug(f"Cash: {cash}")

                # Try to get Total Current Assets and Total Current Liabilities
                current_assets = None
                current_liabilities = None
                
                if not balance_sheet.empty:
                    current_assets = balance_sheet.get('Total Current Assets', [None])[0]
                    if not current_assets:
                        current_assets = balance_sheet.get('Current Assets', [None])[0]
                    
                    current_liabilities = balance_sheet.get('Total Current Liabilities', [None])[0]
                    if not current_liabilities:
                        current_liabilities = balance_sheet.get('Current Liabilities', [None])[0]
                
                logger.debug(f"Total Current Assets: {current_assets}")
                logger.debug(f"Total Current Liabilities: {current_liabilities}")

                # Net Working Capital (NWC)
                nwc = None
                if current_assets is not None and current_liabilities is not None:
                    nwc = current_assets - current_liabilities
                logger.debug(f"NWC: {nwc}")
                
                # Try to get Property Plant And Equipment (PP&E)
                net_fixed_assets = None
                if not balance_sheet.empty:
                    net_fixed_assets = balance_sheet.get('Property Plant And Equipment', [None])[0]
                    if not net_fixed_assets:
                        net_fixed_assets = balance_sheet.get('Net Property, Plant and Equipment', [None])[0]
                
                logger.debug(f"Net Fixed Assets (PP&E): {net_fixed_assets}")
                
                # Graham Principles Metrics - Get total assets and total equity
                total_assets = None
                total_equity = None
                book_value_per_share = None
                shares_outstanding = None
                
                if not balance_sheet.empty:
                    # Try to get Total Assets
                    total_assets = balance_sheet.get('Total Assets', [None])[0]
                    logger.debug(f"Total Assets: {total_assets}")
                    
                    # Try to get Total Equity (Stockholders' Equity)
                    total_equity = balance_sheet.get('Total Stockholder Equity', [None])[0]
                    if total_equity is None:
                        total_equity = balance_sheet.get('Stockholders Equity', [None])[0]
                    if total_equity is None:
                        total_equity = balance_sheet.get('Total Equity', [None])[0]
                    logger.debug(f"Total Equity: {total_equity}")
                
                # Get shares outstanding for book value per share calculation
                if info:
                    shares_outstanding = info.get('sharesOutstanding', None)
                    logger.debug(f"Shares Outstanding: {shares_outstanding}")
                
                # Calculate book value per share
                if total_equity is not None and shares_outstanding is not None and shares_outstanding > 0:
                    book_value_per_share = total_equity / shares_outstanding
                    logger.debug(f"Book Value Per Share: {book_value_per_share}")
                    
                # Get company name and some additional info for display
                company_name = info.get('shortName', ticker.upper())
                industry = info.get('industry', 'N/A')
                sector = info.get('sector', 'N/A')
                country = info.get('country', 'N/A')
                currency = info.get('currency', 'USD')
                
                # Current price and price changes
                current_price = info.get('currentPrice', None)
                previous_close = info.get('previousClose', None)
                
                # Get historical price data for prediction model (last 365 days)
                historical_data = None
                try:
                    historical_data = stock.history(period='1y')
                    logger.debug(f"Retrieved historical price data for {ticker}")
                except Exception as e:
                    logger.error(f"Error fetching historical data for {ticker}: {str(e)}")
                    historical_data = None
                
                price_change = None
                price_change_percent = None
                if current_price and previous_close:
                    price_change = current_price - previous_close
                    price_change_percent = (price_change / previous_close) * 100
                
                # Check if we have minimum required data
                if market_cap is None and ebit is None and (total_debt is None or cash is None):
                    if ticker.upper() in SAMPLE_DATA:
                        use_sample_data = True
                        logger.warning(f"Using sample data for {ticker} due to insufficient data from API")
                    else:
                        raise Exception("Insufficient data retrieved from API, possibly due to rate limiting")
            
        except Exception as e:
            logger.error(f"Error fetching data for {ticker}: {str(e)}")
            if "Too Many Requests" in str(e) and ticker.upper() in SAMPLE_DATA:
                use_sample_data = True
                logger.warning(f"Using sample data for {ticker} due to rate limiting")
            else:
                return {'error': str(e)}
    
    # Use sample data if needed
    if use_sample_data and ticker.upper() in SAMPLE_DATA:
        logger.info(f"Using sample data for {ticker}")
        
        data = SAMPLE_DATA[ticker.upper()]
        
        market_cap = data['market_cap']
        ebit = data['ebit']
        total_debt = data['total_debt']
        cash = data['cash']
        current_assets = data['current_assets']
        current_liabilities = data['current_liabilities']
        nwc = current_assets - current_liabilities
        net_fixed_assets = data['net_fixed_assets']
        company_name = data['company_name']
        industry = data['industry']
        sector = data['sector']
        country = data['country']
        currency = data['currency']
        current_price = data['current_price']
        previous_close = data['previous_close']
        
        price_change = current_price - previous_close
        price_change_percent = (price_change / previous_close) * 100
        
        # Get dividend data from sample data
        dividend_rate = data.get('dividend_rate', None)
        dividend_yield = data.get('dividend_yield', None)
        ex_dividend_date = data.get('ex_dividend_date', None)
        five_year_avg_dividend_yield = data.get('five_year_avg_dividend_yield', None)
        
        # Get Graham Principles metrics from sample data
        total_assets = data.get('total_assets', None)
        total_equity = data.get('total_equity', None)
        book_value_per_share = data.get('book_value_per_share', None)
        
        # For sample data, we'll have a DataFrame-like structure for balance_sheet
        balance_sheet = None
    else:
        # If we're here and not using sample data, it means we successfully retrieved real data
        pass
        
    # Return data as a dictionary
    return {
        'market_cap': market_cap,
        'ebit': ebit,
        'total_debt': total_debt,
        'cash': cash,
        'nwc': nwc,
        'net_fixed_assets': net_fixed_assets,
        'balance_sheet': balance_sheet,
        'company_name': company_name,
        'industry': industry,
        'sector': sector,
        'country': country,
        'currency': currency,
        'current_price': current_price,
        'price_change': price_change,
        'price_change_percent': price_change_percent,
        'dividend_rate': dividend_rate,
        'dividend_yield': dividend_yield,
        'ex_dividend_date': ex_dividend_date,
        'five_year_avg_dividend_yield': five_year_avg_dividend_yield,
        'current_assets': current_assets,
        'current_liabilities': current_liabilities, 
        'total_assets': total_assets,
        'total_equity': total_equity,
        'book_value_per_share': book_value_per_share,
        'trailing_eps': trailing_eps,
        'forward_eps': forward_eps,
        'earnings_growth': earnings_growth,
        'net_income': net_income,
        'historical_data': historical_data
    }
    
# Process financial data for a single ticker
def process_financial_data(ticker, data):
    if 'error' in data:
        return None
    
    # Extract all necessary data for calculations
    market_cap = data['market_cap']
    ebit = data['ebit']
    total_debt = data['total_debt']
    cash = data['cash']
    nwc = data['nwc']
    net_fixed_assets = data['net_fixed_assets']
    company_name = data['company_name']
    currency = data['currency']
    current_price = data['current_price']
    dividend_yield = data['dividend_yield']
    dividend_rate = data['dividend_rate']
    current_assets = data.get('current_assets')
    current_liabilities = data.get('current_liabilities')
    total_assets = data.get('total_assets')
    total_equity = data.get('total_equity')
    book_value_per_share = data.get('book_value_per_share')
    
    # Get earnings per share and growth data
    trailing_eps = data.get('trailing_eps')
    forward_eps = data.get('forward_eps')
    earnings_growth = data.get('earnings_growth')
    
    # Calculate Enterprise Value
    if market_cap is not None and total_debt is not None and cash is not None:
        enterprise_value = market_cap + total_debt - cash
    else:
        enterprise_value = None
    
    # Calculate Earnings Yield using Magic Formula (EBIT/EV) - Key Magic Formula Metric #1
    if enterprise_value and ebit is not None and enterprise_value != 0:
        earnings_yield = (ebit / enterprise_value) * 100
    else:
        earnings_yield = None
        
    # Prepare for Traditional Earnings Yield calculation later
    # We'll need net_income from financial data
    traditional_earnings_yield = None
    
    # Calculate Invested Capital using a more comprehensive definition
    # Traditional definition of Invested Capital = Total Assets - Current Liabilities
    # This is more aligned with how it's calculated in financial analysis
    invested_capital = None
    if total_assets is not None and current_liabilities is not None:
        invested_capital = total_assets - current_liabilities
        logger.debug(f"Invested Capital calculated as Total Assets ({total_assets}) - Current Liabilities ({current_liabilities}) = {invested_capital}")
    # Fallback to net_fixed_assets + nwc if total_assets or current_liabilities are not available
    elif net_fixed_assets and nwc:
        invested_capital = net_fixed_assets + nwc
        logger.debug(f"Invested Capital calculated as Net Fixed Assets ({net_fixed_assets}) + NWC ({nwc}) = {invested_capital}")
    elif net_fixed_assets:
        invested_capital = net_fixed_assets
        logger.debug(f"Invested Capital calculated as Net Fixed Assets only = {invested_capital}")
    elif nwc:
        invested_capital = nwc
        logger.debug(f"Invested Capital calculated as NWC only = {invested_capital}")
    else:
        invested_capital = None
        logger.debug("Could not calculate Invested Capital due to missing data")
    
    # Calculate Return on Capital (EBIT/Invested Capital) - Key Magic Formula Metric #2
    if invested_capital and ebit is not None and invested_capital != 0:
        # ROC is calculated as a percentage (e.g., 37.7%)
        # We'll use the correct calculation for ROC: (EBIT / Invested Capital) *100
        # Note that ebit and invested_capital are already in the same unit (millions or billions)
        return_on_capital = (ebit / invested_capital) * 100
        logger.debug(f"ROC calculation: EBIT ({ebit}) / Invested Capital ({invested_capital}) * 100 = {return_on_capital:.2f}%")
    else:
        return_on_capital = None
        
    # Calculate Magic Formula Rank (higher is better)
    magic_score = 0
    if earnings_yield is not None and return_on_capital is not None:
        # Simple magic formula score - 
        # We're weighting both factors equally, but could adjust weights if needed
        magic_score = (earnings_yield / 2) + (return_on_capital / 2)
    else:
        magic_score = None
        
    # Calculate Traditional Earnings Yield (Net Income/Market Cap)
    traditional_earnings_yield = None
    net_income = data.get('net_income')
    
    # Calculate traditional earnings yield if we have market cap and net income
    if market_cap is not None and market_cap > 0 and net_income is not None:
        traditional_earnings_yield = (net_income / market_cap) * 100
        logger.debug(f"Traditional Earnings Yield calculation: Net Income ({net_income}) / Market Cap ({market_cap}) * 100 = {traditional_earnings_yield:.2f}%")
        
    # Calculate AlphaSpreads score - based on earnings quality and value
    # AlphaSpreads looks at consistency of earnings and relative valuation
    alpha_spreads_score = None
    if earnings_yield is not None and dividend_yield is not None:
        # Higher earnings yield relative to dividend yield indicates potential value
        earnings_to_dividend_ratio = earnings_yield / max(dividend_yield, 0.1)  # Prevent division by zero
        
        # AlphaSpreads typically values consistency and quality
        # A high ratio might indicate good value if earnings are consistent
        if earnings_to_dividend_ratio > 3:  # earnings yield more than 3x dividend yield
            alpha_spreads_score = min(100, earnings_to_dividend_ratio * 10)  # Cap at 100
        else:
            alpha_spreads_score = earnings_to_dividend_ratio * 20
    
    # Calculate Graham Calculator Intrinsic Value
    # Benjamin Graham's formula: Value = EPS × (8.5 + 2g) × 4.4 / Y
    # where g is growth rate, Y is AAA Corporate Bond yield (we use 4.5% as default)
    graham_value = None
    graham_upside = None
    intrinsic_value_class = "secondary"  # Default color class
    
    # First try to use actual EPS if available
    if trailing_eps is not None and current_price and current_price > 0:
        # Use actual trailing EPS and growth rate if available
        eps_to_use = trailing_eps
        growth_to_use = earnings_growth if isinstance(earnings_growth, (int, float)) else 0.05
        
        # Convert growth to percentage if it's in decimal form (0.05 -> 5.0)
        if growth_to_use < 1:
            growth_to_use = growth_to_use * 100
            
        # Cap growth rate at 15% for Graham formula (he was conservative)
        growth_to_use = min(growth_to_use, 15.0)
        
        # Graham's formula for intrinsic value
        aaa_yield = 4.5  # Current approximate AAA corporate bond yield
        graham_value = eps_to_use * (8.5 + 2 * (growth_to_use / 100)) * 4.4 / aaa_yield
        
        # Calculate potential upside/downside
        if current_price > 0:
            graham_upside = ((graham_value / current_price) - 1) * 100
            
            # Set color class based on upside potential
            if graham_upside > 50:
                intrinsic_value_class = "success"  # Deep value - more than 50% upside
            elif graham_upside > 20:
                intrinsic_value_class = "primary"  # Good value - 20-50% upside
            elif graham_upside > 0:
                intrinsic_value_class = "warning"  # Fair value - 0-20% upside
            else:
                intrinsic_value_class = "danger"   # Overvalued - negative upside (downside)
    
    # If actual EPS not available, fall back to estimate from EBIT
    elif ebit is not None and market_cap is not None and market_cap > 0:
        # Estimate EPS from EBIT (rough approximation)
        shares_outstanding = market_cap / current_price if current_price and current_price > 0 else None
        
        if shares_outstanding and shares_outstanding > 0:
            estimated_eps = ebit * 0.7 / shares_outstanding  # 0.7 factor for taxes approximation
            estimated_growth = earnings_growth if isinstance(earnings_growth, (int, float)) else 0.05
            
            # Convert growth to percentage if it's in decimal form (0.05 -> 5.0)
            if estimated_growth < 1:
                estimated_growth = estimated_growth * 100
                
            # Cap growth rate at 15% for Graham formula
            estimated_growth = min(estimated_growth, 15.0)
            
            # Graham's formula for intrinsic value
            aaa_yield = 4.5  # Current approximate AAA corporate bond yield
            graham_value = estimated_eps * (8.5 + 2 * (estimated_growth / 100)) * 4.4 / aaa_yield
            
            # Calculate potential upside/downside
            if current_price and current_price > 0:
                graham_upside = ((graham_value / current_price) - 1) * 100
                
                # Set color class based on upside potential
                if graham_upside > 50:
                    intrinsic_value_class = "success"  # Deep value - more than 50% upside
                elif graham_upside > 20:
                    intrinsic_value_class = "primary"  # Good value - 20-50% upside
                elif graham_upside > 0:
                    intrinsic_value_class = "warning"  # Fair value - 0-20% upside
                else:
                    intrinsic_value_class = "danger"   # Overvalued - negative upside (downside)
    
    # 1. Calculate Price-to-Book Ratio (Graham Principle #1)
    price_to_book = None
    price_to_book_class = "secondary"  # Default color class
    
    if current_price and book_value_per_share and book_value_per_share > 0:
        price_to_book = current_price / book_value_per_share
        # Color coding based on Graham's criteria: <1.5 is good value
        if price_to_book < 1.0:
            price_to_book_class = "success"  # Green - Excellent value
        elif price_to_book < 1.5:
            price_to_book_class = "primary"  # Blue - Good value
        elif price_to_book < 2.5:
            price_to_book_class = "warning"  # Yellow - Fair value
        else:
            price_to_book_class = "danger"   # Red - Poor value
    
    # 2. Calculate Current Ratio (Graham Principle #2)
    current_ratio = None
    current_ratio_class = "secondary"  # Default color class
    
    if current_assets and current_liabilities and current_liabilities > 0:
        current_ratio = current_assets / current_liabilities
        # Color coding based on Graham's criteria: >2 is excellent, >1.5 is good
        if current_ratio > 2.0:
            current_ratio_class = "success"  # Green - Excellent financial health
        elif current_ratio > 1.5:
            current_ratio_class = "primary"  # Blue - Good financial health
        elif current_ratio > 1.0:
            current_ratio_class = "warning"  # Yellow - Adequate financial health
        else:
            current_ratio_class = "danger"   # Red - Poor financial health
    
    # 3. Calculate Debt-to-Equity Ratio (Graham Principle #3)
    debt_to_equity = None
    debt_to_equity_class = "secondary"  # Default color class
    
    if total_debt is not None and total_equity is not None and total_equity > 0:
        debt_to_equity = total_debt / total_equity
        # Color coding based on Graham's criteria: <0.5 is excellent, <1.0 is good
        if debt_to_equity < 0.3:
            debt_to_equity_class = "success"  # Green - Low leverage, excellent
        elif debt_to_equity < 0.5:
            debt_to_equity_class = "primary"  # Blue - Moderate leverage, good
        elif debt_to_equity < 1.0:
            debt_to_equity_class = "warning"  # Yellow - Higher leverage, acceptable
        else:
            debt_to_equity_class = "danger"   # Red - High leverage, poor
    
    # Make a Buy/Not Buy Decision based on Earnings Yield and Return on Capital
    if earnings_yield is not None and return_on_capital is not None:
        if earnings_yield > 40 and return_on_capital > 40:
            buy_decision = "Not Buy"  # Too good to be true - potential trap
            decision_class = "danger"
        elif earnings_yield > 12 and return_on_capital > 15:
            buy_decision = "Strong Buy"
            decision_class = "success"
        elif earnings_yield > 4 and return_on_capital > 8:
            buy_decision = "Buy"
            decision_class = "primary"
        elif earnings_yield > 4 or return_on_capital > 8:
            buy_decision = "Hold"
            decision_class = "warning"
        else:
            buy_decision = "Not Buy"
            decision_class = "danger"
    else:
        buy_decision = "Insufficient Data"
        decision_class = "secondary"
    
    # Apply Peter Lynch's categorization
    lynch_analysis = None
    try:
        # Calculate annual revenue growth if possible
        revenue_growth = None
        financials = data.get('financials')
        if financials is not None and not financials.empty:
            if 'Total Revenue' in financials.index:
                revenues = financials.loc['Total Revenue']
                if len(revenues) >= 2:
                    latest_revenue = revenues.iloc[0]
                    previous_revenue = revenues.iloc[1]
                    if previous_revenue and previous_revenue != 0:
                        revenue_growth = ((latest_revenue / previous_revenue) - 1) * 100
                        logger.debug(f"Revenue growth calculated: {revenue_growth:.2f}%")
        
        # Prepare data for Lynch categorization
        industry = data.get('industry')
        sector = data.get('sector')
        price_change_percent = data.get('price_change_percent')
            
        lynch_data = {
            'ticker': ticker,
            'market_cap': market_cap,
            'earnings_growth': earnings_growth,
            'revenue_growth': revenue_growth, 
            'industry': industry,
            'sector': sector,
            'price_change_percent': price_change_percent,
            'book_value_per_share': book_value_per_share,
            'current_price': current_price,
            'total_assets': total_assets,
            'enterprise_value': enterprise_value,
            'pe_ratio': None,
            'peg_ratio': None,
            'debt_to_equity': debt_to_equity
        }
        
        # Calculate P/E ratio
        if current_price is not None and trailing_eps is not None and trailing_eps != 0:
            lynch_data['pe_ratio'] = current_price / trailing_eps
            logger.debug(f"P/E ratio calculated: {lynch_data['pe_ratio']:.2f}")
            
        # Calculate PEG ratio
        if lynch_data['pe_ratio'] is not None and earnings_growth is not None and earnings_growth != 0:
            # Ensure earnings_growth is in percentage form for PEG calculation
            growth_for_peg = earnings_growth
            if isinstance(growth_for_peg, (int, float)) and growth_for_peg < 1:
                growth_for_peg = growth_for_peg * 100
            lynch_data['peg_ratio'] = lynch_data['pe_ratio'] / growth_for_peg
            logger.debug(f"PEG ratio calculated: {lynch_data['peg_ratio']:.2f}")
        
        # Get Lynch categorization
        lynch_analysis = categorize_stock(lynch_data)
        logger.debug(f"Lynch category for {ticker}: {lynch_analysis['category']}")
    except Exception as e:
        logger.error(f"Error in Lynch categorization: {str(e)}")
        lynch_analysis = {
            "category": "Unknown",
            "description": "Unable to categorize with available data",
            "key_metrics": [],
            "recommendations": ["Insufficient data to provide Lynch category recommendations"]
        }
    
    # Make price prediction using machine learning model if historical data is available
    price_prediction = None
    prediction_class = "secondary"
    long_term_recommendation = None
    long_term_recommendation_class = "secondary"
    long_term_factors = []
    
    historical_data = data.get('historical_data')
    if historical_data is not None and not historical_data.empty and len(historical_data) >= 60:
        try:
            # Call the prediction function with 30-day forecast period
            prediction_result = predict_price_movement(ticker, historical_data, forecast_period=30)
            price_prediction = prediction_result
            
            # Set color class based on prediction
            if prediction_result['prediction'] == 'Strong Bullish':
                prediction_class = "success"
            elif prediction_result['prediction'] == 'Bullish':
                prediction_class = "primary"
            elif prediction_result['prediction'] == 'Neutral':
                prediction_class = "warning"
            elif prediction_result['prediction'] in ['Bearish', 'Strong Bearish']:
                prediction_class = "danger"
            
            # Extract long-term recommendation data if available
            if 'long_term_recommendation' in prediction_result and prediction_result['long_term_recommendation']:
                long_term_recommendation = prediction_result['long_term_recommendation']
                
                # Set color class based on long-term recommendation
                if long_term_recommendation == "Strong Long-Term Buy":
                    long_term_recommendation_class = "success"
                elif long_term_recommendation == "Long-Term Buy":
                    long_term_recommendation_class = "primary"
                elif long_term_recommendation == "Long-Term Neutral":
                    long_term_recommendation_class = "warning"
                elif long_term_recommendation == "Long-Term Caution":
                    long_term_recommendation_class = "info"
                elif long_term_recommendation == "Long-Term Avoid":
                    long_term_recommendation_class = "danger"
            
            # Extract long-term factors if available
            if 'long_term_factors' in prediction_result and prediction_result['long_term_factors']:
                long_term_factors = prediction_result['long_term_factors']
            
        except Exception as e:
            logger.error(f"Error making price prediction for {ticker}: {str(e)}")
            price_prediction = None
            prediction_class = "secondary"
            long_term_recommendation = None
            long_term_recommendation_class = "secondary"
            long_term_factors = []
    
    # Format values for display
    formatted_current_price = format_currency(current_price, currency)
    formatted_earnings_yield = f"{earnings_yield:.2f}%" if earnings_yield is not None else "N/A"
    formatted_traditional_earnings_yield = f"{traditional_earnings_yield:.2f}%" if traditional_earnings_yield is not None else "N/A"
    formatted_return_on_capital = f"{return_on_capital:.2f}%" if return_on_capital is not None else "N/A"
    formatted_dividend_yield = f"{dividend_yield:.2f}%" if dividend_yield is not None else "N/A"
    formatted_dividend_rate = format_currency(dividend_rate, currency) if dividend_rate is not None else "N/A"
    formatted_alpha_score = f"{alpha_spreads_score:.1f}" if alpha_spreads_score is not None else "N/A"
    formatted_graham_value = format_currency(graham_value, currency) if graham_value is not None else "N/A"
    formatted_graham_upside = f"{graham_upside:.1f}%" if graham_upside is not None else "N/A"
    
    # Format the Graham principle metrics
    formatted_price_to_book = f"{price_to_book:.2f}" if price_to_book is not None else "N/A"
    formatted_current_ratio = f"{current_ratio:.2f}" if current_ratio is not None else "N/A"
    formatted_debt_to_equity = f"{debt_to_equity:.2f}" if debt_to_equity is not None else "N/A"
    
    # Create a simplified result object for batch processing
    result = {
        'ticker': ticker,
        'company_name': company_name,
        'current_price': current_price,
        'formatted_current_price': formatted_current_price,
        'earnings_yield': earnings_yield,
        'formatted_earnings_yield': formatted_earnings_yield,
        'traditional_earnings_yield': traditional_earnings_yield,
        'formatted_traditional_earnings_yield': formatted_traditional_earnings_yield,
        'return_on_capital': return_on_capital,
        'formatted_return_on_capital': formatted_return_on_capital,
        'dividend_yield': dividend_yield,
        'formatted_dividend_yield': formatted_dividend_yield,
        'dividend_rate': dividend_rate,
        'formatted_dividend_rate': formatted_dividend_rate,
        'magic_score': magic_score,
        'formatted_magic_score': f"{magic_score:.1f}" if magic_score is not None else "N/A",
        'alpha_spreads_score': alpha_spreads_score,
        'formatted_alpha_score': formatted_alpha_score,
        'graham_value': graham_value,
        'formatted_graham_value': formatted_graham_value,
        'graham_upside': graham_upside,
        'formatted_graham_upside': formatted_graham_upside,
        'intrinsic_value_class': intrinsic_value_class,
        
        # Add Lynch categorization data
        'lynch_category': lynch_analysis.get('category') if lynch_analysis else "Unknown",
        'lynch_description': lynch_analysis.get('description') if lynch_analysis else "",
        'lynch_key_metrics': lynch_analysis.get('key_metrics', []) if lynch_analysis else [],
        'lynch_recommendations': lynch_analysis.get('recommendations', []) if lynch_analysis else [],
        
        # Add Graham's principles metrics
        'price_to_book': price_to_book,
        'formatted_price_to_book': formatted_price_to_book,
        'price_to_book_class': price_to_book_class,
        
        'current_ratio': current_ratio,
        'formatted_current_ratio': formatted_current_ratio,
        'current_ratio_class': current_ratio_class,
        
        'debt_to_equity': debt_to_equity,
        'formatted_debt_to_equity': formatted_debt_to_equity,
        'debt_to_equity_class': debt_to_equity_class,
        
        'buy_decision': buy_decision,
        'decision_class': decision_class,
        
        # Add price prediction information
        'price_prediction': price_prediction,
        'prediction_class': prediction_class,
        
        # Add long-term investment analysis
        'long_term_recommendation': long_term_recommendation,
        'long_term_recommendation_class': long_term_recommendation_class,
        'long_term_factors': long_term_factors
    }
    
    return result

# Helper function to format currency values
def format_currency(value, currency='USD'):
    if value is None:
        return "N/A"
    
    # Format large numbers with B for billions, M for millions, etc.
    if abs(value) >= 1_000_000_000:
        return f"{currency} {value/1_000_000_000:.2f}B"
    elif abs(value) >= 1_000_000:
        return f"{currency} {value/1_000_000:.2f}M"
    elif abs(value) >= 1_000:
        return f"{currency} {value/1_000:.2f}K"
    else:
        return f"{currency} {value:.2f}"

# Route to display the results
@app.route('/', methods=['GET', 'POST'])
@app.route('/stock', methods=['GET'])
def index():
    batch_results = None
    error_message = None
    warning_message = None
    
    # Handle POST requests for batch analysis
    if request.method == 'POST':
        action = request.form.get('action', 'batch')
        
        if action == 'batch':
            ticker_list = request.form.get('ticker_list', '')
            if ticker_list:
                # Split the input by commas, spaces, and newlines
                tickers = re.split(r'[,\s\n]+', ticker_list)
                tickers = [t.strip().upper() for t in tickers if t.strip()]
                
                if tickers:
                    # Limit the number of tickers to process to avoid timeouts
                    MAX_TICKERS = 10
                    if len(tickers) > MAX_TICKERS:
                        tickers = tickers[:MAX_TICKERS]
                        warning_message = f"Processing only the first {MAX_TICKERS} tickers to avoid timeout. Please process the rest in another batch."
                    else:
                        warning_message = None
                        
                    logger.info(f"Processing batch request for {len(tickers)} tickers")
                    batch_results = []
                    
                    for ticker in tickers:
                        # Short delay to avoid API rate limits
                        time.sleep(0.1)
                        
                        logger.info(f"Processing ticker: {ticker}")
                        try:
                            data = fetch_financial_data(ticker)
                            
                            if 'error' in data:
                                # Skip tickers with errors
                                logger.error(f"Error retrieving data for {ticker}: {data['error']}")
                                continue
                            
                            # Create simplified result object with key metrics
                            ticker_result = process_financial_data(ticker, data)
                            if ticker_result:
                                batch_results.append(ticker_result)
                                
                        except Exception as e:
                            logger.error(f"Error processing {ticker}: {str(e)}")
                    
                    if not batch_results:
                        error_message = "Could not retrieve valid data for any of the provided tickers."
                    
                    # Apply Magic Formula ranking to batch results
                    if batch_results:
                        # Create two separate rankings (higher is better for both metrics)
                        earnings_yield_ranking = sorted(batch_results, key=lambda x: x.get('earnings_yield') if x.get('earnings_yield') is not None else -1, reverse=True)
                        roc_ranking = sorted(batch_results, key=lambda x: x.get('return_on_capital') if x.get('return_on_capital') is not None else -1, reverse=True)
                        
                        # Create a dictionary to hold the rankings
                        ey_rank_dict = {}
                        roc_rank_dict = {}
                        
                        # Assign Earnings Yield rank (1 is best)
                        for i, stock in enumerate(earnings_yield_ranking):
                            ey_rank_dict[stock['ticker']] = i + 1
                            
                        # Assign Return on Capital rank (1 is best)
                        for i, stock in enumerate(roc_ranking):
                            roc_rank_dict[stock['ticker']] = i + 1
                        
                        # Calculate combined rank and add to each stock
                        for stock in batch_results:
                            ticker = stock['ticker']
                            ey_rank = ey_rank_dict.get(ticker, len(batch_results))
                            roc_rank = roc_rank_dict.get(ticker, len(batch_results))
                            
                            # The combined rank is the sum of the two ranks (lower is better)
                            combined_rank = ey_rank + roc_rank
                            stock['magic_rank'] = combined_rank
                            stock['ey_rank'] = ey_rank
                            stock['roc_rank'] = roc_rank
                        
                        # Sort by Magic Formula rank (lower is better)
                        batch_results = sorted(batch_results, key=lambda x: x.get('magic_rank', 999))
                    
                    # Return with batch results
                    return render_template('index.html', 
                                          batch_results=batch_results, 
                                          error_message=error_message,
                                          warning_message=warning_message)
    
    # Default view - just show the form
    return render_template('index.html', error_message=error_message)

@app.route('/api/stock/<ticker>', methods=['GET'])
def get_stock_data(ticker):
    ticker = ticker.strip().upper()
    if not ticker:
        return jsonify({'error': 'No ticker provided'}), 400
    
    data = fetch_financial_data(ticker)
    if 'error' in data:
        return jsonify({'error': data['error']}), 400
    
    return jsonify(data)

# Route to get saved ticker lists
@app.route('/api/ticker-lists', methods=['GET'])
def get_ticker_lists():
    try:
        ticker_lists = TickerList.query.order_by(TickerList.name).all()
        return jsonify({
            'success': True,
            'data': [{'id': lst.id, 'name': lst.name, 'tickers': lst.tickers} for lst in ticker_lists]
        })
    except Exception as e:
        logger.error(f"Error fetching ticker lists: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

# Route to save a new ticker list
@app.route('/api/ticker-lists', methods=['POST'])
def save_ticker_list():
    try:
        data = request.json
        name = data.get('name')
        tickers = data.get('tickers')
        
        if not name or not tickers:
            return jsonify({
                'success': False,
                'error': 'Name and tickers are required'
            }), 400
        
        # Check if a list with this name already exists
        existing_list = TickerList.query.filter_by(name=name).first()
        if existing_list:
            # Update existing list
            existing_list.tickers = tickers
            db.session.commit()
            return jsonify({
                'success': True,
                'message': f'Ticker list "{name}" updated successfully',
                'list': {
                    'id': existing_list.id,
                    'name': existing_list.name,
                    'tickers': existing_list.tickers
                }
            })
        else:
            # Create new list
            new_list = TickerList(name=name, tickers=tickers)
            db.session.add(new_list)
            db.session.commit()
            return jsonify({
                'success': True,
                'message': f'Ticker list "{name}" saved successfully',
                'list': {
                    'id': new_list.id,
                    'name': new_list.name,
                    'tickers': new_list.tickers
                }
            })
    except Exception as e:
        logger.error(f"Error saving ticker list: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

# Route to delete a ticker list
@app.route('/api/ticker-lists/<int:list_id>', methods=['DELETE'])
def delete_ticker_list(list_id):
    try:
        ticker_list = TickerList.query.get_or_404(list_id)
        db.session.delete(ticker_list)
        db.session.commit()
        return jsonify({
            'success': True,
            'message': f'Ticker list "{ticker_list.name}" deleted successfully'
        })
    except Exception as e:
        logger.error(f"Error deleting ticker list: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
