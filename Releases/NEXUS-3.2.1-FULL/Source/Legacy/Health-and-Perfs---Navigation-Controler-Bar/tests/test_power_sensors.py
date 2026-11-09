"""Power plugin only publishes genuine sensor readings, not estimated watts."""
import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtWidgets import QApplication
from healthbar.holo import SensorHoloPanel
from healthbar.power_sensors import power_sensor_snapshot


class PowerSensorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_real_hwmon_volts_and_battery_watts_but_no_fake_wall_power(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            chip = root/"hwmon/hwmon0"
            chip.mkdir(parents=True)
            (chip/"in0_label").write_text("Vcore")
            (chip/"in0_input").write_text("1150")
            (chip/"in1_label").write_text("DIMM VDD")
            (chip/"in1_input").write_text("1200")
            battery = root/"power/BAT0"
            battery.mkdir(parents=True)
            (battery/"status").write_text("Discharging")
            (battery/"power_now").write_text("16400000")
            record = power_sensor_snapshot(root/"hwmon", root/"power")
            self.assertEqual(record["cpu_package_voltage_v"], 1.15)
            self.assertEqual(record["ram_voltage_rails"][0]["voltage_v"], 1.2)
            self.assertEqual(record["battery_discharge_w"], 16.4)
            self.assertIsNone(record["power_total_w"])
            self.assertIsNone(record["power_mains_voltage_v"])
            self.assertIsNone(record["gpu_vram_power_w"])

    def test_power_holo_separates_cpu_gpu_ram_and_unknown_values(self):
        panel = SensorHoloPanel("power")
        panel.set_telemetry({
            "cpu_power_w": 18.3,
            "cpu_cores": [{"core": 0, "power_w": None, "voltage_v": None}],
            "ram_voltage_rails": [{"name":"DIMM VDD", "voltage_v":1.2}],
            "battery_discharge_w": 15.2,
        })
        try:
            labels = [panel.grid.itemAt(i).widget().text() for i in range(panel.grid.count())]
            self.assertIn("⚡  VUE D'ENSEMBLE", labels)
            self.assertIn("◈  CPU", labels)
            self.assertIn("◈  GPU / VRAM", labels)
            self.assertIn("◈  RAM / RAILS", labels)
            self.assertIn("18.3 W", labels)
            self.assertIn("1.200 V", labels)
            self.assertIn("—", labels)
        finally:
            panel.close()


if __name__ == "__main__":
    unittest.main()
