#!/usr/bin/env bash
# N3XV5 unified 2.2.5 exactly one TOP and one BOTTOM. User-session only; limited sudo for Turbo helper.
set -Eeuo pipefail
PACKAGE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
TARGET="$HOME/.local/share/n3xvs-hud"
STATE="$HOME/.local/state/n3xvs-hud"
CONFIG="$HOME/.config/n3xvs-hud"
AUTOSTART="$HOME/.config/autostart/n3xvs-hud.desktop"
APPDESKTOP="$HOME/.local/share/applications/n3xvs-hud.desktop"
BIN="$HOME/.local/bin/n3xvs-hud"
LEGACY="Legacy/Health-and-Perfs---Navigation-Controler-Bar"
HELPER='/usr/local/libexec/n3xvs-hud-turbo'
STAMP="$(date +%Y%m%d-%H%M%S)"
BACKUPS="$STATE/backups/$STAMP"
STAGE="$(mktemp -d "$HOME/.local/share/.n3xvs-new.XXXXXXXX")"
OLD_RUNTIME=''
ACTIVATED=0

if [[ "$(id -u)" == 0 ]]; then echo 'Ne lance pas cet installateur avec sudo.' >&2; exit 2; fi
if [[ -z "${DISPLAY:-}" || "${XDG_SESSION_TYPE:-x11}" == 'wayland' ]]; then
  echo 'Lance depuis ta session XFCE/X11.' >&2; exit 2
fi
for bin in python3 git; do command -v "$bin" >/dev/null || { echo "Commande manquante : $bin" >&2; exit 3; }; done
mkdir -p "$STATE" "$CONFIG" "$BACKUPS" "$HOME/.config/autostart" \
  "$HOME/.local/share/applications" "$HOME/.local/bin"
cleanup() { [[ ! -d "$STAGE" ]] || rm -rf -- "$STAGE"; }
rollback() {
  echo 'Échec installation : tentative de retour au runtime précédent.' >&2
  if (( ACTIVATED )); then
    if [[ -d "$TARGET" ]]; then mv "$TARGET" "$BACKUPS/failed-new-runtime"; fi
    if [[ -n "$OLD_RUNTIME" && -d "$OLD_RUNTIME" ]]; then mv "$OLD_RUNTIME" "$TARGET"; fi
  fi
}
trap cleanup EXIT
trap rollback ERR

# Stage and validate EVERYTHING first, before stopping the existing bars.
cp -a "$PACKAGE/App" "$PACKAGE/Linux" "$STAGE/"
cp -a "$PACKAGE/uninstall.sh" "$STAGE/uninstall.sh"
chmod 755 "$STAGE/Linux/start.sh" "$STAGE/uninstall.sh"
mkdir -p "$STAGE/Legacy"
LEGACY_SRC=''
for path in "$HOME/N3XV5-NATIVE-V2/$LEGACY" "$TARGET/$LEGACY"; do
  if [[ -f "$path/src/healthbar/app.py" ]]; then LEGACY_SRC="$path"; break; fi
done
if [[ -n "$LEGACY_SRC" ]]; then
  echo "Réutilisation du moteur historique : $LEGACY_SRC"
  cp -a "$LEGACY_SRC" "$STAGE/$LEGACY"
else
  git clone --depth 1 --branch 0.8.2.2REDBLACK \
    https://github.com/florian74410/Health-and-Perfs---Navigation-Controler-Bar.git \
    "$STAGE/$LEGACY"
fi
rm -rf -- "$STAGE/$LEGACY/.git"
python3 -m py_compile "$STAGE/App/Modules/Top/HUD_Plugins_ViewBar/NativeQt/n3xvs_top_native.py" \
  "$STAGE/App/Modules/Bottom/HUD_HomeNavBar/NativeQt/slim_style.py" "$STAGE/App/Modules/Top/HUD_Plugins_ViewBar/NativeQt/n3xvs_metrics.py" "$STAGE/Linux/stop_legacy.py"
python3 "$PACKAGE/Tests/test_pack.py"
python3 "$PACKAGE/Tests/test_metrics.py"

# Archive conflicting autostart files and application shortcut only when moving
# to the new release; the ordinary xfce4-panel is deliberately untouched.
for file in "$HOME/.config/autostart/health-perfs-bar.desktop" \
            "$HOME/.config/autostart/n3xvs-hud.desktop" \
            "$APPDESKTOP" "$BIN"; do
  if [[ -e "$file" || -L "$file" ]]; then
    cp -a -- "$file" "$BACKUPS/$(basename "$file").previous"
  fi
done

