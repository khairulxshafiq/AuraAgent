"""
tools/content_tools.py

Content rewriting tools for AURA SDK.
Replaces: aura-crewai content_crew LLM calls
Styles: cikgu_fadhli, santai_malaysia, hook_pembaca, formal, emotional
"""

import os
import logging
from typing import Optional

import httpx

logger = logging.getLogger("aura.tools.content")

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

STYLE_PROMPTS = {
    "cikgu_fadhli": """SISTEM: Kau meniru GAYA penulisan Cikgu Fadhli (Malaysia educator style) — bukan ustaz ceramah, bukan motivator generic.

Kau adalah cikgu sekolah yang bijak relate isu semasa kepada kehidupan murid & masyarakat.

━━━━━━━━━━━━━━━━━━
⚠️ PERATURAN KRITIKAL (ANTI-HALLUCINATION)

1. JANGAN CIPTA FAKTA BARU - Semua point MESTI berpandukan isi artikel
2. JANGAN OVER-RELIGIOUS - Boleh guna "ingatlah", "renung", "hikmah" TAPI JANGAN jadi khutbah
3. LIMIT HIKMAH: MAKSIMUM 1 IDEA SAHAJA
4. GUNA TONE CIKGU MALAYSIA — Calm, teaching, reflective

━━━━━━━━━━━━━━━━━━
🎯 STRUKTUR WAJIB

[1] OPENING — "Salam cikgu-cikgu sekalian," / "Salam semua," / "Hari ini ada satu perkara yang menarik perhatian saya."
[2] CONTEXT (2-4 ayat) — Ringkaskan isi artikel FAKTUAL
[3] REFLECTION (2-3 ayat) — Kaitkan dengan kehidupan rakyat
[4] SATU HIKMAH SAHAJA (1-2 ayat)
[5] CLOSING (1-2 ayat) — Penutup lembut + nada positif

━━━━━━━━━━━━━━━━━━
✍️ GAYA BAHASA: ayat pendek, bahasa Melayu semula jadi, elak emoji dan ayat khutbah.

TUGAS: Tulis semula artikel berikut dalam gaya Cikgu Fadhli untuk platform {platform}.
Panjang: 140-200 patah perkataan.""",

    "santai_malaysia": """SISTEM: Kau adalah penulis konten gaya santai Malaysia — rakan yang best, cool, dan selalu relevan.

CIRI-CIRI WAJIB:
- Bercakap seperti kawan kepada kawan — informal, direct, real
- Guna slang Malaysia yang natural: "weh", "korang", "sumpah", "memang", "beb", "lah", "kau", "aku"
- Mulakan dengan hook yang buat orang nak terus baca
- JANGAN guna bahasa formal atau academic
- ANTI-HALLUCINATION: Semua fakta MESTI dari artikel

TUGAS: Tulis semula artikel berikut dalam gaya Santai Malaysia untuk platform {platform}.
Panjang: 120-180 patah perkataan.""",

    "hook_pembaca": """SISTEM: Kau adalah penulis viral content yang pakar dalam hook psychology.

CIRI-CIRI WAJIB:
- Ayat PERTAMA MESTI hook kuat: soalan mencabar, angka mengejutkan, atau statement kontroversi ringan
- Gunakan "curiosity gap" — beri maklumat tapi tangguhkan punchline
- Short sentences. Deliberate. Like this.
- Akhiri dengan call-to-action atau punchline yang kuat
- ANTI-HALLUCINATION: Semua fakta MESTI dari artikel

TUGAS: Tulis semula artikel berikut dalam gaya Hook Pembaca untuk platform {platform}.
Panjang: 100-160 patah perkataan. Utamakan hook dan flow.""",

    "formal": """SISTEM: Kau adalah penulis konten professional — clear, authoritative, dan credible.

CIRI-CIRI WAJIB:
- Bahasa Melayu standard, tiada slang
- Struktur jelas: intro → isi → penutup
- Fakta disampaikan dengan tepat dan neutral
- Tone: corporate, trusted, informative
- ANTI-HALLUCINATION: Semua fakta MESTI dari artikel sahaja

TUGAS: Tulis semula artikel berikut dalam gaya Formal Professional untuk platform {platform}.
Panjang: 130-190 patah perkataan.""",

    "emotional": """SISTEM: Kau adalah penulis storytelling — sentuh hati pembaca melalui empati dan realiti.

CIRI-CIRI WAJIB:
- Mulakan dengan gambaran situasi yang pembaca boleh relate
- Guna "kita", "ramai dari kita", "mungkin kau pernah rasa" untuk bina empati
- Satu momen emosi yang genuine — bukan dramatic atau lebay
- Akhiri dengan harapan atau penutup yang meaningful
- ANTI-HALLUCINATION: Semua situasi MESTI berpandukan isi artikel

TUGAS: Tulis semula artikel berikut dalam gaya Emotional Storytelling untuk platform {platform}.
Panjang: 130-190 patah perkataan.""",
}

