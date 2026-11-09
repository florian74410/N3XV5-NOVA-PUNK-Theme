import json
import os
import tempfile
import unittest
import zipfile
from dataclasses import asdict
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from PySide6.QtWidgets import QApplication
from healthbar.config import Settings, data_dir
from healthbar.installer import InstallerWizard
from healthbar.profiles import workspace_dir, save_profile, current_profile
from healthbar.install_engine import install, install_root, cleanup_obsolete_runtimes, read_installed_state
from healthbar.updates import extract_runtime, version, asset_url, check_release
from healthbar.contact import send_feedback, SMTPConfig
from healthbar.platforms import validate_host


class InstallerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.env=patch.dict(os.environ,HEALTHBAR_DATA_DIR=str(self.root/'data'),
                            HEALTHBAR_DOCUMENTS_DIR=str(self.root/'Documents'),
                            HEALTHBAR_INSTALL_ROOT=str(self.root/'runtime'))
        self.env.start()
    def tearDown(self):self.env.stop();self.temp.cleanup()

    def test_identity_acceptance_and_profile_survive_preference_changes(self):
        wizard=InstallerWizard(Settings())
        self.assertFalse(wizard.next.isEnabled())
        self.assertTrue(wizard.share.isChecked())
        wizard.accept_terms.setChecked(True)
        key='windows11' if os.name=='nt' else 'macos' if __import__('sys').platform=='darwin' else 'ubuntu'
        wizard.os_choice.setCurrentIndex(wizard.os_choice.findData(key))
        wizard.email.setText('test@example.org')
        wizard.advance()
        self.assertEqual(wizard.stack.currentIndex(),1)
        path=workspace_dir()/'App/Profiles'/(current_profile()+'.json')
        self.assertEqual(json.loads(path.read_text())['identity']['email'],'test@example.org')
        settings=Settings(opacity=27,position='left',shortcuts=[{'action':'toggle','sequence':'Ctrl+B'}]);settings.save()
        record=json.loads(path.read_text())
        self.assertEqual(record['identity']['email'],'test@example.org')
        self.assertEqual(record['preferences']['opacity'],27)
        self.assertTrue((workspace_dir()/'Profiles'/path.name).is_file())
        wizard.header.timer.stop();wizard.close()

    def test_reopening_preserves_opt_out_identity_and_installation_metadata(self):
        save_profile({'username':'Flo','email':'keep@example.org','share_experience':False},
                     asdict(Settings()),{'version':'0.2.0','executable':'previous'})
        wizard=InstallerWizard(Settings(configured=True,autostart=False))
        self.assertEqual(wizard.email.text(),'keep@example.org')
        self.assertEqual(wizard.username.text(),'Flo')
        self.assertFalse(wizard.share.isChecked())
        self.assertFalse(wizard.autostart.isChecked())
        save_profile({'username':'Flo','email':'keep@example.org','share_experience':False},asdict(Settings()))
        path=workspace_dir()/'App/Profiles'/(current_profile()+'.json')
        self.assertEqual(json.loads(path.read_text())['installation']['version'],'0.2.0')
        wizard.header.timer.stop();wizard.close()

    def test_existing_plugins_migrate_into_precreated_empty_workspace(self):
        from healthbar.profiles import ensure_workspace
        from healthbar.plugins import PluginRegistry
        ensure_workspace()
        old=data_dir()/'App/Plugins/old-slot';old.mkdir(parents=True)
        (old/'manifest.json').write_text(json.dumps({'id':'old-slot','name':'Existing','version':'1.0.0',
            'api_version':1,'kind':'declarative','slot':'cpu'}))
        (old/'state.json').write_text('{"enabled":true}')
        registry=PluginRegistry()
        self.assertEqual(registry.installed()[0]['name'],'Existing')
        self.assertTrue(old.exists())
        self.assertEqual(registry.root,workspace_dir()/'Plugins')

    def test_legacy_choice_cannot_be_enabled_by_selecting_another_family(self):
        with self.assertRaises(ValueError):validate_host('high-sierra')
        wrong='macos' if __import__('sys').platform!='darwin' else 'windows11'
        with self.assertRaises(ValueError):validate_host(wrong)

    def test_shortcut_editor_detects_duplicates_and_restores_saved_draft(self):
        wizard=InstallerWizard(Settings())
        wizard.add_binding('expand','Ctrl+B')
        with self.assertRaises(ValueError):wizard.bindings()
        wizard.keys.removeRow(1)
        wizard.save_binding_draft()
        wizard.keys.removeRow(0)
        wizard.reset_bindings()
        self.assertEqual(wizard.bindings(),[{'action':'toggle','sequence':'Ctrl+B'}])
        wizard.header.timer.stop();wizard.close()

    def test_failed_payload_test_never_activates_version(self):
        payload=self.root/'payload';(payload/'HealthPerfsBar').mkdir(parents=True)
        name='HealthPerfsBar.exe' if os.name=='nt' else 'HealthPerfsBar'
        (payload/'HealthPerfsBar'/name).write_bytes(b'fake-binary')
        identity={'os':'ubuntu','email':'local@example.org'}
        with patch('healthbar.install_engine.validate_host'),patch('healthbar.install_engine.self_test',side_effect=RuntimeError('test failure')):
            with self.assertRaises(RuntimeError):install(Settings(),identity,False,lambda *args:None,payload=payload)
        self.assertFalse((install_root()/'installation.json').exists())
        self.assertFalse((data_dir()/'settings.json').exists())

    def test_existing_version_reconfigures_without_copying_payload(self):
        from healthbar import __version__
        target=install_root()/'versions'/__version__/'HealthPerfsBar';target.mkdir(parents=True)
        name='HealthPerfsBar.exe' if os.name=='nt' else 'HealthPerfsBar'
        (target/name).write_bytes(b'original')
        with patch('healthbar.install_engine.validate_host'),patch('healthbar.install_engine.self_test'),patch('healthbar.install_engine.activate',return_value={'version':__version__}) as activation:
            result=install(Settings(),{'os':'ubuntu'},False,lambda *args:None,payload=self.root/'does-not-exist')
        self.assertEqual(result['version'],__version__);activation.assert_called_once()
        self.assertEqual((target/name).read_bytes(),b'original')

    def test_upgrade_prunes_only_old_version_folders(self):
        from healthbar import __version__
        root=install_root();versions=root/'versions'
        older=versions/'0.3.3';older.mkdir(parents=True)
        (older/'app.bin').write_text('old')
        future=versions/'99.0.0';future.mkdir()
        custom=versions/'do-not-touch';custom.mkdir()
        active=versions/__version__;active.mkdir()
        user=data_dir()/'App/Plugins/installed';user.mkdir(parents=True)
        (user/'manifest.json').write_text('plugin')
        (root/'installation.json').write_text(json.dumps({'version':__version__}))
        removed=cleanup_obsolete_runtimes(root,__version__)
        self.assertEqual(removed,['0.3.3'])
        self.assertFalse(older.exists())
        self.assertTrue(active.exists())
        self.assertTrue(future.exists())
        self.assertTrue(custom.exists())
        self.assertTrue((user/'manifest.json').is_file())

    def test_upgrade_never_erases_old_runtime_before_new_is_verified(self):
        from healthbar import __version__
        old=install_root()/'versions'/'0.3.3';old.mkdir(parents=True)
        (old/'keep.txt').write_text('restore point')
        install_root().mkdir(parents=True,exist_ok=True)
        (install_root()/'installation.json').write_text(json.dumps(
            {'version':'0.3.3','executable':str(old/'HealthPerfsBar/HealthPerfsBar')}))
        payload=self.root/'payload';(payload/'HealthPerfsBar').mkdir(parents=True)
        name='HealthPerfsBar.exe' if os.name=='nt' else 'HealthPerfsBar'
        (payload/'HealthPerfsBar'/name).write_bytes(b'fake-binary')
        with patch('healthbar.install_engine.validate_host'), patch(
                'healthbar.install_engine.self_test',side_effect=RuntimeError('binary incompatible')):
            with self.assertRaises(RuntimeError):
                install(Settings(),{'os':'ubuntu'},False,lambda *args:None,payload=payload)
        self.assertTrue((old/'keep.txt').is_file())
        self.assertEqual(read_installed_state(install_root())['version'],'0.3.3')

    def test_successful_upgrade_activates_then_removes_old_runtime(self):
        from healthbar import __version__
        root=install_root();old=root/'versions'/'0.3.3';old.mkdir(parents=True)
        (old/'old.bin').write_bytes(b'old')
        root.mkdir(parents=True,exist_ok=True)
        (root/'installation.json').write_text(json.dumps({'version':'0.3.3'}))
        payload=self.root/'payload';(payload/'HealthPerfsBar').mkdir(parents=True)
        name='HealthPerfsBar.exe' if os.name=='nt' else 'HealthPerfsBar'
        (payload/'HealthPerfsBar'/name).write_bytes(b'new')
        def activate_new(executable,*args,**kwargs):
            (root/'installation.json').write_text(json.dumps({'version':__version__,'executable':str(executable)}))
            return {'version':__version__,'executable':str(executable)}
        with patch('healthbar.install_engine.validate_host'), patch(
                'healthbar.install_engine.self_test'),patch(
                'healthbar.install_engine.activate',side_effect=activate_new):
            result=install(Settings(),{'os':'ubuntu'},False,lambda *args:None,payload=payload)
        self.assertEqual(result['version'],__version__)
        self.assertFalse(old.exists())
        self.assertTrue((root/'versions'/__version__/'HealthPerfsBar'/name).is_file())

    def test_invalid_state_forbids_cleanup(self):
        root=install_root();root.mkdir(parents=True)
        (root/'installation.json').write_text('not json')
        with self.assertRaises(ValueError):
            cleanup_obsolete_runtimes(root,'0.3.4')

    def test_release_checks_use_official_manifest_and_monotonic_versions(self):
        release={'tag_name':'v99.0.0','assets':[{'name':'novabar-update-manifest.json',
            'browser_download_url':'https://github.com/florian74410/Health-and-Perfs---Navigation-Controler-Bar/releases/download/v99.0.0/novabar-update-manifest.json'}]}
        manifest={'schema_version':1,'version':'99.0.0','platforms':{'test-platform':{
            'url':'https://github.com/florian74410/Health-and-Perfs---Navigation-Controler-Bar/releases/download/v99.0.0/runtime.zip','sha256':'a'*64}}}
        with patch('healthbar.updates.read_url',side_effect=[json.dumps(release).encode(),json.dumps(manifest).encode()]),patch('healthbar.updates.platform_key',return_value='test-platform'):
            self.assertEqual(check_release()['version'],'99.0.0')
        for url in ('http://github.com/a','https://evil.example/runtime.zip','https://github.com/other/repo/releases/download/x/y'):
            with self.assertRaises(ValueError):asset_url(url)
        self.assertGreater(version('v1.10.0'),version('1.9.9'))

    def test_update_archive_rejects_escape_links_and_duplicate_paths(self):
        archive=self.root/'runtime.zip'
        import stat
        for name in ('../escape','/absolute','C:/drive','a\\b'):
            with zipfile.ZipFile(archive,'w') as z:
                entry=zipfile.ZipInfo('placeholder');entry.filename=name;z.writestr(entry,'bad')
            with self.subTest(name=name), self.assertRaises(ValueError):extract_runtime(archive,self.root/'stage')
        with zipfile.ZipFile(archive,'w') as z:
            item=zipfile.ZipInfo('link');item.external_attr=(stat.S_IFLNK|0o777)<<16;z.writestr(item,'outside')
        with self.assertRaises(ValueError):extract_runtime(archive,self.root/'stage')
        self.assertFalse((self.root/'escape').exists())

    @unittest.skipIf(os.name == 'nt', 'Creating a valid symbolic link may require Windows developer privileges')
    def test_update_preserves_valid_internal_bundle_links(self):
        import stat
        archive=self.root/'bundle.zip'
        with zipfile.ZipFile(archive,'w') as z:
            z.writestr('App/Framework/Versions/A/library','runtime data')
            item=zipfile.ZipInfo('App/Framework/Versions/Current')
            item.create_system=3;item.external_attr=(stat.S_IFLNK|0o777)<<16
            z.writestr(item,'A')
        extract_runtime(archive,self.root/'stage')
        link=self.root/'stage/App/Framework/Versions/Current'
        self.assertTrue(link.is_symlink())
        self.assertEqual((link/'library').read_text(),'runtime data')

    def test_contact_never_sends_without_explicit_confirmation(self):
        with patch('healthbar.contact.smtplib.SMTP') as smtp:
            with self.assertRaises(ValueError):send_feedback(SMTPConfig('','','',''),'Avis','Message')
            smtp.assert_not_called()

    def test_update_bad_hash_keeps_current_install_and_profile_untouched(self):
        import io
        from healthbar.updates import prepare_update
        state=install_root();state.mkdir(parents=True);(state/'installation.json').write_text('{"version":"0.3.0"}')
        response=io.BytesIO(b'not the expected archive')
        with patch('healthbar.updates.urllib.request.urlopen',return_value=response):
            with self.assertRaises(ValueError):prepare_update({'version':'99.0.0','asset':{
                'url':'https://github.com/florian74410/Health-and-Perfs---Navigation-Controler-Bar/releases/download/v99.0.0/runtime.zip',
                'sha256':'a'*64}},lambda *args:None)
        self.assertEqual(json.loads((state/'installation.json').read_text())['version'],'0.3.0')
        self.assertFalse((state/'versions/99.0.0').exists())
