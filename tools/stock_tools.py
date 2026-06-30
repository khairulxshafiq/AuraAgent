import yfinance as yf

def get_stock_quote(symbol: str) -> dict:
    """
    Get the real-time stock quote and basic info from Yahoo Finance.
    For Bursa Malaysia, append '.KL' (e.g. '1155.KL').
    """
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        if not info or "symbol" not in info:
            return {"error": f"No quote data found for {symbol}"}
            
        return {
            "symbol": info.get("symbol", symbol),
            "name": info.get("shortName") or info.get("longName"),
            "price": info.get("currentPrice") or info.get("regularMarketPrice") or info.get("previousClose"),
            "dayLow": info.get("dayLow"),
            "dayHigh": info.get("dayHigh"),
            "yearHigh": info.get("fiftyTwoWeekHigh"),
            "yearLow": info.get("fiftyTwoWeekLow"),
            "marketCap": info.get("marketCap"),
            "pe": info.get("trailingPE") or info.get("forwardPE"),
            "eps": info.get("trailingEps") or info.get("forwardEps")
        }
    except Exception as e:
        return {"error": str(e)}

def get_financial_ratios(symbol: str) -> dict:
    """
    Get fundamental financial ratios from Yahoo Finance.
    Returns Dividend Yield, ROE, Payout Ratio, etc.
    """
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        if not info or "symbol" not in info:
            return {"error": f"No ratios data found for {symbol}"}
            
        return {
            "symbol": symbol,
            "dividendYieldTTM": info.get("dividendYield"),
            "payoutRatioTTM": info.get("payoutRatio"),
            "returnOnEquityTTM": info.get("returnOnEquity"),
            "priceToBookRatioTTM": info.get("priceToBook"),
            "peRatioTTM": info.get("trailingPE")
        }
    except Exception as e:
        return {"error": str(e)}
