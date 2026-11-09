"""Unit tests for in-place plugin updates and GitHub source management (no network)."""
import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtWidgets import QApplication
from healthbar.plugin_sources import (
    DEFAULT_SOURCE, SourceStore, normalized_source, fetch_catalog, download_package
)
from healthbar.plugin_manager import PluginsDialog
from healthbar.plugins import PluginRegistry
from scripts.build_plugins import build

class SourceTests(unittest.TestCase):
    def test_source_validation_persistence_and_no_duplicates(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = SourceStore(Path(tmp)/"sources.json")
            self.assertEqual(store.load()[0]["folder"], "Plugins")
            custom = normalized_source("Other","https://github.com/example/plugins",
                                       branch="stable",folder="dist/zips")
            store.save([DEFAULT_SOURCE,custom])
            self.assertEqual(len(store.load()),2)
            with self.assertRaises(ValueError):
                store.save([custom,custom])
            for url in ("http://github.com/org/repo","https://evil.org/repo",
                        "https://github.com/org/repo?token=secret",
                        "https://github.com/org/../repo"):
                with self.assertRaises(ValueError):
                    normalized_source("Bad",url)
            for folder in ("../Plugins","Plugins/..","Plugins\\ZIP"):
                with self.assertRaises(ValueError):
                    normalized_source("Bad","https://github.com/org/repo",folder=folder)

    def test_catalog_selects_latest_version_across_git_sources(self):
        tree = {"tree":[
            {"path":"Plugins/cpu-manager-viewer-v1.0.0.zip","type":"blob","size":3000,"sha":"a"*40},
            {"path":"Plugins/cpu-manager-viewer-v2.1.0.zip","type":"blob","size":3500,"sha":"b"*40},
            {"path":"Plugins/gpu-manager-viewer-v1.0.0.zip","type":"blob","size":3000,"sha":"c"*40},
            {"path":"Plugins/subdir/ignore-v1.0.0.zip","type":"blob","size":3000,"sha":"d"*40},
        ]}
        with patch("healthbar.plugin_sources.request_bytes", return_value=json.dumps(tree).encode()):
            result, errors = fetch_catalog([DEFAULT_SOURCE])
        self.assertEqual(errors,[])
        self.assertEqual(result["cpu-manager-viewer"]["version"],"2.1.0")
        self.assertIn("raw.githubusercontent.com",result["cpu-manager-viewer"]["url"])
        self.assertEqual(len(result),2)

    def test_download_verifies_git_sha_and_rejects_changed_zip(self):
        sample = b"PK\x03\x04example-test"
        expected=hashlib.sha1(b"blob "+str(len(sample)).encode()+b"\x00"+sample).hexdigest()
        entry = {"url":"https://raw.githubusercontent.com/org/repo/main/Plugins/plug-v1.0.0.zip",
                 "blob_sha":expected}
        with tempfile.TemporaryDirectory() as tmp:
            with patch("healthbar.plugin_sources.request_bytes",return_value=sample):
                path,sha256=download_package(entry,Path(tmp)/"plug.zip")
            self.assertEqual(path.read_bytes(),sample)
            self.assertEqual(sha256,hashlib.sha256(sample).hexdigest())
            with patch("healthbar.plugin_sources.request_bytes",return_value=b"changed"):
                with self.assertRaises(ValueError):
                    download_package(entry,Path(tmp)/"changed.zip")

class UIManagerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_two_tabs_and_version_comparison_without_updating_runtime(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            registry=PluginRegistry(root/"plugins")
            sources=SourceStore(root/"sources.json")
            sources.save([DEFAULT_SOURCE])
            manager=PluginsDialog(registry,source_store=sources)
            manager.remote={"cpu-manager-viewer":{
                "id":"cpu-manager-viewer","source":"NovaBar Official","version":"2.0.0",
                "url":"https://raw.githubusercontent.com/org/r/main/Plugins/cpu.zip",
                "filename":"cpu-manager-viewer-v2.1.0.zip","blob_sha":"a"*40}}
            manager.refresh()
            self.assertEqual(manager.tabs.count(),2)
            self.assertEqual(manager.table.rowCount(),1)
            manager.table.selectRow(0)
            self.assertEqual(manager.table.item(0,1).text(),"—")
            self.assertEqual(manager.table.item(0,2).text(),"2.0.0")
            self.assertTrue(manager.install_button.isVisible() if manager.isVisible()
                            else not manager.install_button.isHidden())
            manager.close()

    def test_compatible_zip_updates_without_installing_program_or_executing_shell(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            build(root/"zip")
            archive=root/"zip"/"cpu-manager-viewer-v2.1.0.zip"
            registry=PluginRegistry(root/"installed")
            manifest,digest=registry.inspect(archive)
            manager=PluginsDialog(registry,source_store=SourceStore(root/"sources.json"))
            self.assertIsNone(manager.compatible(manifest))
            with patch("healthbar.plugin_manager.QMessageBox.question",
                       return_value=QMessageBox.StandardButton.Yes):
                manager.confirm_install(str(archive),manifest,digest)
            self.assertEqual(registry.installed()[0]["version"],"2.1.0")
            self.assertTrue((registry.root/"cpu-manager-viewer"/"Hologram"/"holo.json").is_file())
            manager.close()

from PySide6.QtWidgets import QMessageBox

if __name__ == "__main__":
    unittest.main()
