"""NovaBar 0.8.1 Linux: transparency, context shortcuts, real SSD/network data."""
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage,QIcon
from PySide6.QtWidgets import QApplication,QInputDialog

from healthbar.config import Settings
from healthbar.network_detail import format_compact_rate,format_compact_ping
from healthbar.storage_identity import parse_lsblk,read_storage_identity
from healthbar.desktop_actions import rename_launcher,apt_owner
from healthbar.app_catalog import Application,ApplicationLauncher
from healthbar.bottom_dock import BottomDock,TaskButton,pinned_apps,ElectronToolButton
from healthbar.edge_docks import EdgeDock,PCBDockFrame
from healthbar.cockpit_style import CockpitFrame
from healthbar.app import NeonButton


class V081Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app=QApplication.instance() or QApplication([])

    @staticmethod
    def pixels(widget):
        image=QImage(widget.size(),QImage.Format.Format_ARGB32_Premultiplied)
        image.fill(Qt.GlobalColor.transparent)
        widget.render(image)
        return image

    def test_transparent_pcb_corners_reveal_background(self):
        settings=Settings(dock_folder_paths=[],dock_app_paths=[])
        for widget in (PCBDockFrame(settings),CockpitFrame(),NeonButton()):
            try:
                widget.resize(240,140)
                image=self.pixels(widget)
                self.assertEqual(image.pixelColor(0,0).alpha(),0,type(widget).__name__)
                self.assertGreater(image.pixelColor(60,55).alpha(),0)
            finally:
                widget.close()

    def test_network_short_one_decimal_mo_and_ping(self):
        self.assertEqual(format_compact_rate(0.567),"0.6 Mo/s")
        self.assertEqual(format_compact_rate(0),"0.0 Mo/s")
        self.assertEqual(format_compact_rate(None),"— Mo/s")
        self.assertEqual(format_compact_ping({"net_ping_ms":18.2}),"18ms")
        self.assertEqual(format_compact_ping({}),"—")

    def test_storage_identity_only_for_actual_root_disk(self):
        lsblk=json.dumps({"blockdevices":[
            {"name":"sda","type":"disk","tran":"sata","model":"Backup HDD",
             "children":[{"name":"sda1","type":"part","mountpoints":["/mnt/archive"]}]},
            {"name":"nvme0n1","type":"disk","tran":"nvme","vendor":"SAMSUNG",
             "model":"SSD 980 PRO",
             "children":[{"name":"nvme0n1p2","type":"part","mountpoints":["/"]}]}
        ]})
        result=parse_lsblk(lsblk)
        self.assertEqual(result["storage_model"],"SAMSUNG SSD 980 PRO")
        self.assertEqual(result["storage_technology"],"NVMe / PCIe")
        self.assertIsNone(result["storage_datasheet_read_mbs"])
        self.assertIsNone(parse_lsblk('{"blockdevices":[] }').get("storage_model"))

    def test_verified_datasheet_requires_exact_model_and_source(self):
        root=json.dumps({"blockdevices":[{"name":"nvme0n1","type":"disk",
            "model":"SSD Test","tran":"nvme","mountpoints":["/"]}]})
        from unittest.mock import Mock
        with tempfile.TemporaryDirectory() as tmp:
            catalog=Path(tmp)/"ssd_specs.json"
            catalog.write_text(json.dumps({"SSD Test":{
                "sequential_read_mbs":7000,"sequential_write_mbs":5000,
                "manufacturer_datasheet_url":"https://example.org/manufacturer-datasheet"}}))
            with patch("healthbar.storage_identity.subprocess.run",
                       return_value=Mock(returncode=0,stdout=root)):
                result=read_storage_identity(catalog)
            self.assertEqual(result["storage_datasheet_read_mbs"],7000)

    def test_rename_desktop_launcher_creates_user_override(self):
        with tempfile.TemporaryDirectory() as tmp,patch.dict(os.environ,XDG_DATA_HOME=tmp):
            src=Path(tmp)/"system.desktop"
            src.write_text("[Desktop Entry]\nType=Application\nName=Old App\nExec=/usr/bin/true\nIcon=system\n")
            with patch.object(QInputDialog,"getText",return_value=("New Name",True)):
                result=rename_launcher(src)
            self.assertEqual(Path(result).parent,Path(tmp)/"applications")
            content=Path(result).read_text()
            self.assertIn("Exec=/usr/bin/true",content)
            self.assertIn("Name=New Name",content)
            self.assertIn("Name[fr]=New Name",content)
            self.assertTrue(src.read_text().find("Old App")>0)

    def test_pinned_apps_independent_of_sidebar(self):
        settings=Settings(dock_app_paths=["/tmp/sidebar.desktop"],
                          bottom_pinned_apps=["/tmp/bottom.desktop"])
        self.assertEqual(pinned_apps(settings),["/tmp/bottom.desktop"])

    def test_sidebar_contains_no_settings_button(self):
        settings=Settings(dock_folder_paths=[],dock_app_paths=[])
        dock=EdgeDock("left","folders",settings)
        try:
            self.assertFalse(hasattr(dock,"options"))
            self.assertGreaterEqual(dock.content.layout().contentsMargins().left(),12)
        finally:
            dock.close()

    def test_saved_alias_validates_and_roundtrips(self):
        with tempfile.TemporaryDirectory() as tmp,patch.dict(os.environ,HEALTHBAR_DATA_DIR=tmp):
            settings=Settings(dock_aliases={"/home/demo/Documents":"Mes fichiers"},
                              bottom_pinned_apps=["/home/demo/Documents"])
            settings.save()
            loaded=Settings.load()
            self.assertEqual(loaded.dock_aliases["/home/demo/Documents"],"Mes fichiers")
            self.assertEqual(loaded.bottom_pinned_apps,["/home/demo/Documents"])
            with self.assertRaises(ValueError):
                Settings(dock_aliases={"abc":"invalid"+chr(10)+"value"}).validate()

    def test_real_launcher_has_shortcut_signal_and_click_delay(self):
        app=Application("/tmp/test.desktop","Demo","utilities-terminal","system")
        launcher=ApplicationLauncher("blue-neon",entries=[app],favorites=[])
        try:
            self.assertEqual(launcher.grid.count(),1)
            self.assertFalse(launcher._click_timer.isActive())
            launcher.queue_launch(launcher.grid.item(0))
            self.assertTrue(launcher._click_timer.isActive())
            launcher._click_timer.stop()
            self.assertEqual(launcher._queued_path,"/tmp/test.desktop")
        finally:
            launcher.close()


if __name__=="__main__":
    unittest.main()
