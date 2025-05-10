"""
Stock Price Prediction Module using Machine Learning

This module provides functionality to predict stock prices based on historical data.
It uses scikit-learn to implement a regression model that forecasts future price movements.
"""

import logging
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

def create_features(data):
    """
    Create features for stock price prediction model.
    
    Args:
        data (pd.DataFrame): DataFrame with historical price data
        
    Returns:
        pd.DataFrame: DataFrame with engineered features
    """
    # Make a copy to avoid modifying the original data
    df = data.copy()
    
    # Basic features from price history
    # Percentage changes over different time periods
    df['return_1d'] = df['Close'].pct_change(1)
    df['return_5d'] = df['Close'].pct_change(5)
    df['return_10d'] = df['Close'].pct_change(10)
    df['return_20d'] = df['Close'].pct_change(20)
    
    # Moving averages
    df['ma5'] = df['Close'].rolling(window=5).mean()
    df['ma10'] = df['Close'].rolling(window=10).mean()
    df['ma20'] = df['Close'].rolling(window=20).mean()
    df['ma50'] = df['Close'].rolling(window=50).mean()
    
    # Volatility features
    df['volatility_5d'] = df['return_1d'].rolling(window=5).std()
    df['volatility_10d'] = df['return_1d'].rolling(window=10).std()
    df['volatility_20d'] = df['return_1d'].rolling(window=20).std()
    
    # Price relationships
    df['close_to_ma5'] = df['Close'] / df['ma5']
    df['close_to_ma10'] = df['Close'] / df['ma10']
    df['close_to_ma20'] = df['Close'] / df['ma20']
    df['close_to_ma50'] = df['Close'] / df['ma50']
    
    # Volume features
    if 'Volume' in df.columns:
        df['volume_ma5'] = df['Volume'].rolling(window=5).mean()
        df['volume_ma10'] = df['Volume'].rolling(window=10).mean()
        df['volume_change'] = df['Volume'].pct_change(1)
    
    # Drop rows with NaN values caused by rolling calculations
    df = df.dropna()
    
    return df

def prepare_target(data, forecast_period=30):
    """
    Prepare target variable for prediction.
    
    Args:
        data (pd.DataFrame): DataFrame with historical price data
        forecast_period (int): Number of days ahead to predict
        
    Returns:
        tuple: X features, y target
    """
    # Create target: future price change over the forecast period
    data['future_return'] = data['Close'].pct_change(forecast_period).shift(-forecast_period)
    
    # Separate features and target
    X = data.drop(['future_return', 'Close', 'Open', 'High', 'Low', 'Adj Close'], axis=1, errors='ignore')
    y = data['future_return']
    
    # Drop rows with NaN values in target
    mask = ~y.isna()
    return X[mask], y[mask]

def train_prediction_model(historical_data, forecast_period=30):
    """
    Train a model to predict stock price movement.
    
    Args:
        historical_data (pd.DataFrame): DataFrame with historical OHLCV data
        forecast_period (int): Number of days to forecast
        
    Returns:
        object: Trained prediction model
    """
    try:
        if historical_data.empty or len(historical_data) < 60:
            logger.warning("Insufficient historical data for prediction")
            return None
        
        # Create features from historical data
        df_features = create_features(historical_data)
        
        # Prepare target variable
        X, y = prepare_target(df_features, forecast_period)
        
        if len(X) < 30:  # Need at least 30 samples to train a reasonable model
            logger.warning("Not enough processed data points for prediction")
            return None
        
        # Split into training and validation sets
        X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.2, random_state=42)
        
        # Create a model pipeline with preprocessing
        model = Pipeline([
            ('scaler', StandardScaler()),
            ('regressor', Ridge(alpha=1.0))
        ])
        
        # Train the model
        model.fit(X_train, y_train)
        
        # Log model performance
        val_score = model.score(X_val, y_val)
        logger.info(f"Model R² score on validation: {val_score:.4f}")
        
        return model
    
    except Exception as e:
        logger.error(f"Error training prediction model: {str(e)}")
        return None

