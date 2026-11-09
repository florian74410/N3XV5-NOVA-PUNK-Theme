#!/bin/sh
# Native GUI installer, usable on Mint, Ubuntu and Bazzite Desktop without root.
set -eu
cd -- "$(dirname -- "$0")"
exec ./CyberNexusInstaller/CyberNexusInstaller "$@"
