#!/usr/bin/env bash
# N3XV5 2.2.5: safely update the ENTIRE unified Qt UI from the release checkout.
set -Eeuo pipefail
PACKAGE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
TARGET="$HOME/.local/share/n3xvs-hud"
STATE="$HOME/.local/state/n3xvs-hud"
PYTHON="$TARGET/.venv/bin/python"
TOP="App/Modules/Top/HUD_Plugins_ViewBar/NativeQt/n3xvs_top_native.py"
METRICS="App/Modules/Top/HUD_Plugins_ViewBar/NativeQt/n3xvs_metrics.py"
BOTTOM="App/Modules/Bottom/HUD_HomeNavBar/NativeQt/slim_style.py"
START="Linux/start.sh"
FILES=("$TOP" "$METRICS" "$BOTTOM" "$START")
[[ "$(id -u)" != 0 ]] || { echo 'Ne lance pas avec sudo.' >&2; exit 2; }
[[ -f "$TARGET/$TOP" && -x "$PYTHON" ]] || { echo 'Installation N3XV5 Unified introuvable.' >&2; exit 3; }
for f in "${FILES[@]}"; do
  [[ -f "$PACKAGE/$f" ]] || { echo "Source absente : $f" >&2; exit 4; }
done
"$PYTHON" -m py_compile "$PACKAGE/$TOP" "$PACKAGE/$METRICS" "$PACKAGE/$BOTTOM"
bash -n "$PACKAGE/$START"
python3 "$PACKAGE/Tests/test_pack.py"
python3 "$PACKAGE/Tests/test_metrics.py"
BACKUP="$STATE/backups/v225-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BACKUP"
for f in "${FILES[@]}"; do
  mkdir -p "$BACKUP/$(dirname "$f")"
  [[ ! -f "$TARGET/$f" ]] || cp -a "$TARGET/$f" "$BACKUP/$f"
done
printf '✅ Sauvegarde : %s\n' "$BACKUP"
# Stop the exact currently running unified Python process. Do not stop Firefox,
# the XFCE panel, or any unrelated app with 'python' in its command line.
"$PYTHON" - "$TARGET/$TOP" <<'PY'
import os,sys,signal,time
path=os.path.realpath(sys.argv[1]); mine=os.getpid(); pids=[]
for name in os.listdir('/proc'):
    if not name.isdigit():continue
    pid=int(name)
    if pid==mine:continue
    try:
        with open(f'/proc/{pid}/cmdline','rb') as f:argv=[a.decode('utf-8','replace') for a in f.read().split(b'\0') if a]
        if len(argv)>=2 and os.path.realpath(argv[1])==path and 'python' in os.path.basename(argv[0]):pids.append(pid)
    except (OSError,PermissionError):pass
for pid in pids:
    print('Arrêt N3XV5 Unified PID',pid)
    try:os.kill(pid,signal.SIGTERM)
    except ProcessLookupError:pass
for _ in range(50):
    if all(not os.path.exists(f'/proc/{pid}') for pid in pids):break
    time.sleep(.1)
if any(os.path.exists(f'/proc/{pid}') for pid in pids):raise SystemExit('Impossible de fermer N3XV5, mise à jour annulée')
PY
# Staged transactional replace, restoring old files on install errors.
rollback() {
  echo '❌ Erreur pendant la MAJ, restauration des sources précédentes.' >&2
  for f in "${FILES[@]}"; do
    if [[ -f "$BACKUP/$f" ]]; then cp -a "$BACKUP/$f" "$TARGET/$f"; else rm -f "$TARGET/$f"; fi
  done
}
trap rollback ERR
for f in "${FILES[@]}"; do
  mkdir -p "$TARGET/$(dirname "$f")"
  tempfile="$(mktemp "$TARGET/$(dirname "$f")/.n3xvs-update-XXXXXXXX")"
  cp -- "$PACKAGE/$f" "$tempfile"
  chmod 0644 "$tempfile"
  [[ "$f" != "$START" ]] || chmod 0755 "$tempfile"
  mv -f -- "$tempfile" "$TARGET/$f"
done
"$PYTHON" -m py_compile "$TARGET/$TOP" "$TARGET/$METRICS" "$TARGET/$BOTTOM"
bash -n "$TARGET/$START"
trap - ERR
printf '✅ N3XV5 2.2.5 installé ; sauvegarde : %s\n' "$BACKUP"
if [[ "${1:-}" != '--no-start' ]]; then
  [[ -x "$HOME/.local/bin/n3xvs-hud" ]] || { echo 'Lanceur absent : ~/.local/bin/n3xvs-hud' >&2; exit 5; }
  nohup "$HOME/.local/bin/n3xvs-hud" >/dev/null 2>&1 &
  disown || true
  echo '✅ Relance demandée (consulte ~/.local/state/n3xvs-hud/session.log si nécessaire)'
fi
