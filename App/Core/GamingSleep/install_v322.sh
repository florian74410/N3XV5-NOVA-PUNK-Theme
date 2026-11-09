#!/usr/bin/env bash
# Safe opt-in test upgrade for XFCE X11. Retains NEXUS 3.2/3.2.1.
set -Eeuo pipefail
MODE="${1:-install}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
SOURCE="$ROOT/Releases/NEXUS-3.2.2-FULL/Source"
[[ -f "$SOURCE/VERSION.txt" ]] || SOURCE="$ROOT/Releases/NEXUS-3.2.1-FULL/Source"
DEST="$HOME/.local/share/nexus-322-full"
LAUNCHER="$HOME/.local/bin/nexus-322"
AUTOSTART="$HOME/.config/autostart/nexus-322.desktop"
SERVICE="$HOME/.config/systemd/user/nexus-322-gaming.service"
CFG="$HOME/.config/nexus-320/gaming-sleep.json"
LOG="$HOME/.local/state/nexus-322"
TOP="App/Modules/Top/HUD_Plugins_ViewBar/NativeQt/n3xvs_top_native.py"
mkdir -p "$HOME/.local/bin" "$HOME/.config/autostart" "$HOME/.config/systemd/user" "$HOME/.config/nexus-320" "$LOG"
if [[ "$MODE" == rollback ]]; then
  systemctl --user disable --now nexus-322-gaming.service 2>/dev/null || true
  [[ -f "$AUTOSTART" ]] && mv "$AUTOSTART" "$AUTOSTART.disabled" || true
  if [[ -f "$CFG.v322-backup" ]]; then cp "$CFG.v322-backup" "$CFG"; fi
  if [[ -f "$HOME/.config/autostart/nexus-321.desktop.v322-backup" ]]; then
    mv "$HOME/.config/autostart/nexus-321.desktop.v322-backup" "$HOME/.config/autostart/nexus-321.desktop"
  fi
  echo "3.2.2 autostart/watchdog stopped. Previous settings restored."
  echo "To reopen 3.2.1: ~/.local/bin/nexus-321"
  exit 0
fi
[[ "$MODE" == install ]] || { echo "Usage: bash $0 install|rollback" >&2; exit 2; }
[[ -n "${DISPLAY:-}" && "${XDG_SESSION_TYPE:-x11}" != wayland ]] || { echo "XFCE X11 required" >&2; exit 2; }
[[ -f "$SOURCE/$TOP" && -f "$SOURCE/App/Core/GamingSleep/watcher_v322.py" ]] || { echo "3.2.2 source absent" >&2; exit 2; }
[[ ! -e "$DEST" ]] || { echo "Destination exists; refusing overwrite: $DEST" >&2; exit 2; }
VENV=""
for d in "$HOME/.local/share/nexus-321-full" "$HOME/.local/share/nexus-320-full" "$HOME/.local/share/nexus-backup-3183-gaming"; do
  if [[ -x "$d/.venv/bin/python" ]]; then VENV="$d/.venv";break;fi
done
[[ -n "$VENV" ]] || { echo "No compatible NEXUS Qt virtualenv" >&2; exit 2; }
"$VENV/bin/python" -c 'import PySide6, psutil, Xlib' || exit 2
cp -a "$SOURCE" "$DEST"
echo '3.2.2-GAMING-BOTTOM-TEST' > "$DEST/VERSION.txt"
ln -s "$VENV" "$DEST/.venv"
"$VENV/bin/python" -m py_compile "$DEST/$TOP" "$DEST/App/Core/GamingSleep/qt_bridge.py" "$DEST/App/Core/GamingSleep/watcher_v322.py"

