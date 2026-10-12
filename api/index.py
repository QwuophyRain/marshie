"""Vercel entry point. Vercel looks for an ASGI variable called `app` in api/*.py.

The same FastAPI app runs on the Raspberry Pi, Windows and macOS via `python marshie.py`.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.app.main import app  # noqa: E402,F401
