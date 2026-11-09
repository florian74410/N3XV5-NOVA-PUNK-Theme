"""Launch just the v0.7 Settings UI without starting bars or touching XFCE.

This is deliberately an isolated test entrypoint, not the full desktop app.
Run: python scripts/preview_v07_settings.py
"""
from __future__ import annotations
import os
from pathlib import Path

sandbox = Path.home() / ".config" / "novabar-v07-preview"
sandbox.mkdir(parents=True, exist_ok=True)
os.environ["XDG_CONFIG_HOME"] = str(sandbox)
os.environ["HEALTHBAR_DATA_DIR"] = str(sandbox / "data")

from PySide6.QtWidgets import QApplication
from healthbar.config import Settings
from healthbar.dialogs import SettingsDialog

def main():
    app = QApplication([])
    app.setApplicationName("NovaBar 0.7 Preview")
    config = Settings(
        configured=True,
        bottom_dock_enabled=False,
        xfce_skin_enabled=False,
        autostart=False,
    )
    dialog = SettingsDialog(config, app.screens())
    dialog.setWindowTitle("NovaBar 0.7 DEV — Prévisualisation des paramètres")
    dialog.show()
    return app.exec()

if __name__ == "__main__":
    raise SystemExit(main())
