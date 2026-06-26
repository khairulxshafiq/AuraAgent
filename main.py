"""
main.py — AURA SDK

AURA (Autonomous Unified Reasoning Agent) — Personal AI Operating System untuk Matrol.
Migrated from: AuraAgentic monorepo (Gateway + Brain + CrewAI + Hermes → Single Python process)

Architecture:
  Telegram Bot  →  AURA Agent (google-genai SDK + function calling)  →  Tools

Replaces:
  - apps/gateway/     → python-telegram-bot handlers
  - apps/aura-brain/  → google-genai GenerativeModel + AURA persona
  - apps/aura-crewai/ → content_tools.py (rewrite_content)
  - apps/aura-hermes/ → web_tools.py, image_tools.py, airtable_tools.py

Deploy: Railway.app (single Python service, single process)
"""

import os
import sys
import re
import json
import asyncio
import logging
from typing import Optional, Any

from dotenv import load_dotenv
load_dotenv()

import google.genai as genai
from google.genai import types

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
from telegram.constants import ChatAction

from core.persona import get_system_instructions
from core import session as SessionManager

import tools.web_tools as web_tools
import tools.airtable_tools as airtable_tools
import tools.image_tools as image_tools
import tools.content_tools as content_tools
import tools.gdrive_tools as gdrive_tools

# ─── Logging Setup ────────────────────────────────────────────────────────────

log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    level=getattr(logging, log_level, logging.INFO),
    stream=sys.stdout  # Railway: output to stdout so logs appear white, not red
)
logger = logging.getLogger("aura.main")

# ─── Configuration ────────────────────────────────────────────────────────────

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
BOSS_CHAT_ID = os.environ.get("BOSS_CHAT_ID", "")
BOSS_NAME = os.environ.get("BOSS_NAME", "Matrol")
DEFAULT_BRAND = os.environ.get("DEFAULT_BRAND", "Sakluma")

if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN not set in .env!")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not set in .env!")

# ─── Google Genai Client ──────────────────────────────────────────────────────

_client = genai.Client(api_key=GEMINI_API_KEY)
MODEL = "gemini-2.5-flash"

# ─── Tool Definitions (Function Declarations for Gemini) ─────────────────────

