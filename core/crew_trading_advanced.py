import os
import asyncio
from crewai import Agent, Task, Crew, Process
from crewai.tools import tool

from tools.stock_tools import get_stock_quote, get_financial_ratios
from tools.technical_tools import get_rsi, get_sma

# 1. Definisikan LLM
llm = "gemini/gemini-1.5-pro"

# 2. Balut Python Functions kepada CrewAI Tools
@tool("Get Stock Quote")
def quote_tool(symbol: str) -> dict:
    """Berguna untuk mendapatkan harga semasa dan info asas saham. Input mesti simbol saham (contoh: '1155.KL')."""
    return get_stock_quote(symbol)

@tool("Get Fundamental Ratios")
def ratios_tool(symbol: str) -> dict:
    """Berguna untuk mendapatkan Dividend Yield, ROE, Payout Ratio, dan P/E. Input mesti simbol saham (contoh: '1155.KL')."""
    return get_financial_ratios(symbol)

@tool("Get Technical RSI")
def rsi_tool(symbol: str) -> dict:
    """Berguna untuk semak status Overbought (>70) atau Oversold (<30) saham. Input mesti simbol saham."""
    return get_rsi(symbol)

@tool("Get Technical SMA")
def sma_tool(symbol: str) -> dict:
    """Berguna untuk semak trend harga (berada di atas atau bawah SMA-50). Input mesti simbol saham."""
    return get_sma(symbol)

def analyze_stock_crew(symbol: str) -> str:
    """Jalankan Multi-Agent CrewAI Analysis"""
    
    # EJEN 1: FUNDAMENTAL
    fundamental_agent = Agent(
        role='Penganalisis Fundamental Kanan',
        goal='Menilai kekuatan kewangan dan kestabilan dividen',
        backstory='Pakar pelaburan nilai (Value Investor) yang mengutamakan dividen gaya ASB (4-7%), ROE tinggi (>15%) dan Payout Ratio selamat.',
        verbose=True,
        allow_delegation=False,
        tools=[quote_tool, ratios_tool],
        llm=llm
    )
    
    # EJEN 2: TEKNIKAL
    technical_agent = Agent(
        role='Pakar Analisis Teknikal',
        goal='Mencari titik masuk (entry point) terbaik berdasarkan pergerakan harga',
        backstory='Pakar carta yang membaca RSI (Relative Strength Index) dan SMA-50 untuk memastikan kita tidak membeli ketika harga di puncak.',
        verbose=True,
        allow_delegation=False,
        tools=[rsi_tool, sma_tool],
        llm=llm
    )
    
    # EJEN 3: PENGURUS RISIKO (DECISION MAKER)
    risk_manager = Agent(
        role='Pengurus Risiko Portfolio',
        goal='Membuat keputusan akhir (BUY, HOLD, atau WATCH) berdasarkan kedua-dua laporan dari ejen lain.',
        backstory='Pengurus dana yang konservatif. Jika fundamental bagus tetapi teknikal teruk (RSI tinggi), dia akan cadangkan HOLD/WATCH.',
        verbose=True,
        allow_delegation=False,
        llm=llm
    )
    
    # TASKS
    task_fundamental = Task(
        description=f'Cari data harga dan kewangan untuk saham {symbol}. Nilai kekuatannya mengikut ASB (Dividen, ROE, P/E). Sediakan laporan ringkas.',
        expected_output='Laporan Fundamental ringkas tentang kekuatan syarikat tersebut.',
        agent=fundamental_agent
    )
    
    task_technical = Task(
        description=f'Cari data RSI-14 dan SMA-50 untuk saham {symbol}. Sediakan laporan teknikal memberitahu status harganya (murah/mahal).',
        expected_output='Laporan Teknikal ringkas tentang status harga (Overbought/Oversold).',
        agent=technical_agent
    )
    
    task_risk = Task(
        description=f'Berdasarkan laporan Ejen Fundamental dan Teknikal mengenai {symbol}, hasilkan kesimpulan akhir: BUY, HOLD atau WATCH dengan justifikasi.',
        expected_output='Laporan akhir yang kemas dalam Bahasa Melayu dengan format bullet point dan emoji. Wajib ada kesimpulan keputusan.',
        agent=risk_manager,
        context=[task_fundamental, task_technical]
    )
    
    # BINA CREW
    crew = Crew(
        agents=[fundamental_agent, technical_agent, risk_manager],
        tasks=[task_fundamental, task_technical, task_risk],
        process=Process.sequential,
        verbose=True
    )
    
    try:
        result = crew.kickoff()
        # Handle new CrewOutput object introduced in newer CrewAI versions
        if hasattr(result, 'raw'):
            return result.raw
        return str(result)
    except Exception as e:
        return f"Ralat CrewAI untuk {symbol}: {str(e)}"
