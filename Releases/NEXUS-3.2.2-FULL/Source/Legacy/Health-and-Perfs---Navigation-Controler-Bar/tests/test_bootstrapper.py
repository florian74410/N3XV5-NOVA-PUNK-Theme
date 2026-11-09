import hashlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from healthbar.bootstrapper import package_candidates, download, install_package, latest_package

BASE='https://github.com/florian74410/Health-and-Perfs---Navigation-Controler-Bar/releases/download/v0.5.0/'
def asset(name,content=b'package'):
    return {'name':name,'format':Path(name).suffix,'url':BASE+name,'sha256':hashlib.sha256(content).hexdigest()}
class BootstrapTests(unittest.TestCase):
    def test_select_native_packages_and_run_fallback(self):
        deb,run,exe=asset('NovaBar.deb'),asset('NovaBar.run'),asset('NovaBar.exe')
        manifest={'schema_version':1,'version':'0.5.0','packages':{'linux-x86_64':[run,deb],'windows-x86_64':[exe]}}
        self.assertEqual(package_candidates(manifest,'linux-x86_64'),deb)
        self.assertEqual(package_candidates(manifest,'linux-x86_64','.run'),run)
        self.assertEqual(package_candidates(manifest,'windows-x86_64'),exe)
        with self.assertRaises(ValueError):package_candidates(manifest,'linux-arm64')
        manifest['packages']['linux-x86_64']=[run]
        self.assertEqual(package_candidates(manifest,'linux-x86_64'),run)
    def test_checksum_rejection_removes_partial_download(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch('urllib.request.urlopen',return_value=io.BytesIO(b'corrupt')):
                with self.assertRaises(ValueError):download(asset('NovaBar.deb'),folder)
            self.assertEqual(list(Path(folder).iterdir()),[])
            with patch('urllib.request.urlopen',return_value=io.BytesIO(b'package')):
                self.assertEqual(download(asset('NovaBar.deb'),folder).read_bytes(),b'package')
    def test_foreign_host_and_traversal_rejected(self):
        for name,url in [('../bad.deb',BASE+'bad.deb'),('good.deb','https://evil.example/good.deb')]:
            item=asset('good.deb');item.update(name=name,url=url)
            with self.assertRaises(ValueError):package_candidates({'schema_version':1,'version':'0.5.0','packages':{'linux-x86_64':[item]}},'linux-x86_64')
    def test_install_failure_is_not_success(self):
        with patch('healthbar.bootstrapper.sys.platform','linux'),patch('healthbar.bootstrapper.os.geteuid',return_value=1000,create=True),patch('healthbar.bootstrapper.shutil.which',side_effect=lambda name:'/usr/bin/'+name),patch('healthbar.bootstrapper.subprocess.run') as run:
            run.return_value.returncode=1
            with self.assertRaises(OSError):install_package(Path('/tmp/package.deb'))
            self.assertEqual(run.call_args.args[0][:2],['/usr/bin/pkexec','/usr/bin/apt-get'])
    def test_unpublished_release_has_explicit_fallback(self):
        import json
        with patch('healthbar.bootstrapper.read_url',return_value=json.dumps({'tag_name':'v0.5.0','assets':[]}).encode()):
            with self.assertRaisesRegex(ValueError,'hors ligne'):latest_package()