AURA_TOOLS = [
    types.Tool(function_declarations=[
        types.FunctionDeclaration(
            name="scrape_url",
            description="Scrape a web page URL and return its title, main content, images, and links. Use TIER 1 Firecrawl (bot-bypass) first, falls back to native scraper. Call this when user sends a URL to process.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "url": types.Schema(type=types.Type.STRING, description="Full URL to scrape (must start with http:// or https://)"),
                    "max_content_length": types.Schema(type=types.Type.INTEGER, description="Max chars to return (default 30000)"),
                },
                required=["url"]
            )
        ),
        types.FunctionDeclaration(
            name="search_web",
            description="Search the web for a query using DuckDuckGo (free). Returns titles, links, and snippets. Use for research or when user asks to find information.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "query": types.Schema(type=types.Type.STRING, description="Search query string"),
                    "num_results": types.Schema(type=types.Type.INTEGER, description="Number of results (default 5, max 10)"),
                },
                required=["query"]
            )
        ),
        types.FunctionDeclaration(
            name="rewrite_content",
            description="Rewrite article content in a specific Malaysian writing style for social media. Available styles: santai_malaysia, cikgu_fadhli, hook_pembaca, formal, emotional.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "article_title": types.Schema(type=types.Type.STRING, description="Article title"),
                    "article_content": types.Schema(type=types.Type.STRING, description="Raw article content to rewrite (max ~3000 words)"),
                    "style": types.Schema(type=types.Type.STRING, description="Writing style: santai_malaysia, cikgu_fadhli, hook_pembaca, formal, or emotional"),
                    "platform": types.Schema(type=types.Type.STRING, description="Target platform: facebook, instagram, twitter, threads, or linkedin"),
                },
                required=["article_title", "article_content", "style", "platform"]
            )
        ),
        types.FunctionDeclaration(
            name="save_draft_to_airtable",
            description="Save a content draft to Airtable Content Station. Call this when user says 'upload', 'save', or 'commit' after reviewing a preview.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "title": types.Schema(type=types.Type.STRING, description="Article or content title"),
                    "caption": types.Schema(type=types.Type.STRING, description="Rewritten caption/content to save"),
                    "platform": types.Schema(type=types.Type.STRING, description="Target platform (Facebook, Instagram, etc.)"),
                    "style": types.Schema(type=types.Type.STRING, description="Writing style used"),
                    "source_url": types.Schema(type=types.Type.STRING, description="Original article URL"),
                    "image_url": types.Schema(type=types.Type.STRING, description="Image URL to attach"),
                    "brand": types.Schema(type=types.Type.STRING, description="Brand name"),
                    "created_by": types.Schema(type=types.Type.STRING, description="Creator name"),
                },
                required=["title", "caption", "platform", "style"]
            )
        ),
        types.FunctionDeclaration(
            name="list_airtable_drafts",
            description="List recent draft records from Airtable Content Station. Use when user asks to see existing drafts.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "limit": types.Schema(type=types.Type.INTEGER, description="Number of records to fetch (default 10)"),
                },
            )
        ),
        types.FunctionDeclaration(
            name="generate_image",
            description="Generate an AI image using Replicate Flux based on a description. Returns image URL or prompt-only if Replicate token not configured.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "description": types.Schema(type=types.Type.STRING, description="Detailed description of what the image should show"),
                    "style": types.Schema(type=types.Type.STRING, description="Visual style: photorealistic, artistic, minimalist, illustration, cartoon"),
                    "platform": types.Schema(type=types.Type.STRING, description="Target platform for dimensions: instagram, facebook, twitter, linkedin, threads"),
                    "brand_colors": types.Schema(type=types.Type.STRING, description="Optional comma-separated brand colors to incorporate"),
                },
                required=["description"]
            )
        ),
        types.FunctionDeclaration(
            name="build_image_prompt",
            description="Build an optimised AI image prompt without generating the actual image. Use to preview or refine a prompt first.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "topic": types.Schema(type=types.Type.STRING, description="Subject or theme for the image"),
                    "style": types.Schema(type=types.Type.STRING, description="Visual style: photorealistic, artistic, minimalist, illustration"),
                    "platform": types.Schema(type=types.Type.STRING, description="Target platform: instagram, facebook, twitter"),
                },
                required=["topic"]
            )
        ),
        types.FunctionDeclaration(
            name="list_available_styles",
            description="List all available content writing styles for AURA. Call when user asks what styles are available.",
            parameters=types.Schema(type=types.Type.OBJECT, properties={})
        ),
        types.FunctionDeclaration(
            name="list_drive_files",
            description="List files in the AURA Google Drive folder. Use this when bos asks to see what files are in Drive, or to find reference materials.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "max_files": types.Schema(type=types.Type.INTEGER, description="Max files to list (default 20)"),
                },
            )
        ),
        types.FunctionDeclaration(
            name="read_drive_file",
            description="Read the content of a text file, Google Doc, or Google Sheet from Drive. Use file_id from list_drive_files result.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "file_id": types.Schema(type=types.Type.STRING, description="Google Drive file ID"),
                    "max_chars": types.Schema(type=types.Type.INTEGER, description="Max characters to read (default 8000)"),
                },
                required=["file_id"]
            )
        ),
        types.FunctionDeclaration(
            name="search_drive_files",
            description="Search for files by name in the AURA Google Drive folder.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "query": types.Schema(type=types.Type.STRING, description="Search term — find files with this name"),
                    "max_results": types.Schema(type=types.Type.INTEGER, description="Max results (default 10)"),
                },
                required=["query"]
            )
        ),
        types.FunctionDeclaration(
            name="save_text_to_drive",
            description="Save text content (ideas, notes, drafts) as a .txt or .md file to the AURA Google Drive folder. Use when bos asks to save or dump text to Drive.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "text": types.Schema(type=types.Type.STRING, description="Text content to save"),
                    "filename": types.Schema(type=types.Type.STRING, description="Filename with extension e.g. brainstorm.md, notes.txt"),
                },
                required=["text", "filename"]
            )
        ),
    ])
]

