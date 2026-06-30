import yfinance as yf
import pandas as pd

def get_rsi(symbol: str) -> dict:
    """
    Get the Relative Strength Index (RSI) for a stock symbol using Yahoo Finance.
    Returns the latest RSI value indicating overbought (>70) or oversold (<30) conditions.
    """
    try:
        # Fetch 60 days of data to calculate 14-day RSI
        df = yf.Ticker(symbol).history(period="60d")
        if df.empty:
            return {"error": f"No data found for {symbol}"}
        
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        # Get the last non-NaN value
        rsi_clean = rsi.dropna()
        if rsi_clean.empty:
            return {"error": f"Not enough data to calculate RSI for {symbol}"}
            
        latest_rsi = rsi_clean.iloc[-1]
        latest_date = rsi_clean.index[-1].strftime("%Y-%m-%d")
        
        return {
            "symbol": symbol,
            "date": latest_date,
            "rsi_14_day": float(latest_rsi)
        }
    except Exception as e:
        return {"error": str(e)}

def get_sma(symbol: str) -> dict:
    """
    Get the Simple Moving Average (SMA) for a stock symbol using Yahoo Finance.
    Useful for identifying the current trend (e.g., above or below 50-day SMA).
    """
    try:
        # Fetch 100 days of data to calculate 50-day SMA
        df = yf.Ticker(symbol).history(period="100d")
        if df.empty:
            return {"error": f"No data found for {symbol}"}
        
        sma = df['Close'].rolling(window=50).mean()
        sma_clean = sma.dropna()
        
        if sma_clean.empty:
            return {"error": f"Not enough data to calculate 50-day SMA for {symbol}"}
            
        latest_sma = sma_clean.iloc[-1]
        latest_date = sma_clean.index[-1].strftime("%Y-%m-%d")
        
        return {
            "symbol": symbol,
            "date": latest_date,
            "sma_50_day": float(latest_sma)
        }
    except Exception as e:
        return {"error": str(e)}