cat > "$LAUNCHER" <<'SH'
#!/usr/bin/env bash
set -Eeuo pipefail
R="$HOME/.local/share/nexus-322-full"
export QT_QPA_PLATFORM=xcb
export HEALTHBAR_DATA_DIR="$HOME/.config/nexus-v3-hybrid"
export PYTHONPATH="$R:$R/Legacy/Health-and-Perfs---Navigation-Controler-Bar/src${PYTHONPATH:+:$PYTHONPATH}"
exec "$R/.venv/bin/python" "$R/App/Modules/Top/HUD_Plugins_ViewBar/NativeQt/n3xvs_top_native.py" --legacy "$R/Legacy/Health-and-Perfs---Navigation-Controler-Bar" "$@"
SH
chmod +x "$LAUNCHER"
[[ ! -f "$CFG" || -f "$CFG.v322-backup" ]] || cp -a "$CFG" "$CFG.v322-backup"
python3 - "$CFG" "$DEST/$TOP" "$LAUNCHER" <<'PY'
import json,pathlib,sys
p=pathlib.Path(sys.argv[1])
try: obj=json.loads(p.read_text())
except (OSError,ValueError): obj={}
obj.update(enabled=True,interval=2,applications=["dolphin-emu","dolphin","dolphin-emu-qt2"],
           target_script=sys.argv[2],launcher=sys.argv[3])
p.write_text(json.dumps(obj,indent=2)+"\n")
PY
cat > "$SERVICE" <<EOF
[Unit]
Description=NEXUS 3.2.2 Gaming Bottom-only Watcher
After=graphical-session.target
[Service]
Type=simple
ExecStart=$DEST/.venv/bin/python $DEST/App/Core/GamingSleep/watcher_v322.py --config $CFG
Restart=on-failure
RestartSec=3
[Install]
WantedBy=default.target
EOF
cat > "$AUTOSTART" <<EOF
[Desktop Entry]
Type=Application
Name=NEXUS HUD 3.2.2
Exec=$LAUNCHER
Terminal=false
OnlyShowIn=XFCE;
EOF

# Deactivate older watchers and their autostart; do not erase their code.
for v in 321 320; do
  systemctl --user disable --now "nexus-${v}-gaming.service" 2>/dev/null || true
done
if [[ -f "$HOME/.config/autostart/nexus-321.desktop" && ! -e "$HOME/.config/autostart/nexus-321.desktop.v322-backup" ]]; then
  mv "$HOME/.config/autostart/nexus-321.desktop" "$HOME/.config/autostart/nexus-321.desktop.v322-backup"
fi
# Stop only the known earlier staged HUDs, not XFCE or arbitrary Python processes.
python3 - <<'PY'
import os,pathlib,signal,time
prefixes=[str(pathlib.Path.home()/".local/share"/x/"App/Modules/Top/HUD_Plugins_ViewBar/NativeQt/n3xvs_top_native.py") for x in ("nexus-321-full","nexus-320-full")]
for d in pathlib.Path("/proc").iterdir():
    if not d.name.isdecimal() or int(d.name)==os.getpid():continue
    try:
        if d.stat().st_uid!=os.getuid():continue
        argv=[v.decode("utf-8","replace") for v in (d/"cmdline").read_bytes().split(b"\0") if v]
        if any(target in argv for target in prefixes):os.kill(int(d.name),signal.SIGTERM)
    except (OSError,ValueError):pass
PY
sleep 2
nohup "$LAUNCHER" >> "$LOG/nexus.log" 2>&1 </dev/null &
sleep 3
if ! pgrep -f "$DEST/$TOP" >/dev/null; then
  echo "NEXUS 3.2.2 failed; check $LOG/nexus.log" >&2
  exit 1
fi
systemctl --user import-environment DISPLAY XAUTHORITY 2>/dev/null || true
systemctl --user daemon-reload
systemctl --user enable --now nexus-322-gaming.service
echo "NEXUS 3.2.2 running. Dolphin => Bottom NEXUS only; exit Dolphin => Top + Bottom."
echo "Gaming switch: Paramètres > GÉNÉRALE. Rollback: bash $0 rollback"
