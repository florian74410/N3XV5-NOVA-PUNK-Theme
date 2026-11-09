import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('v3_switch',ROOT/'scripts/switch.py')
switch=importlib.util.module_from_spec(spec)
spec.loader.exec_module(switch)

class SwitchTests(unittest.TestCase):
    def test_autostart_reversible(self):
        with tempfile.TemporaryDirectory() as td:
            home=Path(td);auto=home/'.config/autostart'
            auto.mkdir(parents=True)
            original=b'[Desktop Entry]\nName=NativeV2\nExec=/bin/true\n'
            (auto/'n3xvs-hud.desktop').write_bytes(original)
            real=home/'real-link.desktop';real.write_text('ORIGINAL-LINK-TARGET')
            (auto/'novabar.desktop').symlink_to(real)
            old_auto=switch.AUTOSTART;old_state=switch.STATE
            try:
                switch.AUTOSTART=auto
                switch.STATE=home/'state/switch.json'
                switch.prepare(home/'backup')
                self.assertIn('Hidden=true',(auto/'n3xvs-hud.desktop').read_text())
                self.assertTrue((auto/'nexus-v3.desktop').exists())
                switch.restore()
                self.assertEqual(original,(auto/'n3xvs-hud.desktop').read_bytes())
                self.assertFalse((auto/'nexus-v3.desktop').exists())
                self.assertTrue((auto/'novabar.desktop').is_symlink())
                self.assertEqual('ORIGINAL-LINK-TARGET',real.read_text())
            finally:
                switch.AUTOSTART=old_auto;switch.STATE=old_state
