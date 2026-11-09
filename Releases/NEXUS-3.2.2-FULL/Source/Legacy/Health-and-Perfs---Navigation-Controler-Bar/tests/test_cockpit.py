import os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage
from PySide6.QtWidgets import QApplication
from healthbar.app_catalog import catalog,Application,ApplicationLauncher
from healthbar.cockpit_style import CockpitFrame,app_icon
from healthbar.status_notifier import item_icon,item_address
from healthbar.system_status import read_status
from healthbar.bottom_dock import BottomDock,bottom_height
from healthbar.config import Settings

class CockpitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
    def test_catalog_categories_hidden_overrides_and_desktop_visibility(self):
        with tempfile.TemporaryDirectory() as temp:
            roots=[Path(temp)/'user',Path(temp)/'system']
            for r in roots:r.mkdir()
            def entry(root,name,extra):
                (root/name).write_text('[Desktop Entry]\nType=Application\nName='+name+'\nExec=true\n'+extra)
            entry(roots[0],'hidden.desktop','Hidden=true\n');entry(roots[1],'hidden.desktop','Categories=Office;\n')
            entry(roots[1],'browser.desktop','Categories=Network;WebBrowser;\nKeywords=internet;web;\n')
            entry(roots[1],'settings.desktop','Categories=Settings;\nOnlyShowIn=XFCE;\n')
            entry(roots[1],'foreign.desktop','OnlyShowIn=GNOME;\n')
            with patch.dict(os.environ,XDG_CURRENT_DESKTOP='XFCE'):
                apps=catalog(roots)
            self.assertEqual({a.name for a in apps},{'browser.desktop','settings.desktop'})
            self.assertEqual(apps[0].category,'internet');self.assertEqual(apps[1].category,'system')
    def test_launcher_filter_categories_and_favorites(self):
        entries=[Application('/a','Firefox','firefox','internet','web'),Application('/b','Terminal','utilities-terminal','system','console')]
        launch=ApplicationLauncher('blue-neon',favorites=['/b'],entries=entries)
        try:
            self.assertEqual(launch.grid.count(),2)
            launch.category='favorites';launch.filter();self.assertEqual(launch.grid.item(0).text(),'Terminal')
            launch.category='internet';launch.filter();self.assertEqual(launch.grid.count(),1)
            launch.category='all';launch.search.setText('console');self.assertEqual(launch.grid.item(0).text(),'Terminal')
            self.assertEqual(launch.grid.iconSize().width(),44)
        finally:launch.close()
    def test_cockpit_is_large_and_theme_changes_real_pixels(self):
        self.assertGreaterEqual(bottom_height(Settings()),80)
        frame=CockpitFrame('blue-neon');frame.resize(1000,88)
        first=QImage(frame.size(),QImage.Format.Format_ARGB32);first.fill(Qt.GlobalColor.transparent);frame.render(first)
        frame.theme='red-blood';second=QImage(frame.size(),QImage.Format.Format_ARGB32);second.fill(Qt.GlobalColor.transparent);frame.render(second)
        self.assertNotEqual(first,second);self.assertGreater(first.pixelColor(100,30).alpha(),200);frame.close()
    def test_argb_status_icon_is_decoded_in_correct_channel_order(self):
        icon=item_icon({'IconPixmap':[[1,1,bytes([255,220,40,10])]]})
        color=icon.pixmap(1,1).toImage().pixelColor(0,0)
        self.assertEqual((color.red(),color.green(),color.blue(),color.alpha()),(220,40,10,255))
        self.assertEqual(item_address(':1.45/custom/item'),(':1.45','/custom/item'))
        self.assertEqual(item_address('org.test.App'),('org.test.App','/StatusNotifierItem'))
    def test_native_status_handles_network_names_and_real_volume(self):
        replies=['wlan0:wifi:connected:My\\:Wifi\ntun0:tun:connected:VPN','Volume: front-left: 40000 / 61% / -8dB, front-right: 40000 / 61% / -8dB','Mute: yes','Controller ABC\n\tPowered: yes']
        with patch('healthbar.system_status.query',side_effect=replies),patch('healthbar.system_status.psutil.sensors_battery',return_value=None):state=read_status()
        self.assertEqual(state['network']['name'],'My:Wifi');self.assertEqual(state['volume'],61);self.assertTrue(state['muted']);self.assertTrue(state['bluetooth']);self.assertTrue(state['vpn'])
        with patch('healthbar.system_status.query',return_value=None),patch('healthbar.system_status.psutil.sensors_battery',return_value=None):state=read_status()
        self.assertIsNone(state['network']);self.assertIsNone(state['volume'])
    def test_status_buttons_expose_real_values_without_small_text_tabs(self):
        with tempfile.TemporaryDirectory() as temp,patch.dict(os.environ,HEALTHBAR_DATA_DIR=temp):
            dock=BottomDock(Settings(dock_app_paths=[]))
            try:
                dock.apply_status({'network':{'kind':'wifi','name':'QA','device':'wlan0'},'volume':43,'muted':False,'bluetooth':True,'battery':{'percent':72,'plugged':True},'vpn':False})
                self.assertIn('QA',dock.indicators['network'].toolTip());self.assertIn('43',dock.indicators['volume'].toolTip());self.assertIn('72',dock.indicators['battery'].toolTip())
                self.assertFalse(dock.indicators['volume'].icon().isNull());self.assertGreaterEqual(dock.menu_button.iconSize().width(),32)
            finally:dock.close()
    def test_colored_pack_icons_are_available_without_system_theme(self):
        from healthbar.cockpit_style import lookup_icon
        icon=lookup_icon('firefox');self.assertFalse(icon.isNull())
        image=icon.pixmap(48,48).toImage();colors={image.pixelColor(x,y).name() for x in range(0,48,4) for y in range(0,48,4) if image.pixelColor(x,y).alpha()>100}
        self.assertGreater(len(colors),4)

if __name__=='__main__':unittest.main()
