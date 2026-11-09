import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

spec=importlib.util.spec_from_file_location('nexus_executable_packaging',Path(__file__).resolve().parents[1]/'scripts/package_executables.py')
packager=importlib.util.module_from_spec(spec);spec.loader.exec_module(packager)


class ExecutablePackagingTests(unittest.TestCase):
    @unittest.skipUnless(sys.platform.startswith('linux'),'The single-file launcher targets GNU/Linux')
    def test_single_file_integrity_check_and_corruption_rejection(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);archive=root/'runtime.zip'
            with zipfile.ZipFile(archive,'w') as package:
                item=zipfile.ZipInfo('HealthPerfsBar/HealthPerfsBar');item.external_attr=0o100755<<16
                package.writestr(item,b'test-runtime')
            output=packager.linux_run(archive,root/'installer.run','1.2.3')
            self.assertEqual(subprocess.run(['sh',str(output),'--check'],capture_output=True).returncode,0)
            self.assertEqual(subprocess.check_output(['sh',str(output),'--version']).strip(),b'1.2.3')
            data=output.read_bytes();output.write_bytes(data[:-1]+bytes([data[-1]^1]))
            self.assertNotEqual(subprocess.run(['sh',str(output),'--check'],capture_output=True).returncode,0)

    def test_native_deb_and_flatpak_sources_and_entrypoints(self):
        code = (Path(__file__).resolve().parents[1]/'scripts/package_linux_desktop.py').read_text()
        self.assertIn('dpkg-deb', code)
        self.assertIn('flatpak", "build-bundle"', code)
        self.assertIn('NOVABAR_PACKAGED=deb', code)
        self.assertIn('NOVABAR_PACKAGED=flatpak', code)
        self.assertIn('io.github.florian74410.NovaBar', code)
        self.assertIn('--filesystem=home', code)

    def test_native_packaged_launch_paths(self):
        from healthbar.autostart import launch_command
        from unittest.mock import patch
        with patch.dict(os.environ, NOVABAR_PACKAGED='deb'):
            self.assertEqual(launch_command(), ['/usr/bin/novabar'])
        with patch.dict(os.environ, NOVABAR_PACKAGED='flatpak'):
            self.assertEqual(launch_command(), ['flatpak', 'run', 'io.github.florian74410.NovaBar'])

    def test_new_version_retires_only_previous_downloaded_linux_packages(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)/'Executable/Linux';root.mkdir(parents=True)
            old_deb=root/'NovaBar_0.3.5_amd64.deb'
            old_flatpak=root/'NovaBar_0.3.5_x86_64.flatpak'
            note=root/'README.md'
            for path in (old_deb,old_flatpak,note):path.write_text('original')
            packager.retire_stale_linux_packages(root.parent)
            self.assertFalse(old_deb.exists())
            self.assertFalse(old_flatpak.exists())
            self.assertEqual(note.read_text(),'original')

    def test_unsafe_archive_paths_are_rejected_before_packaging(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);archive=root/'bad.zip'
            with zipfile.ZipFile(archive,'w') as package:package.writestr('../outside','bad')
            with self.assertRaises(ValueError):packager.linux_run(archive,root/'installer.run','1.2.3')
