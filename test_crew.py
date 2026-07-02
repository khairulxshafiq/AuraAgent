import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'apps', 'aura-crewai')))

from crews.crew_trading_advanced.crew import analyze_stock_crew

def test_crew():
    print("Running analyze_stock_crew for 1155.KL...")
    result = analyze_stock_crew("1155.KL")
    print("\n--- FINAL RESULT ---")
    print(result)

if __name__ == "__main__":
    test_crew()
