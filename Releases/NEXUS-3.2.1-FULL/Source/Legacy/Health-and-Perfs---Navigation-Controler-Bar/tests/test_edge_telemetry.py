"""Regression coverage for the always-visible collapsed telemetry edge strip."""
import os
import tempfile
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QRectF
from PySide6.QtGui import QImage, QPainter
from PySide6.QtWidgets import QApplication, QWidget

from healthbar.app import Bar
from healthbar.config import Settings
from healthbar.hud import HudCanvas, battery_meter, tachometer


class EmptyRegistry:
    def installed(self):
        return []


class EdgeTelemetryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_collapsed_layout_does_not_expose_holo_icons(self):
        parent = QWidget()
        parent.retracted = True
        canvas = HudCanvas(EmptyRegistry(), parent=parent)
        canvas.visual_timer.stop()
        canvas.set_telemetry({
            "cpu_temperature_c": 61, "cpu_frequency_ghz": 3.1,
            "gpu_temperature_c": 56, "gpu_clock_mhz": 1650,
            "ram_percent": 41, "disk_percent": 47,
            "fans": [{"name": "CPU", "rpm": 1520}],
            "net_down_mbs": 3.2, "net_up_mbs": 1.4,
        })
        try:
            for vertical, width, height in ((False, 1280, 30), (False, 480, 30),
                                            (True, 66, 720), (True, 44, 360)):
                canvas.vertical = vertical
                canvas.resize(width, height)
                for index, kind in enumerate(canvas.slot_order):
                    rect = canvas.module_rect(kind)
                    self.assertTrue(canvas.rect().contains(rect), (kind, rect))
                    self.assertEqual(canvas.module_at(rect.center()), index)
                    self.assertTrue(canvas.module_icon_rect(kind).isEmpty())
                image = QImage(width, height, QImage.Format.Format_ARGB32_Premultiplied)
                image.fill(0)
                canvas.render(image)
                self.assertFalse(image.isNull())
                self.assertNotEqual(image.pixelColor(width//12, height//2).alpha(), 0)
            parent.retracted = False
            canvas.vertical = False
            canvas.resize(1280, 72)
            self.assertFalse(canvas.module_icon_rect("cpu").isEmpty())
        finally:
            canvas.close()
            parent.close()

    def test_gauge_and_batteries_render_for_real_and_missing_values(self):
        for number, unit in ((2.8, "GHz"), (1640, "RPM"), (None, "GHz")):
            image = QImage(90, 90, QImage.Format.Format_ARGB32_Premultiplied)
            image.fill(0)
            p = QPainter(image)
            tachometer(p, QRectF(10, 10, 70, 70), number, 3000 if unit == "RPM" else 3.5, unit)
            p.end()
            self.assertFalse(image.isNull())
            self.assertGreater(image.pixelColor(45, 12).alpha(), 0)
        def battery_snapshot(percent):
            image = QImage(82, 30, QImage.Format.Format_ARGB32_Premultiplied)
            image.fill(0)
            p = QPainter(image)
            battery_meter(p, QRectF(0, 1, 79, 27), percent, "ram")
            p.end()
            return image
        full, empty, missing = battery_snapshot(100), battery_snapshot(0), battery_snapshot(None)
        self.assertNotEqual(full.pixelColor(8, 14).name(), empty.pixelColor(8, 14).name())
        self.assertEqual(empty.pixelColor(8, 14).name(), missing.pixelColor(8, 14).name())

    def test_retraction_shrinks_window_without_moving_entire_bar_offscreen(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, HEALTHBAR_DATA_DIR=folder):
            bar = Bar(Settings(configured=True, auto_hide=False, retract_mode="manual"))
            bar.show()
            bar.sensor_timer.stop()
            bar.animation.setDuration(0)
            self.app.processEvents()
            try:
                for position in ("top", "bottom", "left", "right"):
                    bar.settings.position = position
                    bar.apply_settings()
                    self.app.processEvents()
                    full = bar.full_rect
                    bar.retract(manual=True)
                    self.app.processEvents()
                    self.assertTrue(bar.retracted)
                    self.assertFalse(bar.actions.isVisible())
                    self.assertTrue(bar.canvas.module_icon_rect("gpu").isEmpty())
                    current = bar.geometry()
                    if position in ("top", "bottom"):
                        self.assertLess(current.height(), full.height())
                        self.assertGreaterEqual(current.height(), 26)
                        self.assertEqual(current.top() if position == "top" else current.bottom(),
                                         full.top() if position == "top" else full.bottom())
                    else:
                        self.assertLess(current.width(), full.width())
                        self.assertGreaterEqual(current.width(), 22)
                        self.assertEqual(current.left() if position == "left" else current.right(),
                                         full.left() if position == "left" else full.right())
                    bar.reveal()
                    self.app.processEvents()
                    self.assertFalse(bar.retracted)
                    self.assertEqual(bar.geometry(), full)
                    self.assertTrue(bar.actions.isVisible())
                    self.assertFalse(bar.canvas.module_icon_rect("gpu").isEmpty())
            finally:
                bar.edge_timer.stop()
                bar.tray.hide()
                bar.close()


if __name__ == "__main__":
    unittest.main()
