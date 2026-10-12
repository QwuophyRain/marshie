#!/usr/bin/env bash
# macOS: double-click this file to start Marshie. (First time only: right-click > Open, then confirm.)
cd "$(dirname "$0")" || exit 1
if command -v python3 >/dev/null 2>&1; then
  python3 marshie.py "$@"
else
  echo "Python is not installed. Get it from https://www.python.org/downloads/ and double-click this file again."
fi
echo
read -r -p "Marshie has stopped. Press Enter to close this window."
