"""Optional "bigger brain" (a paid AI service). Off by default: Marshie works fully offline without it.

Marshie always looks in her own knowledge first. Only when she is not sure does she ask the AI, and only if a teacher
has turned it on. The easy way to do that is the "Paid AI" tab of the Teacher panel. Computers that are set up by hand
can use LLM_PROVIDER, LLM_API_KEY, LLM_MODEL and LLM_BASE_URL in .env instead (the Teacher panel wins when both are set).

  anthropic -> Claude API       (default model: claude-haiku-5-5)
  openai    -> any OpenAI-compatible service: OpenAI, OpenRouter, Groq, Gemini, or a free one on this computer
               such as Ollama (http://localhost:11434/v1) or LM Studio.
Uses only the standard library, so there is nothing extra to install.
"""
from __future__ import annotations

import ipaddress
import json
import re
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

from . import config, i18n

PROVIDERS = ("anthropic", "openai")
DEFAULT_MODEL = {"anthropic": "claude-haiku-5-5", "openai": "gpt-4o-mini"}
DEFAULT_LIMIT = 300
KEY_OK = re.compile(r"[\x21-\x7e]{8,300}")           # printable ASCII only: a pasted newline must never reach a header

# What the Teacher panel offers. "model" is only a suggestion the teacher can change.
PRESETS = [
    {"id": "anthropic", "label": "Claude (Anthropic)", "provider": "anthropic", "base_url": "", "model": "claude-haiku-5-5",
     "needs_key": True, "key_example": "sk-ant-…", "where": "console.anthropic.com"},
    {"id": "openai", "label": "OpenAI (ChatGPT)", "provider": "openai", "base_url": "https://api.openai.com/v1", "model": "gpt-4o-mini",
     "needs_key": True, "key_example": "sk-…", "where": "platform.openai.com"},
    {"id": "openrouter", "label": "OpenRouter (many models, one key)", "provider": "openai", "base_url": "https://openrouter.ai/api/v1",
     "model": "", "needs_key": True, "key_example": "sk-or-…", "where": "openrouter.ai"},
    {"id": "groq", "label": "Groq", "provider": "openai", "base_url": "https://api.groq.com/openai/v1",
     "model": "", "needs_key": True, "key_example": "gsk_…", "where": "console.groq.com"},
    {"id": "gemini", "label": "Google Gemini", "provider": "openai", "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
     "model": "", "needs_key": True, "key_example": "AIza…", "where": "aistudio.google.com"},
    {"id": "ollama", "label": "Ollama on this computer (free, no key)", "provider": "openai", "base_url": "http://localhost:11434/v1",
     "model": "", "needs_key": False, "key_example": "", "where": "ollama.com"},
    {"id": "custom", "label": "Another OpenAI-style service", "provider": "openai", "base_url": "",
     "model": "", "needs_key": True, "key_example": "", "where": ""},
]

SYSTEM = (
    "You are {name}, a cheerful, gentle young marshmallow helper who talks with children at {school} during "
    "their STEAM week celebration in Ghana. Use simple, warm words a child aged 6 to 14 understands. "
    "Answer in at most three short sentences. Use the FACTS below when they help; they come from the school's "
    "own teachers and students. If you are not sure, say so kindly and invite the child to teach you the answer. "
    "Never ask for or repeat private details (full names with addresses, phone numbers, passwords). "
    "Refuse anything unsafe or unkind in a friendly way and suggest asking a teacher. Do not use emojis or markdown."
)


def system_prompt(lang: str = "en") -> str:
    text = SYSTEM.format(name=config.BOT_NAME, school=config.SCHOOL_NAME)
    lang = i18n.clean(lang)
    if lang != "en":
        language = i18n.name(lang)
        text += (f" The child is talking in {language}, so always reply in {language}, in simple, correct {language} a child understands. "
                 f"The FACTS may be written in English: use them, but answer in {language}. Keep names such as {config.SCHOOL_NAME}, "
                 "Ghana and Twi words as they are.")
    return text


