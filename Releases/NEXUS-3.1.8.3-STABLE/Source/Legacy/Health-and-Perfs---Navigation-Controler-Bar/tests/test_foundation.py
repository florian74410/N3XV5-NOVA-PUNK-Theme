import json
import os
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from healthbar.config import Settings, data_dir
from healthbar.plugins import PluginRegistry
from healthbar.autostart import desktop_quote


class FoundationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.env = patch.dict(os.environ, HEALTHBAR_DATA_DIR=str(self.root))
        self.env.start()
        self.registry = PluginRegistry(self.root / "plugins")

    def tearDown(self):
        self.env.stop()
        self.temp.cleanup()

    def package(self, version="1.0.0", **changes):
        manifest = dict(id="test-slot", name="Test slot", slot="cpu", version=version,
                        api_version=1, kind="declarative")
        manifest.update(changes)
        path = self.root / (version + ".hbp")
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("manifest.json", json.dumps(manifest))
        return path

    def test_update_preserves_activation_and_rollback_restores_version(self):
        first = self.package()
        _, digest = self.registry.inspect(first)
        self.registry.install(first, digest)
        self.assertFalse(self.registry.installed()[0]["enabled"])
        self.registry.set_enabled("test-slot", True)
        second = self.package("1.1.0")
        self.registry.install(second, self.registry.inspect(second)[1])
        self.assertTrue(self.registry.installed()[0]["enabled"])
        self.assertEqual(self.registry.installed()[0]["version"], "1.1.0")
        self.registry.rollback("test-slot")
        self.assertEqual(self.registry.installed()[0]["version"], "1.0.0")
        self.assertTrue(self.registry.installed()[0]["enabled"])

    def test_failed_update_leaves_current_version(self):
        first = self.package()
        self.registry.install(first, self.registry.inspect(first)[1])
        with self.assertRaises(ValueError):
            self.registry.install(first, "incorrect-digest")
        with self.assertRaises(ValueError):
            self.registry.install(first, self.registry.inspect(first)[1])
        self.assertEqual(self.registry.installed()[0]["version"], "1.0.0")

    def test_rejects_paths_executable_payloads_api_and_invalid_ids(self):
        archive = self.root / "unsafe.hbp"
        for member in ("../manifest.json", "/manifest.json", "folder\\manifest.json", "main.py"):
            with zipfile.ZipFile(archive, "w") as z:
                z.writestr(member, "{}")
            with self.assertRaises(ValueError):
                self.registry.inspect(archive)
        for changes in ({"api_version": 2}, {"api_version": True}, {"id": "../escape"},
                        {"slot": "unknown"}, {"kind": "python"}):
            with self.assertRaises(ValueError):
                self.registry.inspect(self.package(**changes))
        self.assertEqual(self.registry.installed(), [])

    def test_rename_failure_restores_previous_installation(self):
        first = self.package()
        self.registry.install(first, self.registry.inspect(first)[1])
        second = self.package("1.1.0")
        original = Path.rename
        def fail_stage(path, destination):
            if path.parent.name.startswith(".stage-"):
                raise OSError("simulated disk error")
            return original(path, destination)
        with patch.object(Path, "rename", fail_stage):
            with self.assertRaises(OSError):
                self.registry.install(second, self.registry.inspect(second)[1])
        self.assertEqual(self.registry.installed()[0]["version"], "1.0.0")

    def test_preferences_and_corruption_recovery(self):
        s = Settings(opacity=53, position="bottom", configured=True)
        s.save()
        self.assertEqual(Settings.load(), s)
        (data_dir() / "settings.json").write_text('{"thickness": "bad"}')
        self.assertEqual(Settings.load(), Settings())
        with self.assertRaises(ValueError):
            Settings(opacity=101).save()

    def test_legacy_default_height_migrates_but_custom_height_is_preserved(self):
        data_dir().mkdir(parents=True,exist_ok=True)
        path=data_dir()/'settings.json'
        path.write_text('{"thickness":200,"configured":true}')
        self.assertEqual(Settings.load().thickness,72)
        path.write_text('{"thickness":160,"configured":true}')
        self.assertEqual(Settings.load().thickness,150)
        current=Settings(thickness=120)
        current.save()
        self.assertEqual(Settings.load().thickness,120)

    def test_linux_autostart_quoting_and_remove(self):
        from healthbar import autostart
        with patch.dict(os.environ, XDG_CONFIG_HOME=str(self.root)), patch.object(autostart.sys, "platform", "linux"), patch.object(autostart, "launch_command", return_value=['/tmp/path with spaces/$x%`/python', '-m', 'healthbar']):
            autostart.set_enabled(True)
            desktop = self.root / "autostart/health-perfs-bar.desktop"
            content = desktop.read_text()
            self.assertIn('\\$x%%\\`', content)
            self.assertIn('"-m" "healthbar"', content)
            autostart.set_enabled(False)
            self.assertFalse(desktop.exists())


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtCore import QRect
from PySide6.QtWidgets import QApplication, QDialog
from healthbar.app import Bar
from healthbar.dialogs import SettingsDialog


class ShellTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, HEALTHBAR_DATA_DIR=self.temp.name)
        self.env.start()
        self.settings = Settings(configured=True, auto_hide=False)
        self.bar = Bar(self.settings)
        self.bar.show()
        self.app.processEvents()

    def tearDown(self):
        self.bar.hide_timer.stop()
        self.bar.edge_timer.stop()
        self.bar.tray.hide()
        self.bar.close()
        self.env.stop()
        self.temp.cleanup()

    def test_all_placements_and_resize_have_visible_commands(self):
        for position in ("top", "bottom", "right"):
            self.settings.position = position
            self.bar.apply_settings()
            self.app.processEvents()
            self.assertEqual(self.bar.canvas.vertical, position == "right")
            for i in range(self.bar.button_layout.count()):
                button = self.bar.button_layout.itemAt(i).widget()
                self.assertEqual(button.isVisible(),not (position=="top" and button is self.bar.quit_button))
                self.assertTrue(self.bar.buttons.rect().contains(button.geometry()), (position, button.geometry(), self.bar.buttons.rect()))
            self.assertFalse(self.bar.grab().isNull())

    def test_terminal_button_replaces_wiki_and_folder_without_height_regression(self):
        from unittest.mock import patch
        for height in (50,72,150):
            self.settings.thickness=height
            self.bar.apply_settings()
            self.app.processEvents()
            kinds=[button.property("icon_kind") for button in
                   self.bar.buttons.findChildren(type(self.bar.turbo))]
            self.assertIn("terminal",kinds)
            self.assertNotIn("wiki",kinds)
            self.assertNotIn("folder",kinds)
            self.assertEqual(self.bar.height(),height)
        with (
            patch("healthbar.app.shutil.which",return_value="/usr/bin/exo-open"),
            patch("healthbar.app.subprocess.Popen") as launching,
        ):
            self.bar.open_terminal()
            launching.assert_called_once()
            self.assertEqual(launching.call_args.args[0],
                             ["exo-open","--launch","TerminalEmulator"])

    def test_top_anchor_covers_selected_screen_and_has_zero_outer_margins(self):
        from types import SimpleNamespace
        cases = [QRect(0,0,1366,768),QRect(-1920,0,1920,1080),
                 QRect(1920,-200,2560,1440),QRect(0,0,3840,2160)]
        self.settings.position='top'
        self.settings.length_percent=100
        self.settings.alignment='center'
        self.settings.screen=1
        for bounds in cases:
            screens=[SimpleNamespace(geometry=lambda:QRect(0,0,800,600)),
                     SimpleNamespace(geometry=lambda rect=bounds:QRect(rect))]
            with patch('healthbar.app.QApplication.screens',return_value=screens):
                self.bar.apply_settings()
                self.app.processEvents()
                self.assertEqual(self.bar.geometry().left(),bounds.left())
                self.assertEqual(self.bar.geometry().top(),bounds.top())
                self.assertEqual(self.bar.geometry().width(),bounds.width())
                self.assertEqual(self.bar.geometry().right(),bounds.right())
                self.assertEqual(self.bar.geometry().center().x(),bounds.center().x())
        self.assertEqual(self.bar.root.getContentsMargins(),(0,0,0,0))

    def test_slim_default_and_hidden_top_quit_button_fit_small_screens(self):
        self.assertEqual(Settings().thickness,72)
        for height in (50,72,96,150):
            self.settings.thickness=height
            self.bar.apply_settings()
            self.app.processEvents()
            self.assertEqual(self.bar.height(),height)
            self.assertLessEqual(self.bar.maximumHeight(),150)
            self.assertFalse(self.bar.quit_button.isVisible())
            self.assertTrue(self.bar.expand_button.isVisible())
            self.assertTrue(self.bar.rect().contains(QRect(self.bar.expand_button.mapTo(self.bar,self.bar.expand_button.rect().topLeft()),self.bar.expand_button.size())))
        with patch.object(self.bar,'quit_app') as stop:
            self.bar.quit_button.clicked.disconnect()
            self.bar.quit_button.clicked.connect(stop)
            self.bar.quit_button.click()
            stop.assert_called_once()

    def test_modules_keep_responsive_click_and_hologram_bounds(self):
        from PySide6.QtCore import QPointF
        from healthbar.hud import HudCanvas
        canvas=HudCanvas(self.bar.registry)
        for width in (480,900,1600):
            for height in (50,72,150):
                canvas.resize(width,height)
                for order in (canvas.ORIGINAL,list(reversed(canvas.ORIGINAL))):
                    canvas.slot_order=order.copy()
                    for index,kind in enumerate(order):
                        bounds=canvas.module_rect(kind)
                        self.assertTrue(canvas.rect().contains(bounds))
                        self.assertEqual(canvas.module_at(QPointF(bounds.center())),index)
                        global_rect=canvas.module_global_rect(kind)
                        self.assertEqual(global_rect.size(),bounds.size())
        canvas.visual_timer.stop();canvas.close()
        self.settings.thickness=150
        self.bar.expanded=True
        self.bar.apply_settings()
        self.assertEqual(self.bar.height(),150)

    def test_compact_and_large_render(self):
        for width in (800, 1024, 1366, 2048):
            self.bar.resize(width, 200)
            self.app.processEvents()
            self.assertFalse(self.bar.grab().isNull())

    def test_background_is_clear_and_only_module_fills_follow_opacity(self):
        # Legacy skin contract; the new REDBLACK has intentionally opaque
        # data cavities and dedicated transparency tests in test_redblack_0822.
        self.settings.theme="blue-neon"
        from PySide6.QtCore import QPoint
        for opacity in (0, 35, 100):
            self.settings.opacity = opacity
            self.bar.apply_settings()
            self.bar.resize(2048, 200)
            self.app.processEvents()
            image = self.bar.grab().toImage()
            canvas = self.bar.canvas
            first=canvas.module_rect(canvas.slot_order[0])
            inside=canvas.mapTo(self.bar,first.topRight()+QPoint(-16,canvas.height()//2))
            blank=self.bar.actions.mapTo(self.bar,QPoint(10,self.bar.height()-10))
            button_fill = self.bar.turbo.mapTo(self.bar, QPoint(8, 40))
            self.assertLess(image.pixelColor(0, 0).alpha(), 64)  # PCB traces now span the window
            # The action area now contains PCB routes and the chip identity.
            self.assertAlmostEqual(image.pixelColor(inside).alpha(), round(255*opacity/100), delta=1)
            self.assertAlmostEqual(image.pixelColor(button_fill).alpha(), round(255*opacity/100), delta=1)
            # Text remains visible even when the module background is completely clear.
            baseline=max(34,min(canvas.height()*.6,80))
            dial_size=min(canvas.height()-14,first.width()*.36,92)
            text_rect=QRect(int(12+dial_size),int(baseline)-26,100,30)
            opaque_text = sum(image.pixelColor(canvas.mapTo(self.bar, QPoint(x, y))).alpha() == 255
                              for x in range(text_rect.left(), text_rect.right())
                              for y in range(text_rect.top(), text_rect.bottom()))
            self.assertGreater(opaque_text, 50)

    def test_retract_and_reveal_geometry(self):
        self.settings.auto_hide = True
        # Zero-duration transitions avoid OS-dependent window-manager timing.
        self.bar.animation.setDuration(0)
        with patch('healthbar.app.QCursor.pos', return_value=self.bar.full_rect.bottomRight() * 10):
            for position in ("top", "bottom", "right"):
                self.settings.position = position
                self.bar.apply_settings()
                full = QRect(self.bar.full_rect)
                self.bar.retract()
                self.assertTrue(self.bar.retracted)
                self.app.processEvents()
                hidden = self.bar.geometry()
                if position in ("top", "bottom"):
                    self.assertEqual(hidden.width(), full.width())
                    self.assertLess(hidden.height(), full.height())
                    self.assertEqual(hidden.top() if position == "top" else hidden.bottom(),
                                     full.top() if position == "top" else full.bottom())
                else:
                    self.assertEqual(hidden.height(), full.height())
                    self.assertLess(hidden.width(), full.width())
                    self.assertEqual(hidden.right(), full.right())
                self.bar.reveal()
                self.app.processEvents()
                self.assertEqual(self.bar.geometry(), full)

    def test_preferences_save_and_cancel(self):
        dialog = SettingsDialog(self.settings, self.app.screens(), first_run=True)
        dialog.opacity.setValue(42)
        dialog.reject()
        self.assertEqual(self.settings.opacity, 88)
        with patch('healthbar.dialogs.set_enabled') as register:
            dialog.save()
        register.assert_called_once_with(False)
        self.assertEqual(self.settings.opacity, 42)
        self.assertEqual(dialog.result(), QDialog.DialogCode.Accepted)


if __name__ == '__main__':
    unittest.main()