def calculate_long_term_indicators(historical_data):
    """
    Calculate indicators that are particularly useful for long-term investors.
    
    Args:
        historical_data (pd.DataFrame): DataFrame with historical OHLCV data
        
    Returns:
        dict: Long-term investment indicators
    """
    try:
        if historical_data is None or historical_data.empty or len(historical_data) < 100:
            return None
            
        # Create a copy to avoid modifying the original data
        df = historical_data.copy()
        
        # 1. Calculate longer-term moving averages (50, 100, 200 days)
        df['ma50'] = df['Close'].rolling(window=50).mean()
        df['ma100'] = df['Close'].rolling(window=100).mean()
        if len(df) >= 200:
            df['ma200'] = df['Close'].rolling(window=200).mean()
        else:
            df['ma200'] = None
            
        # 2. Golden Cross / Death Cross detection
        # Golden Cross: 50-day MA crosses above 200-day MA (bullish)
        # Death Cross: 50-day MA crosses below 200-day MA (bearish)
        if len(df) >= 200:
            df['golden_cross'] = (df['ma50'] > df['ma200']) & (df['ma50'].shift(1) <= df['ma200'].shift(1))
            df['death_cross'] = (df['ma50'] < df['ma200']) & (df['ma50'].shift(1) >= df['ma200'].shift(1))
            recent_golden_cross = df['golden_cross'].iloc[-100:].any()
            recent_death_cross = df['death_cross'].iloc[-100:].any()
        else:
            recent_golden_cross = None
            recent_death_cross = None
            
        # 3. Relative strength compared to market (assume last 100 days)
        # Simplified version - in real implementation would compare to S&P 500 or other benchmark
        start_price = df['Close'].iloc[-100] if len(df) >= 100 else df['Close'].iloc[0]
        end_price = df['Close'].iloc[-1]
        percent_change = ((end_price / start_price) - 1) * 100
        
        # 4. Volatility calculation for long-term (100 day)
        long_term_volatility = df['Close'].pct_change().rolling(window=100).std() * (252 ** 0.5)  # Annualized
        current_volatility = long_term_volatility.iloc[-1] if not long_term_volatility.empty else None
        
        # 5. Price-to-moving average ratios (over/under historical means)
        current_price = df['Close'].iloc[-1]
        price_to_ma50 = current_price / df['ma50'].iloc[-1] if not pd.isna(df['ma50'].iloc[-1]) else None
        price_to_ma200 = current_price / df['ma200'].iloc[-1] if not pd.isna(df['ma200'].iloc[-1]) else None
        
        # 6. Trend strength (using linear regression slope)
        # This shows if price movement has momentum in either direction
        from scipy import stats
        if len(df) >= 100:
            x = np.arange(100)
            y = df['Close'].iloc[-100:].values
            slope, _, r_value, _, _ = stats.linregress(x, y)
            trend_strength = r_value**2  # R-squared value
            trend_direction = "Upward" if slope > 0 else "Downward"
        else:
            trend_strength = None
            trend_direction = None
        
        # 7. Determine if current price is near 52-week high or low
        if len(df) >= 252:  # Approximately one trading year
            year_high = df['Close'].iloc[-252:].max()
            year_low = df['Close'].iloc[-252:].min()
            pct_from_high = ((year_high - current_price) / year_high) * 100
            pct_from_low = ((current_price - year_low) / year_low) * 100
        else:
            year_high = df['Close'].max()
            year_low = df['Close'].min()
            pct_from_high = ((year_high - current_price) / year_high) * 100
            pct_from_low = ((current_price - year_low) / year_low) * 100
            
        # 8. Calculate drawdowns (peak to trough declines)
        rolling_max = df['Close'].cummax()
        drawdowns = (df['Close'] / rolling_max - 1.0) * 100
        max_drawdown = drawdowns.min()
        current_drawdown = drawdowns.iloc[-1]
        
        # Return all indicators
        return {
            'recent_golden_cross': recent_golden_cross,
            'recent_death_cross': recent_death_cross,
            'percent_change_100d': round(percent_change, 2),
            'long_term_volatility': round(current_volatility * 100, 2) if current_volatility is not None else None,
            'price_to_ma50': round(price_to_ma50, 2) if price_to_ma50 is not None else None,
            'price_to_ma200': round(price_to_ma200, 2) if price_to_ma200 is not None else None,
            'trend_strength': round(trend_strength, 2) if trend_strength is not None else None,
            'trend_direction': trend_direction,
            'year_high': year_high,
            'year_low': year_low,
            'pct_from_high': round(pct_from_high, 2),
            'pct_from_low': round(pct_from_low, 2),
            'max_drawdown': round(max_drawdown, 2),
            'current_drawdown': round(current_drawdown, 2)
        }
    except Exception as e:
        logger.error(f"Error calculating long-term indicators: {str(e)}")
        return None

