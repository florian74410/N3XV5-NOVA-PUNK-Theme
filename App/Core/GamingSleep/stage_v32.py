#!/usr/bin/env python3
"""Apply NEXUS 3.2 Gaming Sleep Qt bridge to an OUT-OF-TREE copy.

Usage:
  python3 stage_v32.py --source /path/to/3.1.8.3/Source --dest /tmp/nexus-320-test
Never edits the source or the user's installed NEXUS.
"""
from __future__ import annotations
import argparse
import pathlib
import shutil

TOP = pathlib.Path("App/Modules/Top/HUD_Plugins_ViewBar/NativeQt/n3xvs_top_native.py")
MARKER = "    app=QApplication([sys.argv[0]])\n"
INSERT = ("    from App.Core.GamingSleep.qt_bridge import install_game_sleep_bridge\n"
          "    _nexus_gaming_timer = install_game_sleep_bridge(app, app)\n")

def stage(source, destination):
    if not (source / TOP).is_file():
        raise ValueError("Missing exact NEXUS top source")
    if (source / "VERSION.txt").read_text(encoding="utf-8").strip() != "3.1.8.3-FULL":
        raise ValueError("Not the verified 3.1.8.3 baseline")
    if destination.exists():
        raise ValueError("Destination exists. Refusing overwrite.")
    if destination.resolve() == source.resolve() or destination.resolve().is_relative_to(source.resolve()):
        raise ValueError("Destination must not be inside the original source")
    bridge = pathlib.Path(__file__).resolve().parent
    if not (bridge / "qt_bridge.py").is_file():
        raise ValueError("Missing Qt bridge")
    shutil.copytree(source, destination, symlinks=True)
    try:
        target = destination / TOP
        old = target.read_text(encoding="utf-8")
        if old.count(MARKER) != 1 or INSERT.strip() in old:
            raise ValueError("Unexpected Qt entry point; refusing unsafe patch")
        new = old.replace(MARKER, MARKER + INSERT, 1)
        compile(new, str(target), "exec")
        target.write_text(new, encoding="utf-8")
        directory = destination / "App/Core/GamingSleep"
        directory.mkdir(parents=True, exist_ok=True)
        shutil.copy2(bridge / "qt_bridge.py", directory / "qt_bridge.py")
        (directory / "__init__.py").write_text("", encoding="utf-8")
        (destination / "VERSION.txt").write_text("3.2.0-GAMING-SLEEP-TEST\n", encoding="utf-8")
    except Exception:
        shutil.rmtree(destination)
        raise
    print("NEXUS 3.2 staging prepared:", destination)

if __name__ == "__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=pathlib.Path)
    parser.add_argument("--dest", required=True, type=pathlib.Path)
    args=parser.parse_args()
    stage(args.source.expanduser().resolve(), args.dest.expanduser().resolve())
