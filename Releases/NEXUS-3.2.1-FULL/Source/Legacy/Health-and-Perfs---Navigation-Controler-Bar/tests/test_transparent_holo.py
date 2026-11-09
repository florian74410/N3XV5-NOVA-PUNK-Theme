import unittest
from unittest.mock import patch
from types import SimpleNamespace
from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QImage, QPainter
from PySide6.QtWidgets import QApplication
from healthbar.holo import CpuHoloPanel, SensorHoloPanel
from healthbar.hud import HudCanvas
from healthbar.telemetry import Telemetry

class TransparentHoloTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_panels_are_compact_with_uniform_glass_and_transparent_exterior(self):
        for panel in [CpuHoloPanel()] + [SensorHoloPanel(s) for s in SensorHoloPanel.FIELDS]:
            with self.subTest(panel=panel.windowTitle()):
                self.assertLessEqual(panel.width(), 460)
                self.assertLessEqual(panel.height(), 360 if getattr(panel, "slot", None) == "network" else 330)
                panel.show(); self.app.processEvents()
                panel._fade.setOpacity(1)
                self.assertFalse(panel.scroll.viewport().autoFillBackground())
                image = panel.grab().toImage()
                # Power has additional detail labels; sample the glass margin,
                # not a brightly painted value glyph near the grid's right edge.
                glass_x = panel.width()-18 if getattr(panel, "slot", None) == "power" else panel.width()-30
                self.assertAlmostEqual(image.pixelColor(glass_x, panel.height()//2).alpha(), 217, delta=2)
                self.assertEqual(image.pixelColor(0, 0).alpha(), 0)
                panel.show_at(QRect(400, 0, 100, 72), QRect(0, 0, 800, 600))
                self.assertTrue(QRect(0, 0, 800, 600).contains(panel.geometry()))
                panel.close()

    def test_network_details_scroll_and_missing_power_is_not_invented(self):
        panel = SensorHoloPanel('network')
        panel.set_telemetry({'net_interfaces':[{'name':'eth0','isup':True,'speed_mbps':1000,
                                              'down_mbs':12.5,'up_mbs':None}]})
        values = [panel.grid.itemAt(i).widget().text() for i in range(panel.grid.count())]
        self.assertIn('eth0', values); self.assertIn('1000 Mbit/s', values)
        self.assertIn('12.50 MB/s', values); self.assertIn('—', values)
        gpu = SensorHoloPanel('gpu'); gpu.set_telemetry({})
        self.assertEqual(gpu.grid.itemAtPosition(4,1).widget().text(), '—')
        panel.close(); gpu.close()

    def test_slim_dials_render_at_each_supported_height_and_keep_logo_click_targets(self):
        canvas = HudCanvas(SimpleNamespace(installed=lambda: []))
        canvas.set_telemetry({'cpu_frequency_ghz':2.7,'cpu_frequency_max_ghz':3.8,
                              'gpu_clock_mhz':1700,'ram_percent':42,'disk_percent':64})
        for width in (800, 1280, 1920):
            for height in (50,72,100,150):
                canvas.resize(width,height)
                image=QImage(width,height,QImage.Format.Format_ARGB32_Premultiplied)
                image.fill(Qt.GlobalColor.transparent)
                canvas.render(image)
                self.assertFalse(image.isNull())
                for slot in canvas.ORIGINAL:
                    self.assertTrue(canvas.module_rect(slot).contains(canvas.module_icon_rect(slot)))
        canvas.close()

    def test_network_rates_use_interface_deltas_and_first_sample_is_unknown(self):
        def counters(received, sent):
            return SimpleNamespace(bytes_recv=received,bytes_sent=sent)
        telemetry=Telemetry()
        values=iter([{'eth0':counters(100,200)}, {'eth0':counters(1000100,500200)}])
        def io(pernic=False):
            return next(values) if pernic else counters(0,0)
        with patch('healthbar.telemetry.psutil.net_io_counters',side_effect=io), \
             patch('healthbar.telemetry.psutil.net_if_stats',return_value={'eth0':SimpleNamespace(isup=True,speed=1000)}), \
             patch('healthbar.telemetry.time.monotonic',side_effect=[10,11]), \
             patch('healthbar.telemetry.nvidia_gpu',return_value={}), \
             patch('healthbar.telemetry.PingProbe.sample',return_value={}):
            first=telemetry.sample(); second=telemetry.sample()
        self.assertIsNone(first['net_interfaces'][0]['down_mbs'])
        self.assertEqual(second['net_interfaces'][0]['down_mbs'],1)
        self.assertEqual(second['net_interfaces'][0]['up_mbs'],.5)
