"""Autonomous dock, invisible edge triggers and verified-updater UI regressions."""
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch,Mock
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from PySide6.QtCore import QPoint,QRect
from PySide6.QtWidgets import QApplication
from healthbar.config import Settings
from healthbar.edge_docks import EdgeDock
from healthbar.bottom_dock import BottomDock
from healthbar.desktop_backend import NativePanelGuard
from healthbar.updates import UpdateDialog
from healthbar.install_engine import write_shortcuts,refresh_active_shortcuts
from healthbar.system_env import native_env

class BottomUpgradeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])

    def test_collapsed_edges_are_hidden_but_trigger_exactly_within_ten_pixels(self):
        for side in ('left','right'):
            dock=EdgeDock(side,'folders',Settings(dock_folder_paths=[],dock_app_paths=[]))
            try:
                dock.full_rect=(0 if side=='left' else 750,60,250,600);dock.collapse()
                self.assertFalse(dock.isVisible())
                outside=QPoint(10 if side=='left' else 989,100)
                inside=QPoint(9 if side=='left' else 990,100)
                with patch('healthbar.edge_docks.QCursor.pos',return_value=outside):dock.check_pointer()
                self.assertTrue(dock.collapsed)
                # Requires 1 full continuous second inside the 10 px edge.
                with patch('healthbar.edge_docks.QCursor.pos',return_value=inside), patch('healthbar.edge_docks.time.monotonic',side_effect=[5.0,5.9,6.01]):
                    dock.check_pointer();self.assertTrue(dock.collapsed)
                    dock.check_pointer();self.assertTrue(dock.collapsed)
                    dock.check_pointer()
                self.assertTrue(dock.isVisible());self.assertFalse(dock.collapsed)
                with patch('healthbar.edge_docks.QCursor.pos',return_value=QPoint(500,400)):dock.check_pointer()
                self.assertEqual(dock.hide_timer.interval(),3000);self.assertTrue(dock.hide_timer.isActive())
                dock.collapse();self.assertFalse(dock.isVisible())
            finally:dock.close()

    def test_bottom_exists_without_xfce_and_reveals_from_bottom_edge(self):
        with tempfile.TemporaryDirectory() as temp,patch.dict(os.environ,HEALTHBAR_DATA_DIR=temp):
            dock=BottomDock(Settings(dock_app_paths=[]))
            try:
                self.assertTrue(dock.isVisible());self.assertTrue(dock.menu_button.isVisible())
                bounds=self.app.primaryScreen().geometry()
                self.assertEqual(dock.geometry().bottom(),bounds.bottom())
                dock.collapse();self.assertFalse(dock.isVisible())
                with patch('healthbar.bottom_dock.QCursor.pos',return_value=QPoint(bounds.center().x(),bounds.bottom()-9)):
                    dock.check_pointer()
                self.assertTrue(dock.isVisible())
                rows=[{'id':15,'name':'Test window','icon':'missing-icon'}]
                with patch.object(dock.backend,'snapshot',return_value=(rows,15)):
                    dock.refresh()
                button=dock.tasks.itemAt(0).widget()
                with patch.object(dock.backend,'action') as action:
                    button.click();action.assert_called_once_with(15,minimize=True)
            finally:dock.close()

    def test_native_backup_precedes_hide_and_restores_on_exit(self):
        with tempfile.TemporaryDirectory() as temp,patch.dict(os.environ,HEALTHBAR_DATA_DIR=temp),patch('healthbar.desktop_backend.x11_ready',return_value=True),patch('psutil.Process') as process:
            process.return_value.create_time.return_value=123.0
            backend=Mock();backend.native_bottom_panels.return_value=[{'id':22,'pid':200}]
            guard=NativePanelGuard(backend)
            def visibility(rows,visible):
                if not visible:self.assertEqual(json.loads(guard.path.read_text())['panels'],rows)
                return True
            backend.set_panel_visible.side_effect=visibility
            with patch('healthbar.desktop_backend.subprocess.Popen'):
                guard.hide(QRect(0,0,1280,720))
            backend.set_panel_visible.assert_called_with([{'id':22,'pid':200}],False)
            guard.reveal();self.assertGreater(guard.reveal_until,0)
            self.assertTrue(guard.restore());self.assertFalse(guard.path.exists())
            backend.set_panel_visible.assert_called_with([{'id':22,'pid':200}],True)

    def test_no_native_hide_if_restore_watchdog_cannot_start(self):
        with tempfile.TemporaryDirectory() as temp,patch.dict(os.environ,HEALTHBAR_DATA_DIR=temp),patch('healthbar.desktop_backend.x11_ready',return_value=True),patch('psutil.Process') as process:
            process.return_value.create_time.return_value=123.0
            backend=Mock();backend.native_bottom_panels.return_value=[{'id':1,'pid':2}]
            guard=NativePanelGuard(backend)
            with patch('healthbar.desktop_backend.subprocess.Popen',side_effect=OSError('unavailable')):guard.hide(QRect())
            backend.set_panel_visible.assert_not_called();self.assertFalse(guard.path.exists())

    def test_recovers_stale_native_backup(self):
        with tempfile.TemporaryDirectory() as temp,patch.dict(os.environ,HEALTHBAR_DATA_DIR=temp,DISPLAY=':99'):
            path=Path(temp)/'native-panel-visibility.json'
            rows=[{'id':3,'pid':4}]
            path.write_text(json.dumps({'owner':os.getpid(),'owner_started':0,'display':':99','panels':rows}))
            backend=Mock();backend.set_panel_visible.return_value=True
            NativePanelGuard(backend)
            backend.set_panel_visible.assert_called_once_with(rows,True);self.assertFalse(path.exists())

    def test_upgrade_progresses_check_install_restart_and_errors_remain_visible(self):
        with patch('healthbar.updates.QTimer.singleShot') as schedule:
            dialog=UpdateDialog(auto_upgrade=True);dialog.worker=Mock()
            try:
                self.assertEqual(schedule.call_args.args[0],0)
                release={'version':'99.0.0'};dialog.checked(release)
                self.assertEqual(dialog.release,release)
                self.assertEqual(dialog.button.text(),"Installer la mise à jour")
                self.assertEqual(schedule.call_count,1)  # Auto-check only; no silent install.
                dialog.completed({'executable':'new-runtime'})
                self.assertEqual(dialog.button.text(),"Redémarrer NovaBar")
                self.assertEqual(schedule.call_count,1)  # Restart requires confirmation.
                dialog.failed('Checksum failed');self.assertEqual(dialog.label.text(),'Checksum failed')
            finally:dialog.close()

    @unittest.skipUnless(__import__('sys').platform.startswith('linux'),'Linux desktop IDs')
    def test_upgrade_shortcut_overrides_packaged_desktop_id(self):
        with tempfile.TemporaryDirectory() as temp,patch.dict(os.environ,XDG_DATA_HOME=temp):
            write_shortcuts(Path(temp)/'runtime/new version/NovaBar')
            apps=Path(temp)/'applications'
            self.assertIn('new version',(apps/'io.github.florian74410.NovaBar.desktop').read_text())
            self.assertIn('NoDisplay=true',(apps/'novabar.desktop').read_text())

    def test_autostart_uses_activated_runtime_even_with_old_deb_environment(self):
        from healthbar.autostart import launch_command
        import sys
        with patch.dict(os.environ,NOVABAR_PACKAGED='deb'),patch.object(sys,'frozen',True,create=True),patch('healthbar.install_engine.read_installed_state',return_value={'executable':sys.executable}):
            self.assertEqual(launch_command(),[sys.executable])

    def test_native_commands_do_not_inherit_frozen_qt_or_glib_libraries(self):
        with patch.dict(os.environ,LD_LIBRARY_PATH='/tmp/bundle',LD_LIBRARY_PATH_ORIG='/system/lib',QT_PLUGIN_PATH='/bundle/qt'):
            env=native_env();self.assertEqual(env['LD_LIBRARY_PATH'],'/system/lib');self.assertNotIn('QT_PLUGIN_PATH',env)

if __name__=='__main__':unittest.main()
