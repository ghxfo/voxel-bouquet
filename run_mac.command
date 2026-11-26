#!/bin/bash
cd "$(dirname "$0")"
if ! command -v python3 >/dev/null 2>&1; then
  echo ""
  echo "  Python 3 is not installed on this Mac."
  echo "  Install it from https://www.python.org/downloads/ and run this file again."
  echo ""
  read -p "  Press Enter to close..."
  exit 1
fi
echo ""
echo "  Getting things ready (the first time can take a minute)..."
python3 -m pip install --disable-pip-version-check -q --user -r requirements.txt 2>/dev/null \
  || python3 -m pip install --disable-pip-version-check -q --user --break-system-packages -r requirements.txt
echo "  Opening the bouquet..."
python3 voxel_bouquet.py "$@"