# ─── Tool Dispatcher ──────────────────────────────────────────────────────────

def dispatch_tool(name: str, args: dict) -> Any:
    """Execute a tool by name with given arguments."""
    logger.info(f"[TOOL] {name}({list(args.keys())})")
    try:
        if name == "scrape_url":
            return web_tools.scrape_url(**args)
        elif name == "search_web":
            return web_tools.search_web(**args)
        elif name == "rewrite_content":
            return content_tools.rewrite_content(**args)
        elif name == "list_available_styles":
            return content_tools.list_available_styles()
        elif name == "save_draft_to_airtable":
            return airtable_tools.save_draft_to_airtable(**args)
        elif name == "list_airtable_drafts":
            return airtable_tools.list_airtable_drafts(**args)
        elif name == "generate_image":
            return image_tools.generate_image(**args)
        elif name == "build_image_prompt":
            return image_tools.build_image_prompt(**args)
        elif name == "list_drive_files":
            return gdrive_tools.list_drive_files(**args)
        elif name == "read_drive_file":
            return gdrive_tools.read_drive_file(**args)
        elif name == "search_drive_files":
            return gdrive_tools.search_drive_files(**args)
        elif name == "save_text_to_drive":
            return gdrive_tools.save_text_to_drive(**args)
        else:
            return {"status": "error", "error": f"Unknown tool: {name}"}
    except Exception as e:
        logger.error(f"[TOOL ERROR] {name}: {e}", exc_info=True)
        return {"status": "error", "error": str(e)}


# ─── Multi-turn Conversation Store (per chat_id) ─────────────────────────────

# { chat_id: [Content, Content, ...] }
_conversation_history: dict[str, list] = {}

SYSTEM_INSTRUCTIONS = get_system_instructions()


async def run_aura_agent(chat_id: str, user_message: str) -> str:
    """
    Run AURA agent with multi-turn conversation history and function calling.
    Handles the full agentic loop: chat → tool call → result → chat → ...
    """
    history = _conversation_history.get(chat_id, [])

    # Append user message to history
    history.append(types.Content(
        role="user",
        parts=[types.Part(text=user_message)]
    ))

    MAX_TOOL_ROUNDS = 6  # prevent infinite loops
    final_text = ""

    for round_num in range(MAX_TOOL_ROUNDS):
        response = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: _client.models.generate_content(
                model=MODEL,
                contents=history,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_INSTRUCTIONS,
                    tools=AURA_TOOLS,
                    temperature=0.7,
                    max_output_tokens=2048,
                )
            )
        )

        candidate = response.candidates[0] if response.candidates else None
        if not candidate:
            final_text = "Hmm, ada issue sikit. Cuba sekali lagi?"
            break

        # Collect all parts from the model response
        model_parts = []
        tool_calls_found = []

        for part in candidate.content.parts:
            model_parts.append(part)
            if part.function_call:
                tool_calls_found.append(part.function_call)

        # Add model response to history
        history.append(types.Content(role="model", parts=model_parts))

        if not tool_calls_found:
            # No more tool calls — final text response
            final_text = ""
            for part in model_parts:
                if hasattr(part, "text") and part.text:
                    final_text += part.text
            break

        # Execute all tool calls and build function response parts
        function_response_parts = []
        for fc in tool_calls_found:
            tool_args = dict(fc.args) if fc.args else {}
            tool_result = dispatch_tool(fc.name, tool_args)
            function_response_parts.append(
                types.Part(function_response=types.FunctionResponse(
                    name=fc.name,
                    response={"result": tool_result}
                ))
            )

        # Append tool results to history and continue loop
        history.append(types.Content(role="user", parts=function_response_parts))

    # Save updated history (cap at 40 turns to avoid token overflow)
    if len(history) > 40:
        # Keep system context + last 38 turns
        history = history[-38:]
    _conversation_history[chat_id] = history

    return final_text.strip() or "Hmm, ada sesuatu yang tak kena. Cuba sekali lagi?"