# Stop only N3XV5 test/NovaBar launchers using exact argv matches, never pkill -f.
echo 'Arrêt ciblé des barres de test et de l’ancien N3XV5…'
# Prefer Python with Xlib to close orphan windows whose argv is just "python -".
STOP_PY="python3"
for candidate in "$TARGET/.venv/bin/python" "$HOME/N3XV5-NATIVE-V2/.venv/bin/python"; do
  if [[ -x "$candidate" ]] && "$candidate" -c 'import Xlib' 2>/dev/null; then
    STOP_PY="$candidate"
    break
  fi
done
"$STOP_PY" "$STAGE/Linux/stop_legacy.py" || {
  echo 'Ancienne instance encore en cours : opération annulée.' >&2
  exit 4
}

# Prevent the previous autostart (NovaBar) from re-creating a second Navbar.
# Move, not delete: user can restore it if needed.
if [[ -e "$HOME/.config/autostart/health-perfs-bar.desktop" ]]; then
  mv -- "$HOME/.config/autostart/health-perfs-bar.desktop" \
    "$BACKUPS/health-perfs-bar.desktop.disabled"
fi

# Disable startup entries that explicitly relaunch the retired test directories.
# Do NOT alter xfce4-panel or unrelated autostart apps.
shopt -s nullglob
for desktop in "$HOME"/.config/autostart/*.desktop; do
  [[ "$desktop" == "$AUTOSTART" ]] && continue
  if grep -Eq '^Exec=.*(N3XV5-XFCE-TEST|N3XV5-NATIVE-V2|/usr/bin/novabar|HealthPerfsBar)' "$desktop"; then
    echo "Désactivation ancien démarrage : $desktop"
    mv -- "$desktop" "$BACKUPS/$(basename "$desktop").disabled"
  fi
done
shopt -u nullglob

if [[ -d "$TARGET" ]]; then
  OLD_RUNTIME="$BACKUPS/previous-runtime"
  mv -- "$TARGET" "$OLD_RUNTIME"
fi
mkdir -p "$TARGET"
ACTIVATED=1
cp -a "$STAGE/App" "$STAGE/Linux" "$STAGE/Legacy" "$TARGET/"
cp -a "$STAGE/uninstall.sh" "$TARGET/uninstall.sh"
# Venv cannot safely be moved; recreate at final location.
python3 -m venv "$TARGET/.venv"
"$TARGET/.venv/bin/python" -m pip install --disable-pip-version-check \
  -e "$TARGET/$LEGACY"
"$TARGET/.venv/bin/python" - <<'PY'
from PySide6 import QtCore, QtWidgets, QtSvg
import psutil, Xlib
print('Environnement Qt / sensors / X11 : OK')
PY

# Privileged helper code resides in root-owned /usr/local/libexec only.
echo 'Installation du helper Turbo (sudo nécessaire)…'
sudo install -d -o root -g root -m 0755 /usr/local/libexec
sudo install -o root -g root -m 0755 "$STAGE/Linux/n3xvs-hud-turbo" "$HELPER"

cat > "$AUTOSTART" <<DESKTOP
[Desktop Entry]
Type=Application
Name=N3XV5 HUD Theme Unified
Exec=$TARGET/Linux/start.sh
Terminal=false
OnlyShowIn=XFCE;
X-GNOME-Autostart-enabled=true
Hidden=false
DESKTOP
cat > "$APPDESKTOP" <<DESKTOP
[Desktop Entry]
Type=Application
Name=N3XV5 HUD Theme Unified
Comment=Top HUD et Navbar Bottom Slim (Qt natif)
Exec=$TARGET/Linux/start.sh
Terminal=false
Categories=Utility;System;
StartupNotify=false
DESKTOP
# Absolute symlink avoids deriving ROOT from ~/.local/bin/.
if [[ -e "$BIN" || -L "$BIN" ]]; then rm -f -- "$BIN"; fi
ln -s "$TARGET/Linux/start.sh" "$BIN"
[[ "$(readlink -f "$BIN")" == "$TARGET/Linux/start.sh" ]] || { echo 'Lien du lanceur incorrect.' >&2; exit 5; }
[[ -x "$TARGET/.venv/bin/python" ]] || { echo 'Python Qt non disponible' >&2; exit 6; }
ACTIVATED=0
trap - ERR

echo
echo '✅ Réinstallation N3XV5 Unified 2.2.2 terminée'
echo '✅ Une seule entrée autostart N3XV5; anciens lancements connus sauvegardés et désactivés'
echo "✅ Sauvegardes : $BACKUPS"
echo "✅ Lanceur : $BIN"
echo 'Ouverture de N3XV5…'
"$BIN" &
disown || true
sleep 2
if ! pgrep -f "$TARGET/App/Modules/Top/HUD_Plugins_ViewBar/NativeQt/n3xvs_top_native.py" >/dev/null; then
  echo '⚠️ Le processus Qt semble arrêté. Dernier journal :'
  tail -n 35 "$STATE/session.log" || true
else
  echo '✅ Processus Qt Unified détecté (affichage à confirmer sur XFCE)'
fi
