#!/usr/bin/env bash
# N3XV5 Unified: fixed real path, strict single-instance launch.
set -Eeuo pipefail
SCRIPT="$(readlink -f -- "${BASH_SOURCE[0]}")"
ROOT="$(cd -- "$(dirname -- "$SCRIPT")/.." && pwd -P)"
if [[ -z "${DISPLAY:-}" || "${XDG_SESSION_TYPE:-x11}" == "wayland" ]]; then
    echo 'N3XV5 requiert une session XFCE/X11' >&2
    exit 2
fi
if [[ ! -x "$ROOT/.venv/bin/python" ]]; then
    echo "Python N3XV5 introuvable : $ROOT/.venv/bin/python" >&2
    exit 3
fi
# Linux flock excludes second launcher and ensures only 1 application instance.
mkdir -p "$HOME/.local/state/n3xvs-hud"
exec 9>"$HOME/.local/state/n3xvs-hud/unified.lock"
if ! flock -n 9; then
    echo 'N3XV5 est déjà lancé — aucune barre supplémentaire créée.'
    exit 0
fi
export QT_QPA_PLATFORM=xcb
export HEALTHBAR_DATA_DIR="$HOME/.config/n3xvs-hud"
export PYTHONPATH="$ROOT/Legacy/Health-and-Perfs---Navigation-Controler-Bar/src${PYTHONPATH:+:$PYTHONPATH}"
exec >>"$HOME/.local/state/n3xvs-hud/session.log" 2>&1
printf '\n===== N3XV5 2.2.5 unified: %s =====\n' "$(date -Is)"
exec "$ROOT/.venv/bin/python" \
 "$ROOT/App/Modules/Top/HUD_Plugins_ViewBar/NativeQt/n3xvs_top_native.py" \
 --legacy "$ROOT/Legacy/Health-and-Perfs---Navigation-Controler-Bar" "$@"
