import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'apps', 'aura-crewai')))

from shared.tools.stock_tools import get_stock_quote, get_financial_ratios
from shared.tools.technical_tools import get_rsi, get_sma

def test_all():
    symbol = "1155.KL"
    print(f"Testing {symbol}...")
    
    print("\n--- Stock Quote ---")
    quote = get_stock_quote(symbol)
    print(quote)
    
    print("\n--- Financial Ratios ---")
    ratios = get_financial_ratios(symbol)
    print(ratios)
    
    print("\n--- Technical RSI ---")
    rsi = get_rsi(symbol)
    print(rsi)
    
    print("\n--- Technical SMA ---")
    sma = get_sma(symbol)
    print(sma)

if __name__ == "__main__":
    test_all()
