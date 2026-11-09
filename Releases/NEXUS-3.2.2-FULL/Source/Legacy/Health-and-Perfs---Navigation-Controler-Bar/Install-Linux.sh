#!/bin/sh
set -eu
cd -- "$(dirname -- "$0")"
if ! command -v python3 >/dev/null 2>&1; then
    echo 'Installez Python 3.10+ et python3-venv puis relancez cet installateur.'
    exit 1
fi
python3 scripts/install.py