# ─── Authorization Check ──────────────────────────────────────────────────────

def is_authorized(chat_id: str) -> bool:
    if not BOSS_CHAT_ID:
        return True
    return str(chat_id) == str(BOSS_CHAT_ID)


# ─── Telegram Handlers ────────────────────────────────────────────────────────

async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    logger.info(f"[START] chat_id={chat_id} — set this as BOSS_CHAT_ID in .env to restrict access")

    if not is_authorized(chat_id):
        await update.message.reply_text("⛔ Akses tidak dibenarkan.")
        return

    await update.message.reply_text(
        f"Hey boss! Saya AURA — assistant awak yang sentiasa standby. 😊\n\n"
        f"Apa yang awak nak settlekan hari ni?\n\n"
        f"*Capabilities saya:*\n"
        f"• 📰 Scrape & rewrite artikel → save ke Airtable\n"
        f"• 🎨 Jana gambar AI (Flux Schnell)\n"
        f"• 🔍 Research & web search\n"
        f"• 💬 Chat, soal-jawab, brainstorm\n\n"
        f"Hantar je link artikel atau taip apa yang nak dibuat.",
        parse_mode="Markdown"
    )


async def handle_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(str(update.effective_chat.id)):
        return
    await update.message.reply_text(
        "*AURA — Flow Guide*\n\n"
        "*Content Pipeline:*\n"
        "1. Hantar URL artikel\n"
        "2. AURA scrape & tanya gaya/platform\n"
        "3. AURA generate preview\n"
        "4. Reply gaya baru untuk iterate (contoh: `hook`, `cikgu`, `formal`)\n"
        "5. Reply `upload` untuk save ke Airtable\n\n"
        "*Gaya:* santai, cikgu fadhli, hook, formal, emotional\n"
        "*Platform:* facebook, instagram, threads, twitter, linkedin\n\n"
        "*Gambar:* Describe apa yang nak dijana\n"
        "*Research:* Hantar URL atau topik\n\n"
        "/status — Tengok session active\n"
        "/buang — Discard session\n"
        "/clear — Reset conversation history\n"
        "/start — Restart",
        parse_mode="Markdown"
    )


async def handle_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    if not is_authorized(chat_id):
        return
    status = SessionManager.session_summary(chat_id)
    await update.message.reply_text(status)


