#!/usr/bin/env bash
# Installs ONLY the N3XV5 Bottom navbar module from its tested GitHub branch.
# Does not modify NovaBar 0.8.2.2 files or touch the TOP bar / other docks.
set -Eeuo pipefail
REPO="$HOME/N3XV5-HUD-Theme-1.0"
RUNTIME="$HOME/N3XV5-NATIVE-V2"
BRANCH="work/n3xvs-bottom-slim-neon-v1"
PREFIX="App/Modules/Bottom/HUD_HomeNavBar"
[[ -d "$REPO/.git" ]] || { echo "Depot introuvable: $REPO"; exit 2; }
[[ -f "$RUNTIME/Legacy/Health-and-Perfs---Navigation-Controler-Bar/src/healthbar/bottom_dock.py" ]] || { echo "Legacy 0.8.2.2 introuvable."; exit 3; }
[[ -x "$RUNTIME/.venv/bin/python" ]] || { echo "Python Qt absent: $RUNTIME/.venv/bin/python"; exit 4; }

echo "==> Téléchargement de la branche (sans changer de branche locale)"
git -C "$REPO" fetch --no-tags origin "$BRANCH"

src="NativeQt/n3xvs_bottom_slim.py"
dest="$RUNTIME/$PREFIX/$src"
mkdir -p "$(dirname "$dest")"
if [[ -f "$dest" ]]; then
  cp -a "$dest" "$dest.bak.$(date +%Y%m%d-%H%M%S)"
fi
git -C "$REPO" show "FETCH_HEAD:$PREFIX/$src" > "$dest"

src="start_slim_navbar.sh"
dest="$RUNTIME/$PREFIX/$src"
if [[ -f "$dest" ]]; then
  cp -a "$dest" "$dest.bak.$(date +%Y%m%d-%H%M%S)"
fi
git -C "$REPO" show "FETCH_HEAD:$PREFIX/$src" > "$dest"
chmod +x "$dest"

echo "==> Vérification de syntaxe"
"$RUNTIME/.venv/bin/python" -m py_compile "$RUNTIME/$PREFIX/NativeQt/n3xvs_bottom_slim.py"
bash -n "$dest"

echo
echo "✅ Module installé (test): $RUNTIME/$PREFIX"
echo "La Navbar précédente est conservée dans: $RUNTIME/start_navbar_bottom.sh"
echo
echo "==> Pour lancer la Navbar affinée:"
echo "bash '$dest'"
echo
echo "Note: ferme l'ancienne Navbar avant de lancer celle-ci si wmctrl n'est pas installé."
