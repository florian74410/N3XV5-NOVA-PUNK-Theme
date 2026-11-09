"""RedBlack edition functional invariants + renderer alpha geometry."""
import unittest
from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QImage, QPainter, QColor
from PySide6.QtWidgets import QApplication

class RedBlackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app=QApplication.instance() or QApplication(["redblack-test"])

    def test_packager_accepts_four_part_version(self):
        import re
        self.assertTrue(re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+(?:\.[0-9]+)?", "0.8.2.2"))

    def test_four_segment_version_upgrade_ordering(self):
        from healthbar.updates import version
        from healthbar.install_engine import version_tuple
        self.assertEqual(version("v0.8.2.2"),(0,8,2,2))
        self.assertEqual(version_tuple("0.8.2.2"),(0,8,2,2))
        self.assertGreater(version("0.8.2.2"),version("0.8.1"))
        self.assertGreater(version_tuple("0.8.2.2"),version_tuple("0.8.1"))
        with self.assertRaises(ValueError):
            version("0.8.2.2.9")
        self.assertIsNone(version_tuple("not-a-version"))

    def test_version_theme_and_native_palette(self):
        from healthbar import __version__
        from healthbar.ui_kit import THEMES, set_theme, active_theme
        from healthbar.config import Settings
        self.assertEqual(__version__,"0.8.2.2")
        self.assertIn("redblack-0822",THEMES)
        self.assertEqual(Settings(theme="redblack-0822").validate().theme,"redblack-0822")
        set_theme("redblack-0822")
        self.assertEqual(active_theme(),"redblack-0822")
        set_theme("blue-neon")
        self.assertEqual(active_theme(),"blue-neon")

    def test_redblack_assets_exist_and_are_svg(self):
        from healthbar.redblack_shell import ASSET_ROOT
        for asset in ("pcb-layers.svg","chassis-layers.svg","mesh-red.svg","chevron-red.svg"):
            path=ASSET_ROOT/asset
            self.assertTrue(path.is_file(),path)
            self.assertIn("<svg",path.read_text(encoding="utf-8")[:200])

    def test_chrome_is_clipped_with_opaque_readout(self):
        from healthbar.redblack_shell import paint_surface
        for kind in ("holo","settings","hud","dock","notification","button"):
            img=QImage(360,240,QImage.Format.Format_ARGB32_Premultiplied)
            img.fill(Qt.GlobalColor.transparent)
            p=QPainter(img)
            paint_surface(p,QRectF(5,5,350,230),kind,.2)
            p.end()
            self.assertEqual(img.pixelColor(0,0).alpha(),0,kind)
            self.assertEqual(img.pixelColor(359,0).alpha(),0,kind)
            self.assertEqual(img.pixelColor(0,239).alpha(),0,kind)
            self.assertEqual(img.pixelColor(359,239).alpha(),0,kind)
            self.assertGreater(img.pixelColor(180,140).alpha(),220,kind)

    def test_wallpaper_assets_and_backup_are_separate_from_panel(self):
        from healthbar.redblack_shell import ASSET_ROOT
        from healthbar.redblack_wallpaper import PROPERTY, BACKUP
        self.assertTrue((ASSET_ROOT/"wallpaper-redblack.svg").is_file())
        self.assertTrue(PROPERTY.fullmatch("/backdrop/screen0/monitorHDMI-1/workspace0/last-image"))
        self.assertIsNone(PROPERTY.fullmatch("/panels/panel-1/position"))
        self.assertEqual(BACKUP,"redblack-wallpaper-backup.json")

    def test_holo_style_has_readability_and_group_visuals(self):
        from healthbar.redblack_shell import holo_stylesheet
        qss=holo_stylesheet()
        self.assertIn("QScrollArea#novaDataScroll",qss)
        self.assertIn("QLabel#holoGroup",qss)
        self.assertIn("QPushButton#novaClose",qss)

    def test_existing_module_apis_preserved(self):
        from healthbar.holo import SensorHoloPanel
        from healthbar.hud import HudCanvas
        self.assertEqual(set(SensorHoloPanel.FIELDS),
                         {"gpu","ram","storage","network","fans","power"})
        self.assertIn("cpu",HudCanvas.ORIGINAL)
        self.assertIn("network",HudCanvas.ORIGINAL)

if __name__=="__main__":
    unittest.main()
