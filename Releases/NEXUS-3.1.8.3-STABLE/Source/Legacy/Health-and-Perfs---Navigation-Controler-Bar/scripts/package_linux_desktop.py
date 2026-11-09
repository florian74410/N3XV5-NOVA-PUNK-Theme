"""Native DEB and Flatpak distributors for the already-tested PyInstaller runtime.

No maintenance scripts delete user data. The installed application itself owns its
profiles, themes, settings and plugins; updating a package replaces ONLY app files.
"""
import argparse
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

APP_ID = "io.github.florian74410.NovaBar"
RUNTIME = "25.08"
ROOT = Path(__file__).resolve().parents[1]
BINARY = ROOT / "dist/HealthPerfsBar"
OUT = ROOT / "dist/linux"
ICON = (ROOT / "src/healthbar/assets/novabar-icon.svg").read_text(encoding="utf-8")


def _write(path, content, executable=False):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    path.chmod(0o755 if executable else 0o644)


def populate(root, base, application, version):
    """Copy binaries and XDG metadata into a .deb or Flatpak staging root."""
    if not (BINARY / "HealthPerfsBar").is_file():
        raise FileNotFoundError("Compiled Linux runtime missing: dist/HealthPerfsBar/HealthPerfsBar")
    if (root / base / "lib/novabar/HealthPerfsBar").exists():
        raise ValueError("Target staging directory already contains NovaBar")
    shutil.copytree(BINARY, root / base / "lib/novabar/HealthPerfsBar", symlinks=True)
    if application == "flatpak":
        script = ("#!/bin/sh\nexport NOVABAR_PACKAGED=flatpak\n"
                  "exec /app/lib/novabar/HealthPerfsBar/HealthPerfsBar \"$@\"\n")
    else:
        script = ("#!/bin/sh\nexport NOVABAR_PACKAGED=deb\n"
                  "exec /usr/lib/novabar/HealthPerfsBar/HealthPerfsBar \"$@\"\n")
    _write(root / base / "bin/novabar", script, executable=True)
    if application == "deb":
        # Small root-owned Python 3 helper; NovaBar itself never runs as root.
        helper=(ROOT/"scripts/novabar_turbo_helper.py").read_text(encoding="utf-8")
        _write(root/base/"libexec/novabar-turbo-helper",helper,executable=True)
    _write(root / base / "share/applications" / (APP_ID + ".desktop"),
           f"[Desktop Entry]\nType=Application\nName=NovaBar\n"
           f"GenericName=Hardware health and performance HUD\n"
           f"Comment=CYBER NEXUS HUD electric-neon system bar\n"
           f"Exec=novabar\nIcon={APP_ID}\nTerminal=false\n"
           f"Categories=System;Monitor;\nStartupNotify=false\n")
    _write(root / base / "share/icons/hicolor/scalable/apps" / (APP_ID + ".svg"), ICON)
    _write(root / base / "share/metainfo" / (APP_ID + ".metainfo.xml"),
           '<?xml version="1.0" encoding="UTF-8"?>\n'
           '<component type="desktop-application">\n'
           f'  <id>{APP_ID}</id>\n'
           '  <name>NovaBar</name><summary>Neon hardware-monitoring desktop bar</summary>\n'
           '  <metadata_license>CC0-1.0</metadata_license>\n'
           '  <project_license>LicenseRef-proprietary</project_license>\n'
           '  <description><p>NovaBar is a local desktop HUD with read-only '
           'hardware telemetry and modular plugins.</p></description>\n'
           f'  <launchable type="desktop-id">{APP_ID}.desktop</launchable>\n'
           f'  <releases><release version="{version}" date="2026-10-31"/></releases>\n'
           '</component>\n')


def build_deb(version):
    OUT.mkdir(parents=True, exist_ok=True)
    # A locally frozen Python may require the build host's newer glibc.
    libc_name, libc_version = platform.libc_ver()
    minimum_libc = libc_version if libc_name == "glibc" and libc_version else "2.35"
    with tempfile.TemporaryDirectory(prefix="novabar-deb-") as temporary:
        stage = Path(temporary) / "package"
        populate(stage, Path("usr"), "deb", version)
        size = sum(p.stat().st_size for p in stage.rglob("*") if p.is_file()) // 1024
        _write(stage / "DEBIAN/control", (
            "Package: novabar\n"
            f"Version: {version}\nArchitecture: amd64\n"
            "Maintainer: NovaBar Contributors <noreply@github.com>\n"
            f"Installed-Size: {size}\n"
            f"Depends: libc6 (>= {minimum_libc}), libx11-6, libx11-xcb1, libxcb1, "
            "libxkbcommon-x11-0, libxcb-xkb1, libxcb-cursor0, "
            "libxcb-icccm4, libxcb-image0, libxcb-keysyms1, "
            "libxcb-render-util0, libxcb-randr0, libxcb-xinerama0, "
            "libegl1, libgl1, libopengl0, libdbus-1-3, iputils-ping\n"
            "Section: utils\nPriority: optional\n"
            "Homepage: https://github.com/florian74410/Health-and-Perfs---Navigation-Controler-Bar\n"
            "Description: NovaBar neon desktop telemetry HUD\n"
            " Native Linux Mint/Ubuntu package; previous app files are replaced\n"
            " by dpkg while preserving user profiles and plugins.\n"
        ))
        result = OUT / f"NovaBar_{version}_amd64.deb"
        subprocess.run(["dpkg-deb", "--build", "--root-owner-group", str(stage), str(result)], check=True)
    return result


def build_flatpak(version):
    OUT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="novabar-flatpak-") as temporary:
        temp = Path(temporary)
        build = temp / "build"
        repo = temp / "repo"
        subprocess.run(["flatpak", "build-init", str(build), APP_ID,
                        "org.freedesktop.Sdk", "org.freedesktop.Platform", RUNTIME], check=True)
        populate(build, Path("files"), "flatpak", version)
        # Home is needed for existing NovaBar profiles/plugins; the sandbox does
        # not grant privileged device access. Hardware probes may be incomplete.
        subprocess.run(["flatpak", "build-finish", str(build),
                        "--command=novabar", "--share=ipc",
                        "--socket=x11", "--socket=wayland",
                        "--share=network", "--device=dri", "--filesystem=home"], check=True)
        subprocess.run(["flatpak", "build-export", "--disable-fsync",
                        str(repo), str(build), "stable"], check=True)
        result = OUT / f"NovaBar_{version}_x86_64.flatpak"
        subprocess.run(["flatpak", "build-bundle",
                        "--runtime-repo=https://dl.flathub.org/repo/flathub.flatpakrepo",
                        str(repo), str(result), APP_ID, "stable"], check=True)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("format", choices=("deb", "flatpak"))
    parser.add_argument("--version", required=True)
    args = parser.parse_args()
    if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+(?:\.[0-9]+)?", args.version):
        parser.error("Version must be MAJOR.MINOR.PATCH[.BUILD]")
    if not sys.platform.startswith("linux"):
        parser.error("Packages are built only on Linux")
    path = build_deb(args.version) if args.format == "deb" else build_flatpak(args.version)
    if path.stat().st_size >= 100 * 1024 * 1024:
        raise ValueError(f"{path.name} exceeds the GitHub 100 MiB size cap")
    print(f"{path}: {path.stat().st_size/1024/1024:.1f} MiB")


if __name__ == "__main__":
    main()
