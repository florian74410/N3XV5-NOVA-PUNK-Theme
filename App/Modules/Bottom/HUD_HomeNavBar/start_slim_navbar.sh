#!/usr/bin/env bash
# Launch original NovaBar 0.8.2.2 BottomDock with N3XV5 slim visuals.
set -Eeuo pipefail
ROOT="$HOME/N3XV5-NATIVE-V2"
LEGACY="$ROOT/Legacy/Health-and-Perfs---Navigation-Controler-Bar"
MODULE="$ROOT/App/Modules/Bottom/HUD_HomeNavBar/NativeQt/n3xvs_bottom_slim.py"
PYTHON="$ROOT/.venv/bin/python"
[[ -n "$DISPLAY" ]] || { echo "Cette version requiert XFCE/X11 (DISPLAY absent)." >&2; exit 2; }
[[ -f "$LEGACY/src/healthbar/bottom_dock.py" ]] || { echo "Moteur historique introuvable : $LEGACY" >&2; exit 3; }
[[ -f "$MODULE" ]] || { echo "Module N3XV5 introuvable : $MODULE" >&2; exit 4; }
[[ -x "$PYTHON" ]] || { echo "Environnement Qt introuvable : $PYTHON" >&2; exit 5; }

# Only close the old standalone dock, never generic Python/Qt or the N3XV5 TopBar.
if command -v wmctrl >/dev/null 2>&1; then
  wmctrl -c 'NovaBar · CYBER NEXUS · Cockpit inférieur' 2>/dev/null || true
fi
export PYTHONPATH="$LEGACY/src"
export HEALTHBAR_DATA_DIR="$HOME/.config/health-perfs-bar"
exec "$PYTHON" "$MODULE"
