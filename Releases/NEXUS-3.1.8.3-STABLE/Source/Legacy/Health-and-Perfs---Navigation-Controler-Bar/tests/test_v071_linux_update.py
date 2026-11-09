"""NovaBar 0.7.1: Linux GVFS and verified APT update regressions."""
import json
import os
import runpy
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from healthbar.system_env import native_env
from healthbar.updates import check_native_release,prepare_native_update,NATIVE_LINEAGE

REPO="florian74410/Health-and-Perfs---Navigation-Controler-Bar"
BASE=f"https://github.com/{REPO}/releases/download/v0.7.6/"
DEB="NovaBar_0.7.6_amd64.deb"
ASSET={"name":DEB,"format":".deb","url":BASE+DEB,
       "sha256":"a"*64}
RELEASE={"tag_name":"v0.7.6","prerelease":False,"draft":False,
         "assets":[{"name":"novabar-bootstrap-manifest.json",
                    "browser_download_url":BASE+"novabar-bootstrap-manifest.json"},
                   {"name":DEB,"browser_download_url":BASE+DEB}]}
MANIFEST={"schema_version":1,"version":"0.7.6","lineage":NATIVE_LINEAGE,"packages":{"linux-x86_64":[ASSET]}}

class NativeUpdateTests(unittest.TestCase):
    def test_next_patch_selected_and_verified(self):
        releases=[{"tag_name":"v0.7.5","prerelease":False,"draft":False,
                   "assets":RELEASE["assets"]},RELEASE]
        with patch("healthbar.updates.read_url",side_effect=[
            json.dumps(releases).encode(),json.dumps(MANIFEST).encode()]), \
            patch("healthbar.updates.__version__","0.7.1"):
            result=check_native_release()
        self.assertEqual(result["version"],"0.7.6")
        self.assertTrue(result["native"])
        self.assertEqual(result["asset"]["url"],BASE+DEB)

    def test_historical_tags_are_not_offered(self):
        stale={"tag_name":"v0.7.5","prerelease":False,"draft":False,
               "assets":RELEASE["assets"]}
        with patch("healthbar.updates.read_url",
                   return_value=json.dumps([stale]).encode()), \
             patch("healthbar.updates.__version__","0.7.1"):
            self.assertIsNone(check_native_release())

    def test_prerelease_is_not_offered(self):
        release=dict(RELEASE,prerelease=True)
        with patch("healthbar.updates.read_url",
                   return_value=json.dumps([release]).encode()), \
             patch("healthbar.updates.__version__","0.7.1"):
            self.assertIsNone(check_native_release())

    def test_reject_deb_not_in_official_asset_list(self):
        bad=dict(RELEASE,assets=RELEASE["assets"][:1])
        with patch("healthbar.updates.read_url",side_effect=[
            json.dumps([bad]).encode(),json.dumps(MANIFEST).encode()]), \
            patch("healthbar.updates.__version__","0.7.1"):
            with self.assertRaises(ValueError):
                check_native_release()

    def test_native_env_clears_bundle_paths_for_apt(self):
        with patch.dict(os.environ,{"LD_LIBRARY_PATH":"/tmp/pyinstaller",
             "LD_LIBRARY_PATH_ORIG":"/usr/local/lib",
             "GIO_MODULE_DIR":"/tmp/gio-empty",
             "NOVABAR_ORIG_GIO_MODULE_DIR":"/usr/lib/gio/modules"},clear=False):
            env=native_env()
        self.assertEqual(env.get("LD_LIBRARY_PATH"),"/usr/local/lib")
        self.assertEqual(env.get("GIO_MODULE_DIR"),"/usr/lib/gio/modules")
        self.assertNotIn("NOVABAR_ORIG_GIO_MODULE_DIR",env)

    def test_runtime_hook_sets_private_gio_modules(self):
        root=Path(__file__).resolve().parents[1]
        hook=root/"scripts/runtime_linux_gio.py"
        with tempfile.TemporaryDirectory() as tmp:
            directory=Path(tmp)/"healthbar/assets/gio-empty"
            directory.mkdir(parents=True)
            with patch.object(sys,"frozen",True,create=True), \
                 patch.object(sys,"_MEIPASS",tmp,create=True), \
                 patch.dict(os.environ,{"GIO_MODULE_DIR":"/usr/lib/gio/modules"}):
                runpy.run_path(str(hook))
                self.assertEqual(os.environ["GIO_MODULE_DIR"],str(directory))
                self.assertEqual(os.environ["NOVABAR_ORIG_GIO_MODULE_DIR"],"/usr/lib/gio/modules")

    def test_deb_install_requires_identical_package_identity(self):
        from unittest.mock import Mock
        response=Mock(stdout="another-package\\n0.7.6\\namd64\\n")
        with patch.dict(os.environ,{"NOVABAR_PACKAGED":"deb"}), \
             patch("healthbar.bootstrapper.download") as download, \
             patch("healthbar.bootstrapper.install_package") as install, \
             patch("healthbar.updates.subprocess.run",return_value=response), \
             patch("healthbar.updates.__version__","0.7.1"):
            def fake_download(asset, directory):
                path=Path(directory)/DEB
                path.write_bytes(b"fake")
                return path
            download.side_effect=fake_download
            with self.assertRaises(ValueError):
                prepare_native_update({"version":"0.7.6","asset":ASSET,"native":True},lambda *args:None)
            install.assert_not_called()

if __name__=="__main__":
    unittest.main()
