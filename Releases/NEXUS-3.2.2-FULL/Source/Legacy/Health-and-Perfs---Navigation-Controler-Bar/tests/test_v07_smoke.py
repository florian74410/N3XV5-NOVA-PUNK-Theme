"""Fast v0.7 Linux/Qt regression checks; do not mutate user's XFCE desktop."""
import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtWidgets import QApplication, QListWidget
from healthbar.config import Settings
from healthbar.module_preferences import defaults, normalize, load, save
from healthbar.shared_telemetry import SharedTelemetry


class ModuleOptionsTest(unittest.TestCase):
    def test_validation(self):
        raw=defaults()
        raw["cpu"]["refresh_seconds"]=0
        raw["gpu"]["refresh_seconds"]=7
        raw["network"]["details"]=["net_up_mbs","some_invalid_key"]
        clean=normalize(raw)
        self.assertEqual(clean["cpu"]["refresh_seconds"],2)
        self.assertEqual(clean["gpu"]["refresh_seconds"],7)
        self.assertEqual(clean["network"]["details"],["net_up_mbs"])

    def test_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            original=os.environ.get("HEALTHBAR_DATA_DIR")
            try:
                os.environ["HEALTHBAR_DATA_DIR"]=tmp
                data=defaults()
                data["cpu"]["holo_enabled"]=False
                data["gpu"]["refresh_seconds"]=9
                save(data)
                self.assertFalse(load()["cpu"]["holo_enabled"])
                self.assertEqual(load()["gpu"]["refresh_seconds"],9)
                self.assertTrue((Path(tmp)/"module-preferences.json").is_file())
            finally:
                if original is None:
                    os.environ.pop("HEALTHBAR_DATA_DIR",None)
                else:
                    os.environ["HEALTHBAR_DATA_DIR"]=original


class SharedTelemetryTest(unittest.TestCase):
    def test_cache_single_collector(self):
        class Dummy:
            def __init__(self): self.calls=0
            def sample(self):
                self.calls+=1
                return {"cpu_percent":12.5}
        now=[10.]
        dummy=Dummy()
        service=SharedTelemetry(sampler=dummy,clock=lambda:now[0])
        self.assertEqual(service.sample()["cpu_percent"],12.5)
        self.assertEqual(service.sample()["cpu_percent"],12.5)
        self.assertEqual(dummy.calls,1)
        now[0]+=3
        service.sample()
        self.assertEqual(dummy.calls,2)


class SettingsSmokeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.qt=QApplication.instance() or QApplication([])

    def test_sidebar_and_pages(self):
        # Do not save or open the XFCE panel changer in an automated test.
        from healthbar.dialogs import SettingsDialog
        win=SettingsDialog(Settings(configured=True), QApplication.screens())
        navigation=win.findChild(QListWidget,"settingsNavigation")
        self.assertIsNotNone(navigation)
        self.assertEqual(navigation.count(),13)
        self.assertEqual(len(win.module_controls),7)
        self.assertTrue(win.palette_preview.text())
        navigation.setCurrentRow(6)
        self.assertTrue(win.findChild(QListWidget,"settingsNavigation").currentRow()==6)
        win.close()


if __name__=="__main__":
    unittest.main()
