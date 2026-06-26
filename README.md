# AURA SDK — Personal AI Operating System

**AURA** (Autonomous Unified Reasoning Agent) — rebuilt from scratch using **Google Antigravity SDK**.

Migrated from: `AuraAgentic` monorepo (6 services, 4 Railway apps, multiple ports)  
Now: **1 Python file. 1 Railway app. 100% live on Telegram.**

---

## Struktur Projek

```
AuraAgent/
├── main.py                    # ✅ Entrypoint — Telegram Bot + AURA Agent
├── requirements.txt           # Python dependencies
├── .env                       # API Keys (jangan commit!)
├── .env.example               # Template untuk reference
├── Procfile                   # Railway deployment
├── start.sh                   # Local startup script
│
├── core/
│   ├── persona.py             # AURA Persona Kernel (migrated dari persona-kernel.md)
│   └── session.py             # In-memory session (replaces Brain session-cache.js)
│
└── tools/
    ├── web_tools.py           # Scrape (Firecrawl TIER1 + BS4 TIER2) + DuckDuckGo search
    ├── airtable_tools.py      # Save drafts ke Airtable Content Station
    ├── image_tools.py         # Generate images via Replicate Flux
    └── content_tools.py       # Rewrite content (5 styles: santai, cikgu, hook, formal, emotional)
```

---

## Cara Mula (Local)

```bash
cd ~/Desktop/AuraAgent

# 1. Copy dan isi .env
cp .env.example .env
# Edit .env dengan keys anda

# 2. Run
bash start.sh
```

---

## Environment Variables

| Key | Required | Description |
|-----|----------|-------------|
| `GEMINI_API_KEY` | ✅ | Google AI Studio key (AURA brain) |
| `TELEGRAM_BOT_TOKEN` | ✅ | Token dari @BotFather |
| `OPENROUTER_API_KEY` | ✅ | Untuk content rewriting |
| `AIRTABLE_API_KEY` | ✅ | Untuk save drafts |
| `AIRTABLE_BASE_ID` | ✅ | Airtable Base ID |
| `FIRECRAWL_API_KEY` | ⭐ | TIER 1 scraper (bypass bot protection) |
| `REPLICATE_API_TOKEN` | ⭐ | Untuk generate images |
| `BOSS_CHAT_ID` | 🔒 | Optional: restrict bot to Matrol only |

---

## Content Pipeline Flow

```
Matrol → Telegram → AURA → scrape_url() → rewrite_content(style, platform)
                                        → Preview reply ke Matrol
Matrol: "upload" → save_draft_to_airtable() → ✅ DONE
```

### Writing Styles
- `santai_malaysia` — Casual Malaysian (default)
- `cikgu_fadhli` — Educator/reflective style
- `hook_pembaca` — Viral hook psychology
- `formal` — Professional corporate
- `emotional` — Storytelling/empathy

---

## Deploy ke Railway

```bash
# 1. Install Railway CLI
npm install -g @railway/cli

# 2. Login dan deploy
railway login
railway init
railway up

# 3. Set environment variables di Railway dashboard
# (copy dari .env, jangan deploy .env file)
```

---

## Capabilities (vs AuraAgentic Lama)

| Feature | AuraAgentic | AURA SDK |
|---------|------------|----------|
| Services | 6 (Gateway, Brain×2, CrewAI×3, Hermes) | 1 |
| Ports | 3000, 3001, 3002, 5000, 8003, 8004, 8005 | None (bot polling) |
| Article Scrape → Airtable | ✅ | ✅ |
| 3-Mode Content (preview/commit/oneshot) | ✅ | ✅ |
| Image Generation | ✅ (Replicate) | ✅ (Replicate) |
| Web Research | ✅ (SerpAPI) | ✅ (DuckDuckGo free) |
| Persona (AURA PA) | ✅ | ✅ |
| Session Management | Brain server | In-memory |
| Firecrawl TIER 1 | ✅ | ✅ |
| Deploy cost | 4+ Railway services | 1 Railway service |

---

*"Saya bukan chatbot. Saya AURA — assistant awak yang faham, yang ingat, yang selesaikan."*
