"""NovaBar 0.6.9 regression: XFCE panel, themes and X11 workspaces."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtCore import Qt, QRect
from PySide6.QtGui import QImage
from PySide6.QtWidgets import QApplication, QWidget

from healthbar.config import Settings
from healthbar.edge_docks import EdgeDock, PCBDockFrame, dock_stylesheet
from healthbar.xfce_panel_effects import _is_bottom_native_panel


class CyberHotfixTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_xfce_panel_bottom_geometry_not_offscreen_or_sidebars(self):
        screen = QRect(0, 0, 1920, 1080)
        self.assertTrue(_is_bottom_native_panel(QRect(0, 1015, 1920, 65), screen))
        self.assertTrue(_is_bottom_native_panel(QRect(50, 1030, 1820, 50), screen))
        self.assertFalse(_is_bottom_native_panel(QRect(0, 0, 1920, 65), screen))
        self.assertFalse(_is_bottom_native_panel(QRect(0, 64, 9, 1015), screen))
        self.assertFalse(_is_bottom_native_panel(QRect(0, 1079, 1920, 1), screen))

    def test_side_panels_paint_real_theme_palette(self):
        with tempfile.TemporaryDirectory() as temp:
            settings = Settings(configured=True, theme="cyber-futuriste",
                                dock_folder_paths=["recent:///"], dock_app_paths=[])
            frame = PCBDockFrame(settings)
            frame.resize(250, 600)
            try:
                first = QImage(250, 600, QImage.Format.Format_ARGB32_Premultiplied)
                first.fill(Qt.GlobalColor.transparent)
                frame.render(first)
                self.assertGreater(first.pixelColor(4, 50).alpha(), 0)
                self.assertIn("#18dfff", dock_stylesheet("blue-neon"))
                self.assertIn("#43fa9a", dock_stylesheet("green-matrix"))
                self.assertIn("#ff607d", dock_stylesheet("red-blood"))
                settings.theme = "green-matrix"
                frame.phase = .6
                second = QImage(250, 600, QImage.Format.Format_ARGB32_Premultiplied)
                second.fill(Qt.GlobalColor.transparent)
                frame.render(second)
                self.assertNotEqual(first, second)
            finally:
                frame.close()

    def test_dock_animates_and_reuses_theme_without_touching_bookmarks(self):
        settings = Settings(configured=True, theme="blue-neon",
                            dock_folder_paths=["recent:///"], dock_app_paths=[])
        dock = EdgeDock("left", "folders", settings)
        dock.show()
        self.app.processEvents()
        try:
            saved = dock.items.values()
            self.assertFalse(dock.fx_timer.isActive())
            dock.expand()
            self.assertTrue(dock.fx_timer.isActive())
            dock.animate_circuit()
            self.assertGreater(dock.content.phase, 0)
            settings.theme = "red-blood"
            dock.apply_theme()
            self.assertIn("#ff607d", dock.content.styleSheet())
            self.assertEqual(dock.items.values(), saved)
            dock.collapse()
            self.assertFalse(dock.fx_timer.isActive())
            self.assertEqual(dock.width(), dock.edge_width)
        finally:
            dock.close()

    def test_workspace_requests_retry_after_map_only(self):
        from healthbar import overlay
        widget = QWidget()
        widget.show()
        self.app.processEvents()
        requests = []
        callbacks = []
        with (patch("healthbar.overlay.sys.platform", "linux"),
              patch.dict(os.environ, {"DISPLAY": ":1"}),
              patch("PySide6.QtCore.QTimer.singleShot",
                    side_effect=lambda delay, cb: callbacks.append((delay, cb))),
              patch("healthbar.overlay.apply_all_workspaces",
                    side_effect=lambda target: requests.append(target))):
            overlay.schedule_all_workspaces(widget)
            self.assertEqual([delay for delay, _ in callbacks], [0, 180, 750])
            for _delay, cb in callbacks:
                cb()
        self.assertEqual(requests, [widget]*3)
        widget.close()

    def test_workspace_watchdog_only_repairs_windows_not_on_all_desktops(self):
        from healthbar import overlay
        widget = QWidget()
        widget.show()
        self.app.processEvents()
        with (patch("healthbar.overlay.sys.platform", "linux"),
              patch.dict(os.environ, {"DISPLAY": ":1"}),
              patch("healthbar.overlay.is_on_all_workspaces", return_value=True),
              patch("healthbar.overlay.apply_all_workspaces") as request):
            overlay.maintain_all_workspaces(widget)
            request.assert_not_called()
        with (patch("healthbar.overlay.sys.platform", "linux"),
              patch.dict(os.environ, {"DISPLAY": ":1"}),
              patch("healthbar.overlay.is_on_all_workspaces", return_value=False),
              patch("healthbar.overlay.apply_all_workspaces") as request):
            overlay.maintain_all_workspaces(widget)
            request.assert_called_once_with(widget)
        widget.close()

    def test_optional_system_skin_offer_is_one_time(self):
        from healthbar.app import Bar
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, HEALTHBAR_DATA_DIR=folder):
            settings = Settings(bottom_dock_enabled=False, configured=True, auto_hide=False, retract_mode="manual",
                                xfce_skin_enabled=False, dock_app_paths=[], dock_folder_paths=[])
            bar = Bar(settings)
            bar.sensor_timer.stop()
            try:
                with (patch("healthbar.xfce_panel_skin.available", return_value=True),
                      patch("healthbar.app.QMessageBox.question",
                            return_value=__import__("PySide6.QtWidgets", fromlist=["QMessageBox"]).QMessageBox.StandardButton.Yes),
                      patch("healthbar.app.QMessageBox.warning"),
                      patch.object(bar, "sync_xfce_skin") as sync):
                    bar.offer_xfce_cyber()
                    self.assertTrue(settings.xfce_skin_enabled)
                    self.assertTrue(settings.xfce_skin_offer_done)
                    self.assertTrue(Settings.load().xfce_skin_enabled)
                    sync.assert_called_once()
                    bar.offer_xfce_cyber()
                    sync.assert_called_once()
            finally:
                bar.edge_timer.stop()
                bar.tray.hide()
                bar.close()


if __name__ == "__main__":
    unittest.main()