# --------------------------------------------------------------------------- settings
def is_local(base_url: str) -> bool:
    """A service on this computer or this school network does not need a key."""
    host = (urllib.parse.urlparse(base_url or "").hostname or "").lower()
    if not host:
        return False
    if host == "localhost" or host.endswith(".local"):
        return True
    try:
        ip = ipaddress.ip_address(host)
        return ip.is_loopback or ip.is_private
    except ValueError:
        return False


def needs_key(provider: str, base_url: str) -> bool:
    return provider == "anthropic" or not is_local(base_url)


def resolve(saved: dict | None = None) -> dict:
    """The settings Marshie uses right now. What a teacher saved in the Teacher panel wins over .env."""
    saved = saved if isinstance(saved, dict) else {}
    if saved.get("provider") in PROVIDERS:
        cfg = {"provider": saved["provider"], "key": str(saved.get("key") or ""), "model": str(saved.get("model") or ""),
               "base_url": str(saved.get("base_url") or ""), "source": "admin",
               "daily_limit": int(saved.get("daily_limit") or DEFAULT_LIMIT)}
        paused = saved.get("enabled") is False
    else:
        cfg = {"provider": config.LLM_PROVIDER, "key": config.LLM_API_KEY, "model": config.LLM_MODEL,
               "base_url": config.LLM_BASE_URL, "source": "env", "daily_limit": DEFAULT_LIMIT}
        paused = False
    ready = cfg["provider"] in PROVIDERS and (bool(cfg["key"]) or not needs_key(cfg["provider"], cfg["base_url"]))
    if not ready and cfg["source"] == "env":
        cfg["source"] = "none"
    cfg["on"] = ready and not paused
    cfg["paused"] = ready and paused
    cfg["model"] = cfg["model"] or DEFAULT_MODEL.get(cfg["provider"], "")
    return cfg


def provider(cfg: dict | None = None) -> str:
    cfg = cfg or resolve()
    return cfg["provider"] if cfg.get("on") else ""


def describe(cfg: dict | None = None) -> dict:
    cfg = cfg or resolve()
    return {"enabled": bool(cfg.get("on")), "provider": cfg["provider"] if cfg.get("on") else None,
            "model": cfg["model"] if cfg.get("on") else None, "source": cfg.get("source", "none"),
            "paused": bool(cfg.get("paused")), "used_today": used_today(), "daily_limit": cfg.get("daily_limit", DEFAULT_LIMIT)}


def key_hint(key: str) -> str:
    return ("…" + key[-4:]) if len(key) >= 12 else ("saved" if key else "")


# --------------------------------------------------------------------------- daily limit (a guard against a surprise bill)
_lock = threading.Lock()
_usage = {"day": "", "n": 0}


def _today() -> str:
    return time.strftime("%Y-%m-%d")


def used_today() -> int:
    with _lock:
        return _usage["n"] if _usage["day"] == _today() else 0


def _take(limit: int) -> bool:
    with _lock:
        if _usage["day"] != _today():
            _usage["day"], _usage["n"] = _today(), 0
        if _usage["n"] >= limit:
            return False
        _usage["n"] += 1
        return True


# --------------------------------------------------------------------------- talking to the service
class LLMError(Exception):
    """An error with words a teacher can act on."""


