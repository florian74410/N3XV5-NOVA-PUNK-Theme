"""Qt offscreen + plugin contract regression for CPU Holographic Details."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QRect, QPoint, Qt
from PySide6.QtTest import QTest
from healthbar.app import Bar
from healthbar.config import Settings
from healthbar.holo import CpuHoloPanel
from healthbar.cpu_detail import sample_cpu_cores
from healthbar.plugins import PluginRegistry
from scripts.build_plugins import build

class CPUHoloTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.qt = QApplication.instance() or QApplication([])

    def test_cpu_zip_has_declared_holo_and_imports(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            self.assertEqual(build(path / "archives"), 8)
            archive = path / "archives" / "cpu-manager-viewer-v2.1.0.zip"
            self.assertTrue(archive.exists())
            registry = PluginRegistry(path / "installed")
            manifest, digest = registry.inspect(archive)
            self.assertEqual(manifest["holo_view"], "cpu-core-matrix")
            self.assertEqual(manifest["version"], "2.1.0")
            registry.install(archive, digest)
            registry.set_enabled(manifest["id"], True)
            self.assertTrue(registry.installed()[0]["enabled"])


    def test_hud_click_opens_only_after_cpu_plugin_activated(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict(os.environ, HEALTHBAR_DATA_DIR=directory):
                bar = Bar(Settings(configured=True,auto_hide=False))
                bar.show()
                self.qt.processEvents()
                bar.open_module_holo("cpu")
                self.assertFalse(bar.holo.isVisible())
                build(Path(directory)/"packs")
                archive=Path(directory)/"packs"/"cpu-manager-viewer-v2.1.0.zip"
                manifest, digest=bar.registry.inspect(archive)
                bar.registry.install(archive,digest)
                bar.registry.set_enabled(manifest["id"],True)
                received=[]
                bar.canvas.module_activated.connect(received.append)
                QTest.mouseClick(bar.canvas, Qt.MouseButton.LeftButton, pos=bar.canvas.module_icon_rect("cpu").center())
                self.qt.processEvents()
                self.assertIn("cpu", received)
                self.assertTrue(bar.holo.isVisible())
                bar.holo.close_panel()
                bar.sensor_timer.stop()
                bar.edge_timer.stop()
                bar.tray.hide()
                bar.close()

    def test_core_frequency_labeling_does_not_mislabel_threads_as_cores(self):
        dummy = SimpleNamespace(
            cpu_count=lambda logical=True: 4 if logical else 2,
            cpu_freq=lambda percpu=True: [SimpleNamespace(current=v) for v in (2400,2200,2500,2300)]
        )
        with patch("healthbar.cpu_detail.topology",return_value=None):
            rows = sample_cpu_cores(dummy)
        self.assertEqual([row["label"] for row in rows],["Thread 0","Thread 1","Thread 2","Thread 3"])
        self.assertTrue(all(row["temperature_c"] is None and row["power_w"] is None for row in rows))

    def test_hologram_renders_real_and_missing_data_without_creating_fiction(self):
        holo = CpuHoloPanel()
        data = {"cpu_model":"Ryzen test","cpu_physical_cores":2,"cpu_logical_cores":4,
                "cpu_frequency_ghz":2.8,"cpu_temperature_c":55,"cpu_power_w":None,
                "cpu_percent":42,
                "cpu_cores":[{"label":"Core 0","frequency_ghz":2.7,"temperature_c":53,"power_w":None},
                             {"label":"Core 1","frequency_ghz":2.9,"temperature_c":55,"power_w":None}]}
        holo.set_telemetry(data)
        self.assertIn("PACKAGE",holo.summary.text())
        self.assertIn("—",holo.summary.text())
        self.assertEqual(holo.grid.itemAtPosition(3,0).widget().text(),"PACKAGE / TOTAL")
        bounds = QRect(0,0,1440,900)
        holo.show_at(QRect(200,0,310,150),bounds,"top")
        self.qt.processEvents()
        self.assertTrue(bounds.contains(holo.geometry()))
        self.assertTrue(holo.grab().width()>300)
        holo.toggle_pin(True)
        self.assertTrue(holo.pinned)
        holo.close_panel()
        holo.close()
