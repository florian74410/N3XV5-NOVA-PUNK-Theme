#!/usr/bin/env python3
"""Patch an isolated NEXUS 3.2.0 staging tree into 3.2.1 without touching stable."""
from __future__ import annotations
import argparse
import pathlib
import shutil
import tempfile

TOP = pathlib.Path("App/Modules/Top/HUD_Plugins_ViewBar/NativeQt/n3xvs_top_native.py")
PATCHES = [
    ("'net_speedtest_hourly': False, 'fan_max_rpm': {}}",
     "'net_speedtest_hourly': False, 'game_sleep_enabled': True, 'fan_max_rpm': {}}"),
    ("('always_visible','motion','holo_enabled','bottom_enabled','net_speedtest_hourly')",
     "('always_visible','motion','holo_enabled','bottom_enabled','net_speedtest_hourly','game_sleep_enabled')"),
    ("    add_settings_group('general',behavior)\n",
     "    add_settings_group('general',behavior)\n"
     "    gaming_group=QGroupBox('MODE GAMING / VEILLE')\n"
     "    gaming_layout=QVBoxLayout(gaming_group)\n"
     "    gaming_toggle=QCheckBox('Activer la mise en veille de NEXUS avec Dolphin')\n"
     "    gaming_toggle.setChecked(prefs['game_sleep_enabled'])\n"
     "    gaming_layout.addWidget(gaming_toggle)\n"
     "    gaming_desc=QLabel('Dolphin ouvert : barre XFCE d’origine. Dolphin fermé : retour de NEXUS.')\n"
     "    gaming_desc.setWordWrap(True)\n"
     "    gaming_layout.addWidget(gaming_desc)\n"
     "    add_settings_group('general',gaming_group)\n"),
    ("prefs.update(height=height.value(),always_visible=always.isChecked(),hide_delay_s=delay.value(),",
     "prefs.update(game_sleep_enabled=gaming_toggle.isChecked(),height=height.value(),always_visible=always.isChecked(),hide_delay_s=delay.value(),"),
]

def patch(source, dest):
    source = source.expanduser().resolve()
    dest = dest.expanduser().resolve()
    if dest == source or dest.is_relative_to(source):
        raise ValueError("Destination must be separate from the source")
    if dest.exists():
        raise ValueError("Destination already exists; never overwrite")
    if (source / "VERSION.txt").read_text().strip() != "3.2.0-GAMING-SLEEP-TEST":
        raise ValueError("Expected NEXUS 3.2.0 staging source")
    text = (source / TOP).read_text(encoding="utf-8")
    for old, new in PATCHES:
        if text.count(old) != 1:
            raise ValueError("Unexpected source anchor; refusing unsafe patch: " + old[:70])
        text = text.replace(old, new, 1)
    compile(text, str(dest / TOP), "exec")
    shutil.copytree(source, dest, symlinks=True)
    try:
        (dest / TOP).write_text(text, encoding="utf-8")
        here = pathlib.Path(__file__).resolve().parent
        target = dest / "App/Core/GamingSleep"
        for filename in ("watcher_v321.py", "restore_panel_v321.py", "qt_bridge.py"):
            shutil.copy2(here / filename, target / filename)
        (dest / "VERSION.txt").write_text("3.2.1-GAMING-PANEL-TEST\n", encoding="utf-8")
    except Exception:
        shutil.rmtree(dest)
        raise

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--source", required=True, type=pathlib.Path)
    p.add_argument("--dest", required=True, type=pathlib.Path)
    args = p.parse_args()
    patch(args.source, args.dest)
    print("NEXUS 3.2.1 prepared:", args.dest)
