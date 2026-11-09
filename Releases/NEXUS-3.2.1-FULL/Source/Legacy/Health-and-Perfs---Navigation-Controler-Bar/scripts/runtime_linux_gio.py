"""PyInstaller runtime hook: keep Linux host GVFS out of frozen GLib.

Bundled libgio/libglib may predate host libgvfscommon, whose ABI can differ.
Prevent loading host GIO modules *inside this frozen process*; child desktop
programs get their normal GLib environment through healthbar.system_env.native_env.
This runs before importing Qt/GIO application code.
"""
import os
import sys
from pathlib import Path

if sys.platform.startswith("linux") and getattr(sys, "frozen", False):
    home = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    isolated = home / "healthbar" / "assets" / "gio-empty"
    if isolated.is_dir():
        original = os.environ.get("GIO_MODULE_DIR")
        if original is not None:
            os.environ["NOVABAR_ORIG_GIO_MODULE_DIR"] = original
        extra = os.environ.get("GIO_EXTRA_MODULES")
        if extra is not None:
            os.environ["NOVABAR_ORIG_GIO_EXTRA_MODULES"] = extra
        os.environ["GIO_MODULE_DIR"] = str(isolated)
        os.environ.pop("GIO_EXTRA_MODULES", None)
