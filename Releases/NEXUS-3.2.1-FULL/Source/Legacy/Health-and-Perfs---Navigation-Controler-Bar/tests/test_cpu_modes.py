import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from healthbar.cpu_backends import LinuxBoostBackend, UnsupportedBackend
from healthbar.cpu_mode_controller import CpuModeController

class CpuModeTests(unittest.TestCase):
    def backend(self,folder,intel=False):
        path=Path(folder)/('intel_pstate/no_turbo' if intel else 'cpufreq/boost')
        path.parent.mkdir();path.write_text('1' if intel else '0')
        return LinuxBoostBackend(folder),path
    def test_real_sysfs_semantics_and_readback(self):
        for intel in (True,False):
            with tempfile.TemporaryDirectory() as folder:
                backend,path=self.backend(folder,intel)
                self.assertFalse(backend.read());self.assertTrue(backend.write(True))
                self.assertEqual(path.read_text(),'0' if intel else '1')
                self.assertFalse(backend.write(False))
    def test_no_hardware_change_on_launch_and_hysteresis(self):
        with tempfile.TemporaryDirectory() as folder:
            backend,path=self.backend(folder)
            controller=CpuModeController(backend)
            controller.sample(30);self.assertEqual(path.read_text(),'0')
            controller.select('auto')
            for temperature,expected in [(79,True),(84,True),(85,False),(84,False),(81,False),(80,True),(None,False),(float('nan'),False)]:
                with self.subTest(temperature=temperature):self.assertEqual(controller.sample(temperature)['enabled'],expected)
    def test_unavailable_or_denied_is_reported(self):
        controller=CpuModeController(UnsupportedBackend());controller.select('on')
        self.assertIsNotNone(controller.sample(55)['error'])
        with tempfile.TemporaryDirectory() as folder:
            backend,path=self.backend(folder);controller=CpuModeController(backend);controller.select('on')
            with patch('healthbar.cpu_backends.os.access',return_value=False):
                self.assertIn('lecture seule',controller.sample(40)['error'])
            self.assertEqual(path.read_text(),'0')
    def test_manual_and_external_changes_are_reconciled(self):
        with tempfile.TemporaryDirectory() as folder:
            backend,path=self.backend(folder);controller=CpuModeController(backend)
            controller.select('on');self.assertTrue(controller.sample(None)['enabled'])
            path.write_text('0');self.assertTrue(controller.sample(60)['enabled'])
            controller.select('off');self.assertFalse(controller.sample(60)['enabled'])
