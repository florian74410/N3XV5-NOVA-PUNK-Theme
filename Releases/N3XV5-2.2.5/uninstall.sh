#!/usr/bin/env bash
set -Eeuo pipefail
TARGET="$HOME/.local/share/n3xvs-hud"
STATE="$HOME/.local/state/n3xvs-hud"
read -r -p 'Désinstaller N3XV5 Unified (préférences et sauvegardes conservées) ? Tape OUI : ' answer
[[ "$answer" == OUI ]] || { echo 'Annulé'; exit 0; }
if [[ -f "$TARGET/Linux/stop_legacy.py" ]]; then python3 "$TARGET/Linux/stop_legacy.py" || true; fi
for file in "$HOME/.config/autostart/n3xvs-hud.desktop" \
  "$HOME/.local/share/applications/n3xvs-hud.desktop" "$HOME/.local/bin/n3xvs-hud"; do
  [[ ! -e "$file" && ! -L "$file" ]] || rm -f -- "$file"
done
[[ ! -d "$TARGET" ]] || rm -rf -- "$TARGET"
if [[ -f /usr/local/libexec/n3xvs-hud-turbo ]]; then
  sudo rm -f /usr/local/libexec/n3xvs-hud-turbo
fi
echo "✅ N3XV5 désinstallé. Préférences dans ~/.config/n3xvs-hud et archives dans $STATE/backups."
echo 'L’ancien démarrage NovaBar est resté désactivé pour éviter les doublons.'
