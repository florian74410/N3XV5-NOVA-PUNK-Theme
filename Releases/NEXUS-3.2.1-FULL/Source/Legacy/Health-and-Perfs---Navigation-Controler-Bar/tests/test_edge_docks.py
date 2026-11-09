"""Regression tests for 3-panel NovaBar and native edge launcher docks."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from healthbar.app import Bar
from healthbar.config import Settings
from healthbar.dialogs import SettingsDialog
from healthbar.edge_docks import (
    EdgeDock, default_folders, desktop_apps, launch_item,
    normalized_drop, launcher_metadata,
)


class DockTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_folders_are_localized_and_recent_entry_exists(self):
        folders = default_folders()
        self.assertEqual(folders[0], str(Path.home()))
        self.assertIn("recent:///", folders)

    def test_launcher_discovery_and_safe_drops(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            folder = root / "Mes documents"
            folder.mkdir()
            valid = root / "Firefox.desktop"
            valid.write_text("[Desktop Entry]\nType=Application\nName=Firefox\nIcon=firefox\nExec=firefox\n")
            not_app = root / "not-app.desktop"
            not_app.write_text("[Desktop Entry]\nType=Link\nName=Unknown\nURL=https://example.org\n")
            fake = root / "danger.sh"
            fake.write_text("#!/bin/sh\n")
            self.assertEqual(normalized_drop([folder, valid, fake], "folders"), [str(folder.resolve())])
            with patch("healthbar.edge_docks.sys.platform", "linux"):
                self.assertEqual(normalized_drop([folder, valid, fake], "apps"), [str(folder.resolve()), str(valid.resolve())])
                self.assertEqual(launcher_metadata(valid), ("Firefox", "firefox"))
                self.assertIsNone(launcher_metadata(not_app))
                self.assertFalse(launch_item(str(fake), "apps"))
                with patch("healthbar.edge_docks.xdg_folder", return_value=root):
                    self.assertEqual(desktop_apps(), [str(valid)])

    def test_saved_lists_and_independent_panel_settings(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, HEALTHBAR_DATA_DIR=temp):
            s = Settings(bottom_dock_enabled=False, hud_enabled=False, dock_left_enabled=True, dock_right_enabled=False,
                         dock_left_kind="apps", dock_right_kind="folders",
                         dock_folder_paths=[], dock_app_paths=[])
            s.save()
            loaded = Settings.load()
            self.assertFalse(loaded.hud_enabled)
            self.assertEqual(loaded.dock_app_paths, [])
            self.assertEqual(loaded.dock_left_kind, "apps")
            loaded.dock_left_enabled = False
            with self.assertRaises(ValueError):
                loaded.validate()
            loaded.dock_right_enabled = True
            loaded.validate()

    def test_retract_expand_after_three_seconds_and_swap_side(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, HEALTHBAR_DATA_DIR=temp):
            settings = Settings(configured=True, auto_hide=False, retract_mode="manual",
                                dock_folder_paths=["recent:///"], dock_app_paths=[])
            bar = Bar(settings)
            bar.show()
            bar.sensor_timer.stop()
            self.app.processEvents()
            try:
                left, right = bar.sidebars["left"], bar.sidebars["right"]
                self.assertEqual(left.kind, "folders")
                self.assertEqual(right.kind, "apps")
                self.assertEqual(left.hide_timer.interval(), 3000)
                self.assertEqual(left.width(), left.edge_width)
                self.assertEqual(left.items.count(), 1)
                self.assertEqual(left.items.item(0).text(), "Récents")
                left.expand()
                self.app.processEvents()
                self.assertFalse(left.collapsed)
                self.assertEqual(left.width(), left.panel_width)
                left.collapse()
                self.assertTrue(left.collapsed)
                self.assertEqual(left.width(), left.edge_width)
                bar.move_dock("left")
                self.app.processEvents()
                self.assertEqual(bar.sidebars["left"].kind, "apps")
                self.assertEqual(bar.sidebars["right"].kind, "folders")
                self.assertEqual(Settings.load().dock_left_kind, "apps")
                bar.settings.hud_enabled = False
                bar.settings.dock_left_enabled = False
                bar.settings.dock_right_enabled = True
                bar.sync_sidebars()
                bar.hide()
                self.assertFalse(bar.isVisible())
                self.assertEqual(list(bar.sidebars), ["right"])
                bar.move_dock("right")
                self.app.processEvents()
                self.assertEqual(list(bar.sidebars), ["left"])
            finally:
                bar.edge_timer.stop()
                bar.close()

    def test_settings_dialog_exposes_three_controls(self):
        settings = Settings(configured=True)
        dialog = SettingsDialog(settings, self.app.screens())
        try:
            self.assertTrue(dialog.hud_enabled.isChecked())
            self.assertTrue(dialog.dock_left_enabled.isChecked())
            self.assertTrue(dialog.dock_right_enabled.isChecked())
            self.assertEqual(dialog.dock_left_kind.currentData(), "folders")
        finally:
            dialog.close()


if __name__ == "__main__":
    unittest.main()
