import os
import httpx
from dotenv import load_dotenv

load_dotenv()

# Gunakan kunci yang disediakan oleh pengguna jika tiada dalam .env
ALPHA_VANTAGE_KEY = os.getenv("ALPHA_VANTAGE_API_KEY", "FJBZV988DSVIWAA2")
FMP_KEY = os.getenv("FMP_API_KEY", "lClKyUztSgQiUHeZDRwLxlGQLmH8AqwL")

def get_stock_quote(symbol: str) -> dict:
    """
    Get the real-time stock quote from Financial Modeling Prep (FMP).
    For Bursa Malaysia, append '.KL' (e.g. '1155.KL').
    """
    url = f"https://financialmodelingprep.com/api/v3/quote/{symbol}?apikey={FMP_KEY}"
    try:
        response = httpx.get(url, timeout=10.0)
        data = response.json()
        if data and isinstance(data, list) and len(data) > 0:
            info = data[0]
            return {
                "symbol": info.get("symbol"),
                "name": info.get("name"),
                "price": info.get("price"),
                "changesPercentage": info.get("changesPercentage"),
                "dayLow": info.get("dayLow"),
                "dayHigh": info.get("dayHigh"),
                "yearHigh": info.get("yearHigh"),
                "yearLow": info.get("yearLow"),
                "marketCap": info.get("marketCap"),
                "pe": info.get("pe"),
                "eps": info.get("eps")
            }
        return {"error": f"No quote data found for {symbol}"}
    except Exception as e:
        return {"error": str(e)}

def get_financial_ratios(symbol: str) -> dict:
    """
    Get fundamental financial ratios from FMP.
    Returns Dividend Yield, ROE, Payout Ratio, etc.
    """
    url = f"https://financialmodelingprep.com/api/v3/ratios-ttm/{symbol}?apikey={FMP_KEY}"
    try:
        response = httpx.get(url, timeout=10.0)
        data = response.json()
        if data and isinstance(data, list) and len(data) > 0:
            ratios = data[0]
            return {
                "symbol": symbol,
                "dividendYieldTTM": ratios.get("dividendYieldTTM"),
                "payoutRatioTTM": ratios.get("payoutRatioTTM"),
                "returnOnEquityTTM": ratios.get("returnOnEquityTTM"),
                "priceToBookRatioTTM": ratios.get("priceToBookRatioTTM"),
                "peRatioTTM": ratios.get("peRatioTTM")
            }
        return {"error": f"No ratios data found for {symbol}"}
    except Exception as e:
        return {"error": str(e)}