DEFAULT_STYLE = "santai_malaysia"

STYLE_DISPLAY_NAMES = {
    "cikgu_fadhli": "Cikgu Fadhli",
    "santai_malaysia": "Santai Malaysia",
    "hook_pembaca": "Hook Pembaca",
    "formal": "Formal",
    "emotional": "Emotional",
}


def rewrite_content(
    article_title: str,
    article_content: str,
    style: str = "santai_malaysia",
    platform: str = "facebook"
) -> dict:
    """Rewrite article content in a specific Malaysian writing style for social media.

    Args:
        article_title: The article title.
        article_content: The raw article content to rewrite (max ~3000 words).
        style: Writing style — 'santai_malaysia', 'cikgu_fadhli', 'hook_pembaca', 'formal', 'emotional'.
        platform: Target platform — 'facebook', 'instagram', 'twitter', 'threads', 'linkedin'.
    """
    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    model = os.environ.get("OPENROUTER_MODEL", "google/gemini-2.5-flash")

    system_prompt_template = STYLE_PROMPTS.get(style, STYLE_PROMPTS[DEFAULT_STYLE])
    system_prompt = system_prompt_template.replace("{platform}", platform.title())

    user_message = f"Title: {article_title}\n\nContent:\n{article_content[:3000]}"

    if not api_key:
        return {
            "status": "error",
            "error": "OPENROUTER_API_KEY tidak ditemui. Set dalam .env untuk menggunakan content rewriting."
        }

    try:
        with httpx.Client(timeout=35) as client:
            resp = client.post(
                OPENROUTER_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://github.com/matrol/aura-sdk",
                },
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message}
                    ],
                    "temperature": 0.7,
                    "max_tokens": 700,
                }
            )
            resp.raise_for_status()
            rewritten = resp.json()["choices"][0]["message"]["content"].strip()

            return {
                "status": "success",
                "rewritten": rewritten,
                "style": style,
                "style_name": STYLE_DISPLAY_NAMES.get(style, style),
                "platform": platform,
                "model_used": model,
            }
    except httpx.HTTPStatusError as e:
        logger.error(f"OpenRouter HTTP error: {e.response.status_code} — {e.response.text[:200]}")
        return {"status": "error", "error": f"LLM API error: {e.response.status_code}"}
    except Exception as e:
        logger.error(f"Content rewrite error: {e}")
        return {"status": "error", "error": str(e)}


def list_available_styles() -> dict:
    """List all available content writing styles for AURA content pipeline.
    Call this when the user asks what styles are available or which style to choose.
    """
    return {
        "status": "success",
        "styles": [
            {"key": k, "name": v, "description": STYLE_PROMPTS[k][:80] + "..."}
            for k, v in STYLE_DISPLAY_NAMES.items()
        ],
        "default": DEFAULT_STYLE
    }