def _post(url: str, headers: dict, payload: dict) -> dict:
    req = urllib.request.Request(url, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json", **headers}, method="POST")
    with urllib.request.urlopen(req, timeout=25) as resp:
        return json.loads(resp.read().decode())


def _friendly(exc: Exception, key: str) -> str:
    if isinstance(exc, urllib.error.HTTPError):
        try:
            detail = exc.read().decode("utf-8", "replace")[:300]
        except Exception:
            detail = ""
        if key:
            detail = detail.replace(key, "…")
        if exc.code in (401, 403):
            return "The service did not accept this key. Check that you copied all of it, and that the key is switched on."
        if exc.code == 404:
            return "The service does not know that model name or web address. Check the model name and the address."
        if exc.code == 429:
            return "The key is fine, but the account has run out of credit or is asking too fast. Check the account's billing page."
        m = re.search(r'"message"\s*:\s*"([^"]{3,200})"', detail)
        return f"The service said no ({exc.code}). " + (m.group(1) if m else "Check the model name.")
    if isinstance(exc, urllib.error.URLError):
        return "I could not reach the service. Is this computer online, and is the web address right?"
    if isinstance(exc, (TimeoutError, OSError)):
        return "The service took too long to answer. Try again in a moment."
    return "The service sent something I did not understand. Check the model name and web address."


def _call(cfg: dict, system: str, turns: list[dict], max_tokens: int) -> str:
    """One request. Raises an exception on any failure; callers turn it into words."""
    if cfg["provider"] == "anthropic":
        while turns and turns[0]["role"] != "user":
            turns.pop(0)
        data = _post("https://api.anthropic.com/v1/messages",
                     {"x-api-key": cfg["key"], "anthropic-version": "2023-06-01"},
                     {"model": cfg["model"], "max_tokens": max_tokens, "system": system, "messages": turns})
        return "".join(b.get("text", "") for b in data.get("content", [])).strip()
    base = (cfg["base_url"] or "https://api.openai.com/v1").rstrip("/")
    headers = {"Authorization": f"Bearer {cfg['key']}"} if cfg["key"] else {}
    data = _post(f"{base}/chat/completions", headers,
                 {"model": cfg["model"], "max_tokens": max_tokens, "temperature": 0.4,
                  "messages": [{"role": "system", "content": system}, *turns]})
    return (data["choices"][0]["message"]["content"] or "").strip()


def ask(question: str, facts: list[str], history: list[dict] | None = None, cfg: dict | None = None, lang: str = "en") -> str | None:
    """Returns Marshie's answer, or None if the AI is off, over its daily limit, or fails (the caller falls back kindly)."""
    cfg = cfg or resolve()
    if not provider(cfg):
        return None
    if not _take(int(cfg.get("daily_limit") or DEFAULT_LIMIT)):
        print("[marshie] AI daily limit reached; using local knowledge only")
        return None
    system = system_prompt(lang)
    if facts:
        system += "\n\nFACTS:\n" + "\n".join(f"- {f}" for f in facts[:5])
    turns = [{"role": h["role"], "content": h["content"][:600]} for h in (history or [])[-6:]
             if h.get("role") in ("user", "assistant") and h.get("content")]
    turns.append({"role": "user", "content": question[:600]})
    try:
        return _call(cfg, system, turns, 300) or None
    except Exception as exc:
        print(f"[marshie] AI unavailable, using local knowledge only: {_friendly(exc, cfg['key'])}")
        return None


def translate(text: str, target: str, cfg: dict | None = None) -> str | None:
    """Translate a short text (a child's question, or one of Marshie's answers) into French, Spanish, German or English.
    Returns None when the AI is off, over its daily limit, or fails; the caller then falls back to what she knows."""
    cfg = cfg or resolve()
    text = " ".join((text or "").split())
    if not text or not provider(cfg):
        return None
    if not _take(int(cfg.get("daily_limit") or DEFAULT_LIMIT)):
        print("[marshie] AI daily limit reached; not translating")
        return None
    language = i18n.name(target)
    system = (f"You translate short texts for a children's school chatbot. Translate the user's text into {language}. "
              "Keep names such as Ecole Ronsard, Marshie, Ghana and Twi words unchanged. Do not answer the text and do not explain; "
              "reply with the translation only, with no quotation marks.")
    try:
        out = _call(cfg, system, [{"role": "user", "content": text[:1200]}], 500)
    except Exception as exc:
        print(f"[marshie] translation unavailable: {_friendly(exc, cfg['key'])}")
        return None
    return out.strip().strip('"\u201c\u201d') or None


def test(cfg: dict) -> dict:
    """Try the settings with one tiny question. Never counts against the daily limit."""
    try:
        reply = _call(cfg, "You are a friendly helper for school children. Reply in one short sentence.",
                      [{"role": "user", "content": "Say hello to the children of the school."}], 60)
    except Exception as exc:
        return {"ok": False, "message": _friendly(exc, cfg["key"])}
    if not reply:
        return {"ok": False, "message": "The service answered with nothing. Check the model name."}
    return {"ok": True, "message": "It works. The service answered.", "reply": reply[:200]}
