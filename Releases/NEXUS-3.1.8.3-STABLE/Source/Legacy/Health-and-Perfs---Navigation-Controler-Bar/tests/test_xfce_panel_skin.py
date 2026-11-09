"""Non-destructive Xfce 4 native panel skin and 10-second autohide tests."""
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QTabWidget
from healthbar.config import Settings
from healthbar.dialogs import SettingsDialog
from healthbar.xfce_panel_skin import (
    START, END, apply_skin, bottom_panel_id, remove_skin,
    render_css, with_managed_block,
)


class NativePanelSkinTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_scoped_css_and_safe_user_preservation(self):
        custom = "button.some-unrelated-app {color: purple;}\n"
        block = render_css("green-matrix", 10)
        self.assertIn("-XfcePanelWindow-popdown-delay: 10000;", block)
        self.assertIn("-XfcePanelWindow-autohide-size: 1;", block)
        self.assertIn("-XfcePanelWindow-popdown-delay: 45000;", render_css("blue-neon",45))
        self.assertIn("#43fa9a", block)
        self.assertIn(".xfce4-panel.background", block)
        merged = with_managed_block(custom, block)
        self.assertIn(custom.strip(), merged)
        self.assertEqual(merged.count(START), 1)
        self.assertEqual(merged.count(END), 1)
        self.assertEqual(with_managed_block(merged, block), merged)
        replaced = with_managed_block(merged, render_css("red-blood", 10))
        self.assertIn("#ff607d", replaced)
        self.assertNotIn("#43fa9a", replaced)
        removed = with_managed_block(replaced, "")
        self.assertEqual(removed.strip(), custom.strip())
        with self.assertRaises(ValueError):
            with_managed_block(custom+START, block)

    def test_only_bottom_panel_is_selected(self):
        listing = ("/panels/panel-0/position   p=6;x=0;y=0\n"
                   "/panels/panel-2/position   p=10;x=0;y=0\n"
                   "/panels/panel-1/position   p=0;x=300;y=300")
        with patch("healthbar.xfce_panel_skin._query", return_value=listing):
            self.assertEqual(bottom_panel_id(), 2)

    def test_enable_disable_restores_prior_autohide_and_user_css(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            css = base/"gtk-3.0/gtk.css"
            css.parent.mkdir()
            css.write_text("/* Own CSS */\n.somebody-else {color: red;}\n", encoding="utf-8")
            backup = base/"novabar-backup.json"
            state = {"autohide-behavior": "0", "size": "30"}
            def set_native(panel, property_name, value):
                state[property_name] = str(value)
                return True
            with (patch("healthbar.xfce_panel_skin.available", return_value=True),
                  patch("healthbar.xfce_panel_skin.bottom_panel_id", return_value=2),
                  patch("healthbar.xfce_panel_skin.panel_setting", side_effect=lambda panel, prop: state[prop]),
                  patch("healthbar.xfce_panel_skin._set_panel_setting", side_effect=set_native),
                  patch("healthbar.xfce_panel_skin.gtk_css_path", return_value=css),
                  patch("healthbar.xfce_panel_skin.backup_path", return_value=backup),
                  patch("healthbar.xfce_panel_skin._reload_panel") as reload):
                self.assertTrue(apply_skin("blue-neon")[0])
                self.assertEqual(state["autohide-behavior"], "2")
                self.assertEqual(state["size"], "52")
                self.assertEqual(json.loads(backup.read_text())["original_autohide"], "0")
                self.assertEqual(json.loads(backup.read_text())["original_size"], 30)
                self.assertTrue(apply_skin("blue-neon")[0])
                self.assertEqual(reload.call_count, 1)
                self.assertTrue(apply_skin("red-blood", 15, 200)[0])
                self.assertEqual(state["size"], "60")  # 2x original size, never 2x current.
                self.assertEqual(reload.call_count, 2)
                self.assertTrue(remove_skin()[0])
                self.assertEqual(state["autohide-behavior"], "0")
                self.assertEqual(state["size"], "30")
                self.assertNotIn(START, css.read_text())
                self.assertIn(".somebody-else", css.read_text())
                self.assertFalse(backup.exists())

    def test_missing_panel_refuses_to_touch_user_css(self):
        with tempfile.TemporaryDirectory() as folder:
            css = Path(folder)/"gtk.css"
            css.write_text("/* Custom */")
            with (patch("healthbar.xfce_panel_skin.available", return_value=True),
                  patch("healthbar.xfce_panel_skin.bottom_panel_id", return_value=None),
                  patch("healthbar.xfce_panel_skin.gtk_css_path", return_value=css)):
                self.assertFalse(apply_skin("blue-neon")[0])
                self.assertEqual(css.read_text(), "/* Custom */")

    def test_electronic_overlay_draws_without_capturing_input(self):
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QImage
        from healthbar.xfce_panel_effects import XFCEPanelCircuitEffects
        settings = Settings(configured=True, xfce_skin_enabled=True,
                            xfce_skin_fx_intensity=72)
        with patch("healthbar.xfce_panel_effects.panel_x11_bounds", return_value=None):
            effect = XFCEPanelCircuitEffects(settings)
        try:
            effect.poller.stop()
            effect.timer.stop()
            effect.resize(512, 36)
            effect._phase = .42
            frame = QImage(512, 36, QImage.Format.Format_ARGB32_Premultiplied)
            frame.fill(Qt.GlobalColor.transparent)
            effect.render(frame)
            self.assertTrue(effect.testAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents))
            self.assertGreater(frame.pixelColor(100, 2).alpha(), 0)
        finally:
            effect.close()

    def test_invalid_native_thickness_fails_before_any_write(self):
        with (patch("healthbar.xfce_panel_skin.available", return_value=True),
              patch("healthbar.xfce_panel_skin.bottom_panel_id", return_value=1),
              patch("healthbar.xfce_panel_skin._set_panel_setting") as setter):
            self.assertFalse(apply_skin("blue-neon", 10, 201)[0])
            self.assertFalse(apply_skin("blue-neon", 121, 150)[0])
            setter.assert_not_called()

    def test_config_can_run_only_native_xfce_without_other_docks(self):
        settings = Settings(hud_enabled=False, dock_left_enabled=False,
                            dock_right_enabled=False, xfce_skin_enabled=True,
                            xfce_skin_scale_percent=200, xfce_skin_delay_seconds=120)
        settings.validate()
        settings.xfce_skin_scale_percent = 201
        with self.assertRaises(ValueError):
            settings.validate()

    def test_settings_dialog_has_optional_skin(self):
        settings = Settings(configured=True, xfce_skin_enabled=True)
        settings.validate()
        dialog = SettingsDialog(settings, self.app.screens())
        try:
            tabs = dialog.findChild(QTabWidget)
            self.assertIn("Générale", [tabs.tabText(i) for i in range(tabs.count())])  # XFCE options grouped into General
            self.assertTrue(dialog.xfce_skin_enabled.isChecked())
            self.assertEqual(dialog.xfce_skin_fx_intensity.value(), 72)
            self.assertEqual(dialog.xfce_skin_delay_seconds.value(), 10)
            self.assertEqual(dialog.xfce_skin_scale_percent.value(), 175)
        finally:
            dialog.close()


if __name__ == "__main__":
    unittest.main()
