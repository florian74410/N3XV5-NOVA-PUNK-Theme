import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from healthbar.plugins import PluginRegistry
from healthbar.telemetry import Telemetry
from scripts.build_plugins import build

class PluginV2Tests(unittest.TestCase):
    def test_all_seven_packs_import_and_reports(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch.dict(os.environ, HEALTHBAR_DATA_DIR=str(root)):
                count = build(root / "zip")
                self.assertEqual(count, 8)
                registry = PluginRegistry(root / "App" / "Plugins")
                for archive in sorted((root/"zip").glob("*.zip")):
                    manifest, digest = registry.inspect(archive)
                    self.assertEqual(manifest["api_version"], 2)
                    self.assertEqual(manifest["kind"], "builtin-sensor")
                    registry.install(archive, digest)
                    registry.set_enabled(manifest["id"], True)
                self.assertEqual(len(registry.installed()), 8)
                self.assertEqual(len(list((root/"App"/"Repports"/"Plugins").glob("REPORT-*.md"))), 8)

    def test_sample_has_stable_structure(self):
        data = Telemetry().sample()
        self.assertIn("cpu_percent", data)
        self.assertIn("gpu_power_w", data)
        self.assertIn("fans", data)
        self.assertIsInstance(data["fans"], list)

if __name__ == "__main__":
    unittest.main()
