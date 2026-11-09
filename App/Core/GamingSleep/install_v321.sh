#!/usr/bin/env bash
# Opt-in NEXUS 3.2.1 installer. Keeps 3.2 intact for rollback.
set -Eeuo pipefail
MODE="${1:-install}"
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
OLD="$HOME/.local/share/nexus-320-full"
NEW="$HOME/.local/share/nexus-321-full"
BIN="$HOME/.local/bin/nexus-321"
TOP="App/Modules/Top/HUD_Plugins_ViewBar/NativeQt/n3xvs_top_native.py"
CFG="$HOME/.config/nexus-320/gaming-sleep.json"
SVC="$HOME/.config/systemd/user/nexus-321-gaming.service"
AUTO="$HOME/.config/autostart/nexus-321.desktop"
LOG="$HOME/.local/state/nexus-321/logs"
mkdir -p "$HOME/.local/bin" "$HOME/.config/nexus-320" "$HOME/.config/systemd/user" "$HOME/.config/autostart" "$LOG"

stop_script() {
  python3 - "$1" <<'PY'
import os,sys,signal,time,pathlib
target=str(pathlib.Path(sys.argv[1]).resolve())
for d in pathlib.Path("/proc").iterdir():
    if not d.name.isdecimal() or int(d.name)==os.getpid():continue
    try:
        if d.stat().st_uid != os.getuid():continue
        argv=[x.decode("utf-8","replace") for x in (d/"cmdline").read_bytes().split(b"\0") if x]
        if target in argv and any(x.endswith("n3xvs_top_native.py") for x in argv):
            os.kill(int(d.name),signal.SIGUSR1)
    except (OSError,ValueError):pass
PY
}
stop_old_watcher() {
  python3 - <<'PY'
import os,pathlib,signal
for d in pathlib.Path("/proc").iterdir():
    if not d.name.isdecimal() or int(d.name)==os.getpid():continue
    try:
        if d.stat().st_uid!=os.getuid():continue
        argv=[x.decode("utf-8","replace") for x in (d/"cmdline").read_bytes().split(b"\0") if x]
        if any(x.endswith("/GamingSleep/watcher_v32.py") for x in argv):
            os.kill(int(d.name),signal.SIGTERM)
    except (OSError,ValueError):pass
PY
}

if [[ "$MODE" == rollback ]]; then
  systemctl --user disable --now nexus-321-gaming.service 2>/dev/null || true
  [[ ! -f "$NEW/$TOP" ]] || stop_script "$NEW/$TOP"
  sleep 2
  [[ ! -e "$AUTO" ]] || mv "$AUTO" "$AUTO.v321-backup"
  [[ ! -e "$CFG.v321-backup" ]] || mv "$CFG.v321-backup" "$CFG"
  if [[ -x "$HOME/.local/bin/nexus-320" ]]; then
    nohup "$HOME/.local/bin/nexus-320" >> "$LOG/rollback.log" 2>&1 </dev/null &
  fi
  echo "Rollback demandé vers NEXUS 3.2.0 (sources 3.2.1 conservées)."
  exit 0
fi
[[ "$MODE" == install ]] || { echo "Usage: bash $0 install|rollback" >&2; exit 2; }
[[ -n "${DISPLAY:-}" && "${XDG_SESSION_TYPE:-x11}" != wayland ]] || { echo "XFCE X11 requis" >&2; exit 2; }
[[ -f "$OLD/$TOP" && "$(cat "$OLD/VERSION.txt" 2>/dev/null)" == "3.2.0-GAMING-SLEEP-TEST" ]] || {
  echo "NEXUS 3.2.0 installé introuvable à $OLD. Aucun changement." >&2; exit 2;
}
if [[ ! -d "$NEW" ]]; then
  python3 "$REPO/App/Core/GamingSleep/stage_v321.py" --source "$OLD" --dest "$NEW"
fi
[[ "$(cat "$NEW/VERSION.txt")" == "3.2.1-GAMING-PANEL-TEST" ]] || exit 3
"$NEW/.venv/bin/python" -c 'import PySide6,psutil,Xlib'
"$NEW/.venv/bin/python" -m py_compile "$NEW/$TOP" "$NEW/App/Core/GamingSleep/"*.py

cat > "$BIN" <<'SH'
#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$HOME/.local/share/nexus-321-full"
export QT_QPA_PLATFORM=xcb
export HEALTHBAR_DATA_DIR="$HOME/.config/nexus-v3-hybrid"
export PYTHONPATH="$ROOT:$ROOT/Legacy/Health-and-Perfs---Navigation-Controler-Bar/src${PYTHONPATH:+:$PYTHONPATH}"
exec "$ROOT/.venv/bin/python" "$ROOT/App/Modules/Top/HUD_Plugins_ViewBar/NativeQt/n3xvs_top_native.py" --legacy "$ROOT/Legacy/Health-and-Perfs---Navigation-Controler-Bar" "$@"
SH
chmod +x "$BIN"

if [[ -f "$CFG" && ! -f "$CFG.v321-backup" ]]; then
  cp -a "$CFG" "$CFG.v321-backup"
fi
python3 - "$CFG" "$NEW/$TOP" "$BIN" <<'PY'
import json,pathlib,sys
path=pathlib.Path(sys.argv[1])
try: data=json.loads(path.read_text())
except (OSError,ValueError): data={}
data.update(enabled=True,applications=["dolphin-emu","dolphin","dolphin-emu-qt2"],
            interval=2,target_script=sys.argv[2],launcher=sys.argv[3])
path.write_text(json.dumps(data,indent=2)+"\n")
PY

cat > "$SVC" <<EOF
[Unit]
Description=NEXUS 3.2.1 Dolphin Gaming Sleep (XFCE X11)
After=graphical-session.target
[Service]
Type=simple
ExecStart=$NEW/.venv/bin/python $NEW/App/Core/GamingSleep/watcher_v321.py --config $CFG
Restart=on-failure
RestartSec=3
[Install]
WantedBy=default.target
EOF
if [[ -f "$HOME/.config/autostart/nexus-320.desktop" && ! -f "$HOME/.config/autostart/nexus-320.desktop.v321-backup" ]]; then
  mv "$HOME/.config/autostart/nexus-320.desktop" "$HOME/.config/autostart/nexus-320.desktop.v321-backup"
fi
cat > "$AUTO" <<EOF
[Desktop Entry]
Type=Application
Name=NEXUS HUD 3.2.1
Exec=$BIN
Terminal=false
OnlyShowIn=XFCE;
X-GNOME-Autostart-enabled=true
EOF

stop_old_watcher
stop_script "$OLD/$TOP"
sleep 2
nohup "$BIN" >> "$LOG/nexus.log" 2>&1 </dev/null &
sleep 3
if ! pgrep -f "$NEW/$TOP" >/dev/null; then
  echo "Échec du lancement 3.2.1 : retour à 3.2.0" >&2
  bash "$0" rollback
  exit 1
fi
systemctl --user import-environment DISPLAY XAUTHORITY 2>/dev/null || true
systemctl --user daemon-reload
systemctl --user enable --now nexus-321-gaming.service
echo "NEXUS 3.2.1 installé. Paramètres > GÉNÉRALE > MODE GAMING / VEILLE"
echo "Rollback: bash $REPO/App/Core/GamingSleep/install_v321.sh rollback"
