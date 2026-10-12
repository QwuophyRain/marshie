"""Optional OFFLINE speech for any computer (Piper for talking, Vosk for listening).

Both are optional. When they're not installed (e.g. on Vercel) the browser's own speech is used instead.
Install with:  python marshie.py voice
"""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import threading
from collections import OrderedDict
from pathlib import Path

from . import config

_cache: "OrderedDict[str, bytes]" = OrderedDict()
_cache_lock = threading.Lock()
_vosk_model = None
_vosk_lock = threading.Lock()


# ----------------------------------------------------------------------------- talking (Piper)
def _piper_cmd() -> list[str] | None:
    if shutil.which("piper"):
        return ["piper"]
    try:
        import importlib.util
        if importlib.util.find_spec("piper"):
            return [sys.executable, "-m", "piper"]
    except Exception:
        pass
    return None


def tts_available() -> bool:
    return bool(_piper_cmd()) and Path(config.PIPER_MODEL).is_file()


def synthesize(text: str, length_scale: float = 1.25) -> bytes | None:
    """Text -> WAV bytes. A slower length_scale is paired with a pitch raise in the browser,
    which together make the voice sound like a young girl instead of a robot."""
    text = " ".join(text.split())[:700]
    if not text or not tts_available():
        return None
    key = hashlib.sha1(f"{text}|{length_scale}|{config.PIPER_MODEL}".encode()).hexdigest()
    with _cache_lock:
        if key in _cache:
            _cache.move_to_end(key)
            return _cache[key]
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "say.wav"
        cmd = _piper_cmd() + ["--model", config.PIPER_MODEL, "--output_file", str(out),
                              "--length-scale", str(length_scale)]
        try:
            subprocess.run(cmd, input=text.encode("utf-8"), check=True, capture_output=True, timeout=60)
            wav = out.read_bytes()
        except Exception as exc:
            print(f"[marshie] piper failed: {exc}")
            return None
    with _cache_lock:
        _cache[key] = wav
        while len(_cache) > 64:
            _cache.popitem(last=False)
    return wav


# ----------------------------------------------------------------------------- listening (Vosk)
def stt_available() -> bool:
    try:
        import importlib.util
        return bool(importlib.util.find_spec("vosk")) and Path(config.VOSK_MODEL).is_dir()
    except Exception:
        return False


def transcribe(pcm16_mono_16k: bytes) -> str:
    """Raw little-endian 16-bit mono PCM at 16 kHz -> text."""
    global _vosk_model
    import vosk                                         # imported lazily: only the Pi has it
    vosk.SetLogLevel(-1)
    with _vosk_lock:
        if _vosk_model is None:
            _vosk_model = vosk.Model(config.VOSK_MODEL)
        rec = vosk.KaldiRecognizer(_vosk_model, 16000)
        step = 8000
        for i in range(0, len(pcm16_mono_16k), step):
            rec.AcceptWaveform(pcm16_mono_16k[i:i + step])
        return (json.loads(rec.FinalResult()).get("text") or "").strip()


def capabilities() -> dict:
    return {"tts_server": tts_available(), "stt_server": stt_available()}
