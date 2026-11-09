import os
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path
from PySide6.QtWidgets import QApplication, QTabWidget
from PySide6.QtCore import Qt
from healthbar.config import Settings
from healthbar.ui_kit import set_theme, QColor
from healthbar.app import Bar
from healthbar.dialogs import SettingsDialog

class NextVisualTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.app=QApplication.instance() or QApplication([])

    def test_legacy_preferences_survive_migration(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, HEALTHBAR_DATA_DIR=folder):
            Path(folder,'settings.json').write_text('{"auto_hide":false,"opacity":67,"theme":"cyber-futuriste"}')
            settings=Settings.load()
            self.assertEqual(settings.retract_mode,'manual'); self.assertEqual(settings.opacity,67)
            settings.theme='green-matrix';settings.save()
            self.assertEqual(Settings.load().theme,'green-matrix')

    def test_themes_preserve_warning_colors(self):
        for theme in ('blue-neon','green-matrix','red-blood'):
            set_theme(theme)
            self.assertEqual(QColor('#ff0000').name(),'#ff0000')
            if theme!='blue-neon':self.assertNotEqual(QColor('#00d9ff').name(),'#00d9ff')
        set_theme('blue-neon')

    def test_manual_retract_and_wiki(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, HEALTHBAR_DATA_DIR=folder):
            settings=Settings(configured=True, auto_hide=False, retract_mode='manual')
            bar=Bar(settings);bar.show();self.app.processEvents()
            try:
                bar.retract();self.assertFalse(bar.retracted)
                bar.expand_button.click();self.assertTrue(bar.retracted)
                bar.reveal();self.assertFalse(bar.retracted)
                from PySide6.QtTest import QTest
                received=[];bar.canvas.module_activated.connect(received.append)
                QTest.mouseClick(bar.canvas,Qt.MouseButton.LeftButton,pos=bar.canvas.module_rect('cpu').center())
                self.assertEqual(received,['cpu'])
                QTest.mouseClick(bar.canvas,Qt.MouseButton.LeftButton,pos=bar.canvas.module_icon_rect('cpu').center())
                self.assertEqual(received,['cpu','cpu'])
                dialog=SettingsDialog(settings,self.app.screens())
                tabs=dialog.findChild(QTabWidget)
                self.assertIn('À propos',[tabs.tabText(i) for i in range(tabs.count())])
                dialog.close()
            finally:bar.close()

    def test_all_plugin_logos_toggle_holos_without_hover_or_value_activation(self):
        from scripts.build_plugins import build
        from PySide6.QtTest import QTest
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ,HEALTHBAR_DATA_DIR=folder):
            bar=Bar(Settings(configured=True,auto_hide=False));bar.sensor_timer.stop()
            build(Path(folder)/'packs')
            for archive in (Path(folder)/'packs').glob('*.zip'):
                manifest,digest=bar.registry.inspect(archive)
                bar.registry.install(archive,digest);bar.registry.set_enabled(manifest['id'],True)
            bar.show();bar.resize(1920,96);self.app.processEvents()
            try:
                for slot in bar.canvas.ORIGINAL:
                    panel=bar.holo if slot=='cpu' else bar.module_holos[slot]
                    QTest.mouseMove(bar.canvas,bar.canvas.module_icon_rect(slot).center())
                    self.app.processEvents();self.assertFalse(panel.isVisible())
                    QTest.mouseClick(bar.canvas,Qt.MouseButton.LeftButton,pos=bar.canvas.module_rect(slot).center())
                    self.assertTrue(panel.isVisible(),slot)
                    QTest.mouseClick(bar.canvas,Qt.MouseButton.LeftButton,pos=bar.canvas.module_icon_rect(slot).center())
                    self.assertFalse(panel.isVisible(),slot)
                    QTest.mouseClick(bar.canvas,Qt.MouseButton.LeftButton,pos=bar.canvas.module_icon_rect(slot).center())
                    self.assertTrue(panel.isVisible(),slot)
                    QTest.mouseClick(bar.canvas,Qt.MouseButton.LeftButton,pos=bar.canvas.module_icon_rect(slot).center())
                    self.assertFalse(panel.isVisible(),slot)
            finally:bar.close()
