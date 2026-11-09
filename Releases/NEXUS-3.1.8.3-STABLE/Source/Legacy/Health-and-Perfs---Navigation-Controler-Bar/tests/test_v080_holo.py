"""0.8.0: inspectable Holo identity and X11 navigation regressions."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from PySide6.QtWidgets import QApplication,QLabel
from healthbar.hardware_identity import compact_cpu_name,_memory_blocks,connected_interface_name
from healthbar.config import Settings
from healthbar.holo import CpuHoloPanel,SensorHoloPanel
from healthbar.hud import battery_meter,tachometer
from healthbar.bottom_dock import BottomDock
from healthbar.settings_visual import PCBSettingsDialog, BarPreview
from PySide6.QtGui import QImage,QPainter
from PySide6.QtCore import Qt,QRectF


class Holo08Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app=QApplication.instance() or QApplication([])

    def test_cpu_model_brand_compact(self):
        self.assertIn("Ryzen 7 1700X",
                      compact_cpu_name("AMD Ryzen 7 1700X Eight-Core Processor"))
        self.assertIn("i7-12700K",compact_cpu_name("Intel(R) Core(TM) i7-12700K CPU @ 3.60GHz"))

    def test_ram_inventory_is_truthful_and_never_live(self):
        text="""Memory Device
    Size: 8 GB
    Locator: DIMM_A
    Configured Memory Speed: 3200 MT/s
Memory Device
    Size: No Module Installed
Memory Device
    Size: 8 GB
    Locator: DIMM_B
    Speed: 3200 MT/s
"""
        rows=_memory_blocks(text)
        self.assertEqual(len(rows),2)
        self.assertEqual(rows[0]["speed"],"3200 MT/s")
        self.assertIsNone(rows[0]["live_clock_mhz"])
        self.assertIsNone(rows[0]["cl"])

    def test_connected_interfaces_only(self):
        details={"net_interface":"wlp3s0","net_interfaces":[
            {"name":"eth0","isup":False},
            {"name":"wlp3s0","isup":True}]}
        self.assertEqual(connected_interface_name(details),"Wi-Fi · wlp3s0")

    def test_cpu_title_and_topology_are_real(self):
        widget=CpuHoloPanel()
        try:
            widget.set_telemetry({"cpu_model":"AMD Ryzen 7 1700X Eight-Core Processor",
                                  "cpu_architecture":"x86_64",
                                  "cpu_physical_cores":8,"cpu_logical_cores":16,
                                  "cpu_power_w":64.5})
            self.assertIn("Ryzen 7 1700X",widget.findChild(QLabel,"holoTitle").text())
            self.assertIn("x86_64",widget.cpu_name.text())
            self.assertIn("16",widget.topology.text())
            self.assertIn("64.5",widget.summary.text())
        finally:
            widget.close()

    def test_fans_show_counts_and_only_known_maxima(self):
        with tempfile.TemporaryDirectory() as root,patch.dict(os.environ,HEALTHBAR_DATA_DIR=root):
            widget=SensorHoloPanel("fans")
            try:
                widget.set_telemetry({"fans":[
                    {"name":"Exhaust","rpm":6204,"percent_max":None},
                    {"name":"Intake","rpm":1200,"percent_max":60}],
                    "pc_temperature_c":43,"cpu_turbo_enabled":True})
                self.assertIn("2",widget.findChild(QLabel,"holoTitle").text())
                self.assertIn("TURBO : ON",widget.cpu_name.text())
                content=" ".join(w.text() for w in widget.grid_widget.findChildren(QLabel))
                self.assertIn("6204",content)
                self.assertIn("max inconnu",content)
                self.assertIn("60 %",content)
            finally:
                widget.close()

    def test_network_omits_disconnected(self):
        with tempfile.TemporaryDirectory() as root,patch.dict(os.environ,HEALTHBAR_DATA_DIR=root):
            widget=SensorHoloPanel("network")
            try:
                widget.set_telemetry({"net_interface":"wlan0","net_interfaces":[
                    {"name":"eth0","isup":False},{"name":"wlan0","isup":True}],
                    "net_down_mbs":1.2,"net_up_mbs":.2})
                self.assertIn("Wi-Fi",widget.findChild(QLabel,"holoTitle").text())
                content=" ".join(w.text() for w in widget.grid_widget.findChildren(QLabel))
                self.assertIn("wlan0",content)
                self.assertNotIn("eth0",content)
            finally:
                widget.close()

    def test_gauges_render_without_dependencies(self):
        image=QImage(190,65,QImage.Format.Format_ARGB32)
        image.fill(Qt.GlobalColor.transparent)
        painter=QPainter(image)
        battery_meter(painter,QRectF(0,0,130,28),53,"ram")
        tachometer(painter,QRectF(130,0,55,55),6204,8000,"RPM",show_value=False)
        painter.end()
        self.assertFalse(image.isNull())

    def test_custom_pcb_glass_renders_without_timer(self):
        panel=PCBSettingsDialog()
        try:
            panel.use_pcb_theme("blue-neon")
            panel.resize(960,610)
            image=QImage(panel.size(),QImage.Format.Format_ARGB32)
            image.fill(Qt.GlobalColor.transparent)
            panel.render(image)
            self.assertGreater(image.pixelColor(25,25).alpha(),0)
            preview=BarPreview("green-matrix")
            preview.resize(450,145)
            proof=QImage(preview.size(),QImage.Format.Format_ARGB32)
            proof.fill(Qt.GlobalColor.transparent)
            preview.render(proof)
            self.assertFalse(proof.isNull())
        finally:
            panel.close()

    def test_bottom_dock_no_longer_reserves_screen(self):
        with tempfile.TemporaryDirectory() as root,patch.dict(os.environ,HEALTHBAR_DATA_DIR=root):
            settings=Settings(dock_app_paths=[],bottom_nav_opacity=42)
            dock=BottomDock(settings)
            try:
                self.assertEqual(dock.body.glass_opacity,42)
                with patch("healthbar.bottom_dock.reserve_edge") as edge:
                    dock._reserve_workarea()
                    self.assertFalse(edge.call_args.args[-1])
            finally:
                dock.close()


if __name__=="__main__":
    unittest.main()
