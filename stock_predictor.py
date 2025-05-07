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
        # Train model on historical data
        model = train_prediction_model(historical_data, forecast_period)
        
        if model is None:
            logger.warning(f"Could not create prediction model for {ticker}")
            return {
                'prediction': 'Unknown',
                'predicted_return': None, 
                'confidence': None,
                'forecast_period': forecast_period
            }
        
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
        
        return {
            'prediction': prediction,
            'predicted_return': formatted_return,
            'confidence': formatted_confidence,
            'forecast_period': forecast_period,
            'current_price': current_price,
            'predicted_price': predicted_price
        }
    
    except Exception as e:
        logger.error(f"Error predicting price for {ticker}: {str(e)}")
        return {
            'prediction': 'Error',
            'predicted_return': None,
            'confidence': None,
            'forecast_period': forecast_period
        }