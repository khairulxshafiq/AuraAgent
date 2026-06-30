import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage
from langgraph.prebuilt import create_react_agent

# Import tools yang memanggil API FMP / Alpha Vantage secara terus
from tools.stock_tools import get_stock_quote, get_financial_ratios

# 1. Definisikan Tools
tools = [get_stock_quote, get_financial_ratios]

# 2. Definisikan LLM (Pastikan GEMINI_API_KEY ada di dalam .env)
# Kita gunakan gemini-1.5-pro kerana ia stabil untuk tool calling di LangChain
llm = ChatGoogleGenerativeAI(
    model="gemini-1.5-pro",
    temperature=0.2
)

# 3. Definisikan Persona & Sistem Arahan
system_prompt = """
Anda adalah 'AURA CrewTrading Decision Agent', seorang penganalisis saham pakar yang menfokuskan pelaburan jangka panjang gaya 'ASB' (dividen & kestabilan).
Anda sentiasa menggunakan tools yang disediakan untuk mendapatkan data pasaran sebenar. JANGAN sesekali mereka cipta (hallucinate) data!

Gunakan kriteria ASB-style ini semasa menganalisis:
1. Dividend Yield (TTM): 4% - 7% adalah sihat. Lebih dari 8% mungkin 'yield trap' (bahaya).
2. ROE (Return on Equity): > 15% adalah bagus.
3. P/E Ratio: Rendah lebih baik (bandingkan dengan pasaran/sektor).
4. Payout Ratio: 40% - 70% sihat. > 90% bahaya (tidak cukup tunai untuk growth).

Tugas anda:
1. Ambil input simbol saham (contoh: 1155.KL).
2. WAJIB panggil tool 'get_stock_quote' dan 'get_financial_ratios'.
3. Buat kiraan dan tafsiran berdasarkan nilai sebenar dari API.
4. Berikan kesimpulan akhir: BUY, HOLD, atau WATCH.
5. Formatkan output dengan emoji dan perenggan yang kemas, sesuai untuk Telegram.
"""
system_message = SystemMessage(content=system_prompt)

# 4. Bina LangGraph Agent (Single Agent React Architecture)
crew_trading_agent = create_react_agent(
    model=llm,
    tools=tools,
    state_modifier=system_message
)

def analyze_stock_sync(symbol: str) -> str:
    """
    Fungsi utama yang akan dipanggil oleh Telegram Bot.
    """
    try:
        inputs = {"messages": [("user", f"Tolong analisa saham {symbol} mengikut gaya pelaburan ASB.")]}
        result = crew_trading_agent.invoke(inputs)
        return result["messages"][-1].content
    except Exception as e:
        return f"Ralat semasa menganalisis {symbol}: {str(e)}"
