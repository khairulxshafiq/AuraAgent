# scripts/test_gemini_key.py
"""Simple test to verify GEMINI_API_KEY works using raw HTTP request.
It loads .env, sends a minimal prompt, and prints the full response text.
"""
import os
from dotenv import load_dotenv
import httpx

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise SystemExit("❌ GEMINI_API_KEY not set")

model_name = "gemini-2.5-flash"
prompt = "Reply with the word: PONG"

url = f"https://generativelanguage.googleapis.com/v1/models/{model_name}:generateContent?key={api_key}"
payload = {
    "contents": [{"role": "user", "parts": [{"text": prompt}]}],
    "generationConfig": {"temperature": 0.0, "maxOutputTokens": 50},
}

response = httpx.post(url, json=payload, timeout=30.0)
response.raise_for_status()
data = response.json()
# Extract text response
if "candidates" in data and data["candidates"]:
    text = "".join(part.get("text", "") for part in data["candidates"][0].get("content", {}).get("parts", []))
    print("✅ Full Response:", text)
else:
    print("⚠️ No content returned")
