#!/usr/bin/env bash
# N3XV5 2.2.5 GitHub bootstrap for an already installed Unified 2.2.x.
# No sudo, no changes to the user's current Git working tree.
set -Eeuo pipefail
[[ "$(id -u)" -ne 0 ]] || { echo "Ne pas lancer avec sudo." >&2; exit 2; }
command -v git >/dev/null || { echo "Installer git d'abord." >&2; exit 3; }
TMP="$(mktemp -d)"
trap 'rm -rf -- "$TMP"' EXIT
git clone --quiet --filter=blob:none --depth=1 --sparse \
  --branch work/n3xvs-unified-v2.2.5 \
  https://github.com/florian74410/N3XV5-NOVA-PUNK-Theme.git "$TMP/repo"
git -C "$TMP/repo" sparse-checkout set Releases/N3XV5-2.2.5
bash "$TMP/repo/Releases/N3XV5-2.2.5/update.sh" "$@"
