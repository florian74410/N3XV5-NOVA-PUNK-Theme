#!/usr/bin/env bash
# NEXUS 3.2 Macro pilot installer / reversible migration
set -Eeuo pipefail
MODE="${1:-}"
SRC="${HOME}/Téléchargements/NEXUS-3.2-TEST"
DEV="${HOME}/Téléchargements/NEXUS-3.2-DEV"
OLD="${HOME}/.local/share/nexus-318-full"
NEW="${HOME}/.local/share/nexus-320-full"
BACKUP="${HOME}/.local/share/nexus-backup-3183-gaming"
OLD_LAUNCHER="${HOME}/.local/bin/nexus-318"
NEW_LAUNCHER="${HOME}/.local/bin/nexus-320"
AUTOSTART="${HOME}/.config/autostart/nexus-318.desktop"
STATE="${HOME}/.local/state/nexus-320-gaming"
CONFIG="${HOME}/.config/nexus-320/gaming-sleep.json"
PY="${BACKUP}/.venv/bin/python"
TOP="App/Modules/Top/HUD_Plugins_ViewBar/NativeQt/n3xvs_top_native.py"
mkdir -p "${STATE}" "${HOME}/.local/bin" "${HOME}/.config/nexus-320"

pids_for() {
  local script="$1"
  python3 - "$script" <<'PY'
import os,sys
target=sys.argv[1].encode()
for ent in os.scandir("/proc"):
    if not ent.name.isdigit() or int(ent.name)==os.getpid(): continue
    try:
        data=open(f"/proc/{ent.name}/cmdline","rb").read().split(b"\0")
        uid=os.stat(f"/proc/{ent.name}").st_uid
    except (PermissionError,FileNotFoundError,ProcessLookupError): continue
    if uid == os.getuid() and target in data:
        print(ent.name)
PY
}
stop_exact() {
  local script="$1" pid i
  mapfile -t ps < <(pids_for "$script")
  for pid in "${ps[@]}"; do
    echo "SIGTERM NEXUS PID=$pid"
    kill -TERM "$pid" || true
  done
  for i in {1..30}; do
    mapfile -t ps < <(pids_for "$script")
    (("${#ps[@]}"==0)) && return 0
    sleep .4
  done
  echo "Refus de forcer l'arrêt: ${ps[*]}" >&2
  return 1
}

restore() {
  echo "Arrêt pilote 3.2…"
  if [[ -f "$NEW/$TOP" ]]; then stop_exact "$NEW/$TOP"; fi
  if [[ -e "$BACKUP" ]]; then
    if [[ -e "$OLD" ]]; then echo "Conflit: ancien dossier déjà présent" >&2; exit 1; fi
    mv "$BACKUP" "$OLD"
  fi
  [[ -f "${AUTOSTART}.gaming-backup" ]] && mv "${AUTOSTART}.gaming-backup" "$AUTOSTART"
  [[ -f "${OLD_LAUNCHER}.gaming-backup" ]] && mv "${OLD_LAUNCHER}.gaming-backup" "$OLD_LAUNCHER"
  # Keep new files for diagnosis; they have no autostart enabled.
  [[ -x "$OLD_LAUNCHER" ]] && "$OLD_LAUNCHER" >> "$STATE/rollback.log" 2>&1 &
  echo "Retour à la 3.1.8.3 demandé. Vérifier NEXUS et XFCE."
}

install() {
  [[ -n "${DISPLAY:-}" ]] || { echo "Lancer depuis XFCE X11" >&2; exit 2; }
  [[ "$(cat "$SRC/VERSION.txt" 2>/dev/null)" == '3.2.0-GAMING-SLEEP-TEST' ]] || { echo "Staging 3.2 manquant" >&2; exit 2; }
  [[ -f "$SRC/$TOP" && -f "$SRC/App/Core/GamingSleep/qt_bridge.py" ]] || { echo "Staging incomplet" >&2; exit 2; }
  [[ -f "$OLD/$TOP" && -x "$OLD/.venv/bin/python" && -x "$OLD_LAUNCHER" ]] || { echo "3.1.8.3 existante non reconnue" >&2; exit 2; }
  [[ ! -e "$BACKUP" && ! -e "$NEW" && ! -e "$NEW_LAUNCHER" ]] || { echo "Déjà installé ou sauvegarde existante. Ne pas écraser." >&2; exit 2; }
  echo "Préparation sans impact sur le bureau…"
  cp -a "$SRC" "$NEW"
  python3 -m py_compile "$NEW/$TOP" "$NEW/App/Core/GamingSleep/qt_bridge.py"
  # Refuse to proceed without a healthy Python environment
  "$OLD/.venv/bin/python" -c 'import PySide6,psutil,Xlib'
  echo "Arrêt propre 3.1.8.3…"
  stop_exact "$OLD/$TOP" || { rm -rf "$NEW"; exit 1; }
  mv "$OLD" "$BACKUP"
  ln -s "$BACKUP/.venv" "$NEW/.venv"
  [[ ! -f "$AUTOSTART" ]] || mv "$AUTOSTART" "${AUTOSTART}.gaming-backup"
  mv "$OLD_LAUNCHER" "${OLD_LAUNCHER}.gaming-backup"
  cat > "$NEW_LAUNCHER" <<'SH'
#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$HOME/.local/share/nexus-320-full"
export QT_QPA_PLATFORM=xcb
export HEALTHBAR_DATA_DIR="$HOME/.config/nexus-v3-hybrid"
export PYTHONPATH="$ROOT:$ROOT/Legacy/Health-and-Perfs---Navigation-Controler-Bar/src${PYTHONPATH:+:$PYTHONPATH}"
exec "$ROOT/.venv/bin/python" "$ROOT/App/Modules/Top/HUD_Plugins_ViewBar/NativeQt/n3xvs_top_native.py" --legacy "$ROOT/Legacy/Health-and-Perfs---Navigation-Controler-Bar" "$@"
SH
  chmod +x "$NEW_LAUNCHER"
  cp "$DEV/App/Core/GamingSleep/watcher_v32.py" "$NEW/App/Core/GamingSleep/watcher_v32.py"
  cat > "$CONFIG" <<EOF
{
  "enabled": false,
  "applications": ["dolphin-emu", "dolphin", "dolphin-emu-qt2"],
  "interval": 2,
  "target_script": "$NEW/$TOP",
  "launcher": "$NEW_LAUNCHER"
}
EOF
  echo "Lancement de la 3.2 (veille automatique désactivée pour vérifier le bureau)…"
  nohup "$NEW_LAUNCHER" >> "$STATE/nexus.log" 2>&1 < /dev/null &
  sleep 5
  mapfile -t ps < <(pids_for "$NEW/$TOP")
  if (("${#ps[@]}"==0)); then
    echo "Le lancement 3.2 a échoué. Retour arrière…" >&2
    tail -25 "$STATE/nexus.log" || true
    restore
    exit 1
  fi
  echo "NEXUS 3.2 actif: PID ${ps[*]}. Observer les barres. Activer le watcher dans une deuxième étape."
  echo "Rollback: bash $0 rollback"
}
case "$MODE" in
  install) install;;
  rollback) restore;;
  *) echo "Usage: bash $0 {install|rollback}";exit 2;;
esac
