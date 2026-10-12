#!/usr/bin/env bash
# Raspberry Pi, Linux and macOS (Terminal):  ./start.sh          or   ./start.sh kiosk
cd "$(dirname "$0")" || exit 1
if command -v python3 >/dev/null 2>&1; then PY=python3; elif command -v python >/dev/null 2>&1; then PY=python; else
  echo "Python is not installed. Get it from https://www.python.org/downloads/ (Raspberry Pi OS: sudo apt install python3 python3-venv python3-pip)"
  exit 1
fi
exec "$PY" marshie.py "$@"
