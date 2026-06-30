import os
import httpx
from dotenv import load_dotenv

load_dotenv()

ALPHA_VANTAGE_KEY = os.getenv("ALPHA_VANTAGE_API_KEY", "FJBZV988DSVIWAA2")

def get_rsi(symbol: str) -> dict:
    """
    Get the Relative Strength Index (RSI) for a stock symbol from Alpha Vantage.
    Returns the latest RSI value indicating overbought (>70) or oversold (<30) conditions.
    """
    url = f"https://www.alphavantage.co/query?function=RSI&symbol={symbol}&interval=daily&time_period=14&series_type=close&apikey={ALPHA_VANTAGE_KEY}"
    try:
        response = httpx.get(url, timeout=10.0)
        data = response.json()
        if "Technical Analysis: RSI" in data:
            # Get the first date key (latest)
            latest_date = list(data["Technical Analysis: RSI"].keys())[0]
            latest_rsi = data["Technical Analysis: RSI"][latest_date]["RSI"]
            return {
                "symbol": symbol,
                "date": latest_date,
                "rsi_14_day": float(latest_rsi)
            }
        return {"error": data.get("Note") or data.get("Information") or f"No RSI data found for {symbol}"}
    except Exception as e:
        return {"error": str(e)}

def get_sma(symbol: str) -> dict:
    """
    Get the Simple Moving Average (SMA) for a stock symbol from Alpha Vantage.
    Useful for identifying the current trend (e.g., above or below 50-day SMA).
    """
    url = f"https://www.alphavantage.co/query?function=SMA&symbol={symbol}&interval=daily&time_period=50&series_type=close&apikey={ALPHA_VANTAGE_KEY}"
    try:
        response = httpx.get(url, timeout=10.0)
        data = response.json()
        if "Technical Analysis: SMA" in data:
            latest_date = list(data["Technical Analysis: SMA"].keys())[0]
            latest_sma = data["Technical Analysis: SMA"][latest_date]["SMA"]
            return {
                "symbol": symbol,
                "date": latest_date,
                "sma_50_day": float(latest_sma)
            }
        return {"error": data.get("Note") or data.get("Information") or f"No SMA data found for {symbol}"}
    except Exception as e:
        return {"error": str(e)}