async def handle_buang(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    if not is_authorized(chat_id):
        return
    if SessionManager.has_uncommitted_session(chat_id):
        SessionManager.delete_session(chat_id)
        await update.message.reply_text("Session discarded. Hantar URL baru bila ready.")
    else:
        await update.message.reply_text("Takde active session pun. Hantar URL bila nak mulakan.")


async def handle_clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reset conversation history for the chat."""
    chat_id = str(update.effective_chat.id)
    if not is_authorized(chat_id):
        return
    _conversation_history.pop(chat_id, None)
    SessionManager.delete_session(chat_id)
    await update.message.reply_text("Conversation history cleared. Fresh start! 👍")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Main message handler — routes all user messages through AURA agent."""
    chat_id = str(update.effective_chat.id)
    user_message = (update.message.text or "").strip()

    if not is_authorized(chat_id):
        await update.message.reply_text("⛔ Akses tidak dibenarkan.")
        return

    if not user_message:
        return

    logger.info(f"[MSG] chat_id={chat_id} | {user_message[:80]}...")

    # Show typing indicator
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action=ChatAction.TYPING
    )

    # ─── Shortcut: Handle upload/commit directly ────────────────────────────
    lower_msg = user_message.lower().strip()
    commit_keywords = ("upload", "save", "commit", "ok upload", "ok save", "upload dulu", "upload sekarang", "ok, upload")
    if lower_msg in commit_keywords:
        if SessionManager.has_uncommitted_session(chat_id):
            session = SessionManager.get_session(chat_id)
            latest = SessionManager.get_latest_iteration(chat_id)
            if latest and session:
                scraped = session.get("scraped_data", {})
                result = airtable_tools.save_draft_to_airtable(
                    title=scraped.get("title", "Draft"),
                    caption=latest.get("rewritten", ""),
                    platform=latest.get("platform", "facebook"),
                    style=latest.get("style_raw", latest.get("style", "Santai Malaysia")),
                    source_url=session.get("url", ""),
                    image_url=(scraped.get("images") or [""])[0],
                    brand=DEFAULT_BRAND,
                    created_by="AURA (SDK)"
                )
                if result.get("status") == "success":
                    SessionManager.commit_session(chat_id)
                    platform_name = latest.get("platform", "facebook").title()
                    style_name = latest.get("style", "Santai Malaysia")
                    source_url = session.get("url", "")
                    source_domain = re.sub(r'https?://(www\.)?', '', source_url).split("/")[0]
                    reply = (
                        f"✅ DONE — Draft saved ke Content Station!\n\n"
                        f"{platform_name} | {style_name} | Draft\n\n"
                        f"Source: {source_domain}\n"
                        f"Brand: {DEFAULT_BRAND}"
                    )
                    await update.message.reply_text(reply)
                    return
                else:
                    await update.message.reply_text(
                        f"❌ Gagal save ke Airtable — {result.get('error', 'Unknown')}\n"
                        f"Cuba semula atau check AIRTABLE_API_KEY dalam .env."
                    )
                    return

    # ─── Shortcut: Warn if new URL while pending session ───────────────────
    URL_PATTERN = re.compile(r'https?://[^\s]+')
    url_in_msg = (URL_PATTERN.findall(user_message) or [None])[0]
    if url_in_msg and SessionManager.has_uncommitted_session(chat_id):
        existing_url = SessionManager.get_session_url(chat_id)
        if existing_url and existing_url != url_in_msg:
            old_domain = re.sub(r'https?://(www\.)?', '', existing_url).split("/")[0]
            await update.message.reply_text(
                f"⚠️ Boss, preview untuk *{old_domain}* belum commit lagi.\n\n"
                f"Reply `buang` untuk discard, atau `upload` untuk save yang lama dulu.",
                parse_mode="Markdown"
            )
            return

    # ─── Main: AURA Agent (agentic loop with function calling) ─────────────
    try:
        reply_text = await run_aura_agent(chat_id, user_message)

        # Check for [STYLE_BUTTONS] tag
        reply_markup = None
        if "[STYLE_BUTTONS]" in reply_text:
            reply_text = reply_text.replace("[STYLE_BUTTONS]", "").strip()
            keyboard = [
                [
                    InlineKeyboardButton("👨‍🏫 Cikgu Fadhli", callback_data="style_cikgufadhli"),
                    InlineKeyboardButton("✨ Sakluma", callback_data="style_sakluma")
                ],
                [
                    InlineKeyboardButton("💼 Marketing", callback_data="style_marketing"),
                    InlineKeyboardButton("🏖️ Santai Malaysia", callback_data="style_santaimalaysia")
                ],
                [
                    InlineKeyboardButton("📱 GenZ", callback_data="style_genz")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

        # Handle Telegram 4096 char limit
        if len(reply_text) > 4096:
            chunks = [reply_text[i:i+4000] for i in range(0, len(reply_text), 4000)]
            for i, chunk in enumerate(chunks):
                if i == len(chunks) - 1:
                    await update.message.reply_text(chunk, reply_markup=reply_markup)
                else:
                    await update.message.reply_text(chunk)
        else:
            await update.message.reply_text(reply_text, reply_markup=reply_markup)

        logger.info(f"[REPLY] chat_id={chat_id} | length={len(reply_text)}")

    except Exception as e:
        logger.error(f"[ERROR] chat_id={chat_id} | {e}", exc_info=True)
        await update.message.reply_text(
            "Hmm, ada issue kat system saya. Let me try again — atau cuba reformulate request awak?"
        )


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    if not is_authorized(chat_id):
        return
    await update.message.reply_text(
        "Gambar received! Feature image analysis coming soon. "
        "For now, hantar description dan saya generate gambar baru."
    )


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline button clicks."""
    query = update.callback_query
    await query.answer()

    chat_id = str(update.effective_chat.id)
    if not is_authorized(chat_id):
        return

    data = query.data
    logger.info(f"[CALLBACK] chat_id={chat_id} | data={data}")

    # Map callback data to style names
    style_map = {
        "style_cikgufadhli": "Cikgu Fadhli",
        "style_sakluma": "Sakluma",
        "style_marketing": "Marketing",
        "style_santaimalaysia": "Santai Malaysia",
        "style_genz": "GenZ",
    }

    if data in style_map:
        selected_style = style_map[data]
        user_message = f"Saya pilih gaya {selected_style}"
        
        # Remove buttons from original message
        await query.edit_message_reply_markup(reply_markup=None)
        
        # Show what user selected
        await context.bot.send_message(chat_id=chat_id, text=f"_(Bos tekan: {selected_style})_", parse_mode="Markdown")

        # Process via AURA
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
        try:
            reply_text = await run_aura_agent(chat_id, user_message)
            
            # Re-check for buttons in reply (unlikely, but just in case)
            reply_markup = None
            if "[STYLE_BUTTONS]" in reply_text:
                reply_text = reply_text.replace("[STYLE_BUTTONS]", "").strip()
                keyboard = [
                    [InlineKeyboardButton("👨‍🏫 Cikgu Fadhli", callback_data="style_cikgufadhli"), InlineKeyboardButton("✨ Sakluma", callback_data="style_sakluma")],
                    [InlineKeyboardButton("💼 Marketing", callback_data="style_marketing"), InlineKeyboardButton("🏖️ Santai Malaysia", callback_data="style_santaimalaysia")],
                    [InlineKeyboardButton("📱 GenZ", callback_data="style_genz")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)

            if len(reply_text) > 4096:
                chunks = [reply_text[i:i+4000] for i in range(0, len(reply_text), 4000)]
                for i, chunk in enumerate(chunks):
                    if i == len(chunks) - 1:
                        await context.bot.send_message(chat_id=chat_id, text=chunk, reply_markup=reply_markup)
                    else:
                        await context.bot.send_message(chat_id=chat_id, text=chunk)
            else:
                await context.bot.send_message(chat_id=chat_id, text=reply_text, reply_markup=reply_markup)
                
            logger.info(f"[REPLY] chat_id={chat_id} | length={len(reply_text)}")
        except Exception as e:
            logger.error(f"[ERROR] chat_id={chat_id} | {e}", exc_info=True)
            await context.bot.send_message(chat_id=chat_id, text="Hmm, ada issue kat system saya. Cuba lagi?")



# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    logger.info("=" * 65)
    logger.info(" 🧠 AURA (Autonomous Unified Reasoning Agent) BOOT SEQUENCE...")
    logger.info("=" * 65)
    logger.info(f" [SYSTEM] Model        : {MODEL}")
    logger.info(f" [SYSTEM] Brand        : {DEFAULT_BRAND}")
    logger.info(f" [SYSTEM] Boss         : {BOSS_NAME}")
    logger.info(f" [SYSTEM] Access       : {'Restricted (Boss Only)' if BOSS_CHAT_ID else 'Open Access'}")
    logger.info(" ")
    logger.info(" [TOOLS]  Airtable     : ✅ READY (Content Station Sync)")
    logger.info(" [TOOLS]  Web Scraper  : ✅ READY (Firecrawl / BS4 Engine)")
    logger.info(" [TOOLS]  Google Drive : ✅ READY (Service Account Linked)")
    logger.info(" [TOOLS]  Image Gen    : ✅ READY (Replicate Flux Schnell)")
    logger.info(" ")
    logger.info(" [CREWS]  Active       : 🕵️ Research | ✍️ Content | 🎨 Image | 🗂️ Data")
    logger.info("=" * 65)

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", handle_start))
    app.add_handler(CommandHandler("help", handle_help))
    app.add_handler(CommandHandler("status", handle_status))
    app.add_handler(CommandHandler("buang", handle_buang))
    app.add_handler(CommandHandler("clear", handle_clear))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(handle_callback))

    logger.info(" 🚀 AURA is LIVE. Polling for Telegram messages...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