def predict_price_movement(ticker, historical_data, forecast_period=30):
    """
    Predict future price movement for a stock.
    
    Args:
        ticker (str): Stock ticker symbol
        historical_data (pd.DataFrame): DataFrame with historical OHLCV data
        forecast_period (int): Number of days ahead to predict
        
    Returns:
        dict: Prediction results including predicted return and confidence
    """
    try:
        # Calculate long-term indicators
        long_term_data = calculate_long_term_indicators(historical_data)
        
        # Train model on historical data
        model = train_prediction_model(historical_data, forecast_period)
        
        if model is None:
            logger.warning(f"Could not create prediction model for {ticker}")
            prediction_result = {
                'prediction': 'Unknown',
                'predicted_return': None, 
                'confidence': None,
                'forecast_period': forecast_period
            }
        else:
            # Create features for the most recent data
            df_features = create_features(historical_data)
            
            # Get the latest data point with all features
            latest_features = df_features.iloc[-1:].drop(['Close', 'Open', 'High', 'Low', 'Adj Close'], axis=1, errors='ignore')
            
            # Make prediction
            predicted_return = model.predict(latest_features)[0]
            
            # Determine prediction confidence based on feature importance
            # Since we're using Ridge regression, we can't directly access feature importance
            # Instead, use the model's explained variance on validation set as a proxy for confidence
            confidence = min(0.95, max(0.2, abs(predicted_return) * 2))  # Scale confidence based on magnitude of prediction
            
            # Create a prediction label
            if predicted_return > 0.05:
                prediction = 'Strong Bullish'
            elif predicted_return > 0.02:
                prediction = 'Bullish'
            elif predicted_return > -0.02:
                prediction = 'Neutral'
            elif predicted_return > -0.05:
                prediction = 'Bearish'
            else:
                prediction = 'Strong Bearish'
            
            # Calculate predicted price
            current_price = historical_data['Close'].iloc[-1]
            predicted_price = current_price * (1 + predicted_return)
            
            # Format the prediction as a percentage
            formatted_return = f"{predicted_return * 100:.1f}%"
            formatted_confidence = f"{confidence * 100:.0f}%"
            
            prediction_result = {
                'prediction': prediction,
                'predicted_return': formatted_return,
                'confidence': formatted_confidence,
                'forecast_period': forecast_period,
                'current_price': current_price,
                'predicted_price': predicted_price
            }
        
        # Create a long-term investment recommendation
        long_term_recommendation = None
        long_term_factors = []
        
        if long_term_data:
            # Collect positive long-term factors
            positive_factors = []
            negative_factors = []
            
            # Check for Golden Cross (very bullish long-term signal)
            if long_term_data.get('recent_golden_cross'):
                positive_factors.append("Recent Golden Cross detected (50-day MA crossed above 200-day MA)")
            
            # Check for Death Cross (very bearish long-term signal)
            if long_term_data.get('recent_death_cross'):
                negative_factors.append("Recent Death Cross detected (50-day MA crossed below 200-day MA)")
            
            # Check price relative to moving averages
            if long_term_data.get('price_to_ma50', 0) > 1.05:
                positive_factors.append(f"Price is {((long_term_data['price_to_ma50'] - 1) * 100):.1f}% above 50-day MA")
            elif long_term_data.get('price_to_ma50', 0) < 0.95:
                negative_factors.append(f"Price is {((1 - long_term_data['price_to_ma50']) * 100):.1f}% below 50-day MA")
                
            if long_term_data.get('price_to_ma200', 0) > 1.05:
                positive_factors.append(f"Price is {((long_term_data['price_to_ma200'] - 1) * 100):.1f}% above 200-day MA")
            elif long_term_data.get('price_to_ma200', 0) < 0.95:
                negative_factors.append(f"Price is {((1 - long_term_data['price_to_ma200']) * 100):.1f}% below 200-day MA")
            
            # Check 100-day performance
            if long_term_data.get('percent_change_100d', 0) > 10:
                positive_factors.append(f"Strong 100-day performance: +{long_term_data['percent_change_100d']}%")
            elif long_term_data.get('percent_change_100d', 0) < -10:
                negative_factors.append(f"Weak 100-day performance: {long_term_data['percent_change_100d']}%")
            
            # Check volatility
            if long_term_data.get('long_term_volatility', 100) < 20:
                positive_factors.append(f"Low volatility: {long_term_data['long_term_volatility']}%")
            elif long_term_data.get('long_term_volatility', 0) > 40:
                negative_factors.append(f"High volatility: {long_term_data['long_term_volatility']}%")
            
            # Check trend strength
            if long_term_data.get('trend_strength', 0) > 0.7 and long_term_data.get('trend_direction') == "Upward":
                positive_factors.append(f"Strong upward trend (R²: {long_term_data['trend_strength']})")
            elif long_term_data.get('trend_strength', 0) > 0.7 and long_term_data.get('trend_direction') == "Downward":
                negative_factors.append(f"Strong downward trend (R²: {long_term_data['trend_strength']})")
            
            # Check proximity to 52-week high/low
            if long_term_data.get('pct_from_high', 100) < 5:
                positive_factors.append(f"Near 52-week high (within {long_term_data['pct_from_high']}%)")
            elif long_term_data.get('pct_from_low', 0) < 10:
                negative_factors.append(f"Near 52-week low (within {long_term_data['pct_from_low']}% of bottom)")
            
            # Check drawdown
            if long_term_data.get('current_drawdown', -100) > -5:
                positive_factors.append(f"Minimal current drawdown: {long_term_data['current_drawdown']}%")
            elif long_term_data.get('current_drawdown', 0) < -20:
                negative_factors.append(f"Significant current drawdown: {long_term_data['current_drawdown']}%")
            
            # Determine long-term recommendation based on factors count
            if len(positive_factors) >= 3 and len(positive_factors) > len(negative_factors) * 2:
                long_term_recommendation = "Strong Long-Term Buy"
            elif len(positive_factors) > len(negative_factors):
                long_term_recommendation = "Long-Term Buy"
            elif len(negative_factors) >= 3 and len(negative_factors) > len(positive_factors) * 2:
                long_term_recommendation = "Long-Term Avoid"
            elif len(negative_factors) > len(positive_factors):
                long_term_recommendation = "Long-Term Caution"
            else:
                long_term_recommendation = "Long-Term Neutral"
            
            # Combine positive and negative factors
            long_term_factors = positive_factors + negative_factors
        
        # Add long-term analysis to the prediction result
        prediction_result.update({
            'long_term_recommendation': long_term_recommendation,
            'long_term_factors': long_term_factors,
            'long_term_data': long_term_data
        })
        
        return prediction_result
    
    except Exception as e:
        logger.error(f"Error predicting price for {ticker}: {str(e)}")
        return {
            'prediction': 'Error',
            'predicted_return': None,
            'confidence': None,
            'forecast_period': forecast_period
        }