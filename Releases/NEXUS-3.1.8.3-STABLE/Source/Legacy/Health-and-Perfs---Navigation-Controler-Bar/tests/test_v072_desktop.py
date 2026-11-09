"""NovaBar 0.7.2 Linux: full control and rendering smoke tests."""
import os
import tempfile
import unittest
from unittest.mock import patch
from PySide6.QtCore import QPoint
from PySide6.QtWidgets import QApplication,QListWidget
from healthbar.config import Settings
from healthbar.dialogs import SettingsDialog
from healthbar.bottom_dock import BottomDock,bottom_height
from healthbar.app import Bar
from healthbar.settings_visual import settings_stylesheet
from healthbar.x11_workarea import reserve_edge


class V072DesktopTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app=QApplication.instance() or QApplication([])

    def test_settings_persist_independent_controls(self):
        with tempfile.TemporaryDirectory() as root,patch.dict(os.environ,HEALTHBAR_DATA_DIR=root):
            opts=Settings(bottom_dock_height=96,bottom_tabs_max=2,top_hover_ms=1200,
                          top_trigger_px=10,top_reserved=True,turbo_auth_enabled=False)
            opts.validate();opts.save()
            updated=Settings.load()
            self.assertEqual((updated.bottom_dock_height,updated.bottom_tabs_max,updated.top_hover_ms),
                             (96,2,1200))
            self.assertFalse(updated.turbo_auth_enabled)
            self.assertEqual(bottom_height(updated),96)

    def test_neon_settings_has_no_grey_default_and_genuine_controls(self):
        with tempfile.TemporaryDirectory() as root,patch.dict(os.environ,HEALTHBAR_DATA_DIR=root):
            dialog=SettingsDialog(Settings(configured=True,theme="blue-neon"),self.app.screens())
            try:
                self.assertGreaterEqual(dialog.width(),650)
                self.assertIsNotNone(dialog.findChild(QListWidget,"settingsNavigation"))
                self.assertEqual(dialog.bottom_tabs_max.value(),3)
                self.assertEqual(dialog.top_trigger_px.value(),10)
                self.assertEqual(dialog.top_hover_ms.value(),1000)
                self.assertTrue(dialog.top_reserved.isChecked())
                self.assertTrue(dialog.live_bar_preview.minimumHeight()>=130)
                self.assertIn("background:rgba(2,14,32,175)",dialog.styleSheet())
                dialog.reset_display()
                self.assertEqual(dialog.bottom_dock_height.value(),84)
            finally:
                dialog.close()

    def test_dock_has_max_three_visible_tabs_plus_overflow(self):
        with tempfile.TemporaryDirectory() as root,patch.dict(os.environ,HEALTHBAR_DATA_DIR=root):
            dock=BottomDock(Settings(dock_app_paths=[],bottom_tabs_max=3))
            try:
                rows=[{"id":i,"name":"Window "+str(i),"icon":"none"} for i in range(7)]
                with patch.object(dock.backend,"snapshot",return_value=(rows,rows[0]["id"])):
                    dock.refresh()
                self.assertEqual(dock.tasks.count(),4) # 3 buttons + stretch
                self.assertEqual(len(dock._overflow_rows),4)
                self.assertEqual(dock.overflow.text(),"+4")
                self.assertTrue(dock.overflow.isVisible())
            finally:
                dock.close()

    def test_top_hud_never_shows_close_x(self):
        with tempfile.TemporaryDirectory() as root,patch.dict(os.environ,HEALTHBAR_DATA_DIR=root):
            settings=Settings(configured=True,bottom_dock_enabled=False,
                              dock_left_enabled=False,dock_right_enabled=False)
            bar=Bar(settings)
            try:
                bar.show();self.app.processEvents()
                self.assertFalse(bar.quit_button.isVisible())
                self.assertTrue(bar.expand_button.isVisible())
                self.assertEqual(bar.settings.top_hover_ms,1000)
            finally:
                bar.close()

    def test_gio_and_x11_reservation_fail_safe_offscreen(self):
        self.assertFalse(reserve_edge(object(),"top",72,True))

    def test_pcb_theme_colors_are_selectable(self):
        css=settings_stylesheet("green-matrix")
        self.assertIn("#43fa9a",css.lower())
        self.assertNotIn("background: #dddddd",css.lower())


if __name__=="__main__":
    unittest.main()
