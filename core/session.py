"""
core/session.py

In-memory session management for AURA SDK.
Replaces: apps/aura-brain/state/session-cache.js + shared/brain_session_client.py

Stores per-chat scrape sessions (URL, scraped content, iterations, commit state).
Sessions expire after SESSION_TTL_MINUTES (default 30 mins) of inactivity.
"""

import time
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger("aura.core.session")

SESSION_TTL_MINUTES = 30
SESSION_TTL_SECONDS = SESSION_TTL_MINUTES * 60

# In-memory store: { chat_id: SessionData }
_sessions: Dict[str, Dict[str, Any]] = {}


def _now() -> float:
    return time.time()


def _prune_expired():
    """Remove sessions older than TTL."""
    cutoff = _now() - SESSION_TTL_SECONDS
    expired = [cid for cid, s in _sessions.items() if s.get("updated_at", 0) < cutoff]
    for cid in expired:
        del _sessions[cid]
        logger.debug(f"Session expired and pruned for chat_id={cid}")


# ─── Public API ───────────────────────────────────────────────────────────────

def create_session(chat_id: str, url: str, scraped_data: Dict[str, Any]) -> None:
    """Create or overwrite a scrape session for a chat."""
    _sessions[str(chat_id)] = {
        "url": url,
        "scraped_data": scraped_data,
        "iterations": [],
        "committed": False,
        "created_at": _now(),
        "updated_at": _now(),
    }
    logger.info(f"Session created for chat_id={chat_id}, url={url}")


def get_session(chat_id: str) -> Optional[Dict[str, Any]]:
    """Get active session for a chat, or None if expired/not found."""
    _prune_expired()
    session = _sessions.get(str(chat_id))
    if not session:
        return None
    # Double-check TTL
    if _now() - session.get("updated_at", 0) > SESSION_TTL_SECONDS:
        del _sessions[str(chat_id)]
        return None
    return session


def add_iteration(
    chat_id: str,
    platform: str,
    style: str,
    rewritten: str,
    style_raw: Optional[str] = None,
    platform_raw: Optional[str] = None
) -> bool:
    """Add a rewrite iteration to the active session."""
    session = get_session(chat_id)
    if not session:
        return False
    session["iterations"].append({
        "platform": platform,
        "style": style,
        "style_raw": style_raw or style,
        "platform_raw": platform_raw or platform,
        "rewritten": rewritten,
        "created_at": _now(),
    })
    session["updated_at"] = _now()
    logger.info(f"Iteration added for chat_id={chat_id} | platform={platform} | style={style}")
    return True


def get_latest_iteration(chat_id: str) -> Optional[Dict[str, Any]]:
    """Get the most recent iteration for a chat session."""
    session = get_session(chat_id)
    if not session or not session.get("iterations"):
        return None
    return session["iterations"][-1]


def commit_session(chat_id: str) -> bool:
    """Mark session as committed (uploaded to Airtable)."""
    session = get_session(chat_id)
    if not session:
        return False
    session["committed"] = True
    session["updated_at"] = _now()
    logger.info(f"Session committed for chat_id={chat_id}")
    return True


def delete_session(chat_id: str) -> None:
    """Delete a session (after commit or explicit discard)."""
    _sessions.pop(str(chat_id), None)
    logger.info(f"Session deleted for chat_id={chat_id}")


def has_uncommitted_session(chat_id: str) -> bool:
    """Check if there's an active, uncommitted session for this chat."""
    session = get_session(chat_id)
    return session is not None and not session.get("committed", False)


def get_session_url(chat_id: str) -> Optional[str]:
    """Get the URL from the active session."""
    session = get_session(chat_id)
    return session.get("url") if session else None


def session_summary(chat_id: str) -> str:
    """Return a human-readable summary of the current session state."""
    session = get_session(chat_id)
    if not session:
        return "Tiada active session."
    url = session.get("url", "")
    iterations = len(session.get("iterations", []))
    committed = session.get("committed", False)
    status = "✅ Committed" if committed else "⏳ Pending upload"
    return f"Session: {url}\nIterations: {iterations}\nStatus: {status}"
