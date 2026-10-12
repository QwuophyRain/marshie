"""Settings, read from environment variables (or a .env file on the Raspberry Pi)."""
from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]          # backend/
PROJECT_ROOT = ROOT.parent                          # repo root
IS_VERCEL = bool(os.environ.get("VERCEL"))


def _load_dotenv() -> None:
    """Tiny .env loader so we don't need python-dotenv."""
    for candidate in (PROJECT_ROOT / ".env", ROOT / ".env"):
        if candidate.is_file():
            for line in candidate.read_text(encoding="utf-8-sig").splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_dotenv()


def env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def env_path(name: str, default: Path) -> Path:
    """A folder or file setting. Relative paths count from the project folder, wherever Marshie was started."""
    raw = env(name)
    if not raw:
        return default
    path = Path(raw).expanduser()
    return path if path.is_absolute() else PROJECT_ROOT / path


BOT_NAME = env("BOT_NAME", "Marshie") or "Marshie"
# Older copies of Marshie wrote "our school" into .env; treat that like "not set".
SCHOOL_NAME = env("SCHOOL_NAME") if env("SCHOOL_NAME").lower() not in ("", "our school") else "Ecole Ronsard"
EVENT_NAME = env("EVENT_NAME", "STEAM Program 2026")
SCHOOL_URL = env("SCHOOL_URL", "https://ecole-ronsard.com/")

# What Marshie says first. {name} and {school} are filled in. Teachers can change it in the Teacher panel.
DEFAULT_GREETING = (
    "Hello! My name is {name}, your friendly educative chatbot for the {school} STEAM "
    "(Science, Technology, English, Agriculture & Arts, and Mathematics) Program 2026. "
    "How may I be of assistance?"
)
GREETING = env("GREETING") or DEFAULT_GREETING

ADMIN_PIN = env("ADMIN_PIN", "2468")
PIN_IS_DEFAULT = ADMIN_PIN == "2468"
# Signs teacher sessions. A blank or copied-from-the-example key must never be trusted as a secret.
_key = env("SECRET_KEY")
SECRET_KEY = _key if _key and not _key.lower().startswith("change-me") else "marshie-" + ADMIN_PIN

# The school colours (read from the logo): teal, a button yellow, a pink and a green. Teachers can change them.
DEFAULT_THEME = {"primary": "#045870", "button": "#fae240", "highlight": "#e80075", "success": "#74bd54"}


def _hex(name: str, fallback: str) -> str:
    v = env(name)
    return v if len(v) == 7 and v.startswith("#") and all(c in "0123456789abcdefABCDEF" for c in v[1:]) else fallback


THEME = {
    "primary": _hex("THEME_PRIMARY", DEFAULT_THEME["primary"]),
    "button": _hex("THEME_BUTTON", DEFAULT_THEME["button"]),
    "highlight": _hex("THEME_HIGHLIGHT", DEFAULT_THEME["highlight"]),
    "success": _hex("THEME_SUCCESS", DEFAULT_THEME["success"]),
}

# How to say words the browser voice gets wrong. "Written=How to say it;Other=Say it". Only used for speaking.
_DEFAULT_SAY = "Ecole=Ay-kol;École=Ay-kol;Ronsard=Ron-sar"
SPEECH_FIXES = {
    k.strip(): v.strip()
    for k, _, v in (p.partition("=") for p in (_DEFAULT_SAY + ";" + env("SPEECH_FIXES")).split(";"))
    if k.strip() and v.strip()
}

LLM_PROVIDER = env("LLM_PROVIDER").lower()
LLM_API_KEY = env("LLM_API_KEY")
LLM_MODEL = env("LLM_MODEL")
LLM_BASE_URL = env("LLM_BASE_URL")

KV_URL = env("KV_REST_API_URL") or env("UPSTASH_REDIS_REST_URL")
KV_TOKEN = env("KV_REST_API_TOKEN") or env("UPSTASH_REDIS_REST_TOKEN")

# Where mutable state lives. Vercel's filesystem is read-only except /tmp.
DATA_DIR = env_path("DATA_DIR", Path("/tmp/marshie") if IS_VERCEL else PROJECT_ROOT / "data")
STATE_FILE = DATA_DIR / "state.json"

SEED_DIR = ROOT / "app" / "data"
CUSTOM_SEED_DIR = SEED_DIR / "custom"      # drop exported JSON here to ship taught knowledge with a deploy

PIPER_MODEL = str(env_path("PIPER_MODEL", PROJECT_ROOT / "voices" / "en_US-amy-low.onnx"))
VOSK_MODEL = str(env_path("VOSK_MODEL", PROJECT_ROOT / "voices" / "vosk-model-small-en-us-0.15"))

FRONTEND_DIST = PROJECT_ROOT / "frontend" / "dist"

# Pictures, sound and other files teachers add. Vercel has no disk of its own, so files go to the KV store there
# and must stay small (Upstash accepts about 1 MB per value and Vercel about 4.5 MB per request).
MEDIA_DIR = env_path("MEDIA_DIR", DATA_DIR / "media")
_default_mb = 3 if IS_VERCEL else 40


def _mb(name: str, default: float) -> int:
    try:
        return int(float(env(name) or default) * 1024 * 1024)
    except ValueError:
        return int(default * 1024 * 1024)


MAX_MEDIA_BYTES = _mb("MAX_MEDIA_MB", _default_mb)
MAX_KV_MEDIA_BYTES = 600 * 1024

# How sure Marshie must be before answering from her own knowledge (BM25 + overlap, 0..1).
CONFIDENT = 0.55
UNSURE = 0.45
