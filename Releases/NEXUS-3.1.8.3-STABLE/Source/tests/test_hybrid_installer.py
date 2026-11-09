"""Non-destructive validation of the hybrid launcher contract."""
from pathlib import Path
import importlib.util
import tempfile
import unittest

HERE=Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location('hybrid_install',HERE/'scripts/install.py')
module=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)

class InstallerTests(unittest.TestCase):
    def test_launcher_keeps_v2_venv_and_isolated_user_data(self):
        launcher=module.make_launcher(Path('/tmp/demo/release'),Path('/tmp/v2/.venv/bin/python'))
        self.assertIn('/tmp/v2/.venv/bin/python',launcher)
        self.assertIn('HEALTHBAR_DATA_DIR="$HOME/.config/nexus-v3-hybrid"',launcher)
        self.assertIn('reference_shell',str(module.SHELL_REL))
        self.assertIn('flock -n 9',launcher)
        self.assertIn('PYTHONPATH=',launcher)
    def test_relative_asset_paths_are_v2_exact(self):
        self.assertEqual(module.TOP_REL.name,'n3xvs_top_native.py')
        self.assertEqual(module.BOTTOM_REL.name,'slim_style.py')
        self.assertEqual(module.SHELL_REL.name,'reference_shell.png')
    def test_backup_restore_regular_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            path=root/'a.desktop'
            path.write_text('original')
            backup=root/'b';backup.mkdir()
            entry=module.backup_file(path,backup)
            path.write_text('changed')
            module.restore_file(path,entry)
            self.assertEqual(path.read_text(),'original')
    def test_backup_restore_symlink(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            target=root/'target';target.write_text('safe')
            path=root/'link';path.symlink_to(target)
            backup=root/'b';backup.mkdir()
            entry=module.backup_file(path,backup)
            path.unlink();path.write_text('changed')
            module.restore_file(path,entry)
            self.assertTrue(path.is_symlink())
            self.assertEqual(path.resolve(),target)

if __name__=='__main__':unittest.main()
