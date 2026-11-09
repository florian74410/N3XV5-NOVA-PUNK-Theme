"""Verified native-package downloader; the offline installer remains available.

Only official, version-matched release assets may be downloaded and executed.
Native installation runs as the user, with the OS authorization dialog for DEB.
"""
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from .updates import API, asset_url, read_url, version, platform_key

MAX_PACKAGE=300*1024*1024

def package_candidates(manifest, key, preferred=None):
    if manifest.get('schema_version')!=1:raise ValueError('Manifeste bootstrap non pris en charge')
    version(manifest.get('version'))
    formats=('.deb','.run') if key.startswith('linux-') else ('.exe',) if key.startswith('windows-') else ('.dmg',)
    if preferred in formats:formats=(preferred,)+tuple(x for x in formats if x!=preferred)
    assets=manifest.get('packages',{}).get(key,[])
    for suffix in formats:
        for asset in assets:
            if asset.get('format')!=suffix:continue
            url=asset_url(asset.get('url',''))
            name=asset.get('name','')
            if not re.fullmatch(r'[A-Za-z0-9_.-]+',name) or not name.endswith(suffix) or not url.endswith('/'+name):
                raise ValueError('Nom de paquet invalide')
            if not re.fullmatch(r'[a-f0-9]{64}',asset.get('sha256','')):raise ValueError('Empreinte manquante')
            return asset
    raise ValueError('Aucun paquet natif publié pour cette architecture. Aucun téléchargement de substitution.')

def latest_package(preferred=None):
    release=json.loads(read_url(API))
    if release.get('draft') or release.get('prerelease'):raise ValueError('Release stable indisponible')
    tag=release.get('tag_name','');version(tag)
    descriptor=next((a for a in release.get('assets',[]) if a.get('name')=='novabar-bootstrap-manifest.json'),None)
    if descriptor is None:raise ValueError('Aucune release downloader publiée. Utilisez un installateur hors ligne existant.')
    url=asset_url(descriptor['browser_download_url'])
    if '/releases/download/'+tag+'/' not in url:raise ValueError('Release incohérente')
    manifest=json.loads(read_url(url))
    if version(manifest.get('version'))!=version(tag):raise ValueError('Version du manifeste incohérente')
    if platform.machine().lower() not in ('x86_64','amd64','arm64','aarch64'):raise ValueError('Architecture non prise en charge')
    asset=package_candidates(manifest,platform_key(),preferred)
    if '/releases/download/'+tag+'/' not in asset['url']:raise ValueError('Paquet hors de la release sélectionnée')
    return asset

def download(asset, directory, notify=lambda message:None):
    import urllib.request
    path=Path(directory)/asset['name']
    digest=hashlib.sha256();size=0
    try:
        with urllib.request.urlopen(asset_url(asset['url']),timeout=30) as response, path.open('wb') as output:
            while True:
                chunk=response.read(1024*1024)
                if not chunk:break
                size+=len(chunk)
                if size>MAX_PACKAGE:raise ValueError('Paquet trop volumineux')
                output.write(chunk);digest.update(chunk)
                notify(f'Téléchargement : {size//1024//1024} Mo')
        if digest.hexdigest()!=asset['sha256']:raise ValueError('SHA-256 incorrect : installation refusée')
        return path
    except Exception:
        path.unlink(missing_ok=True)
        raise

def install_package(path, settings=None):
    path=Path(path).resolve()
    if path.suffix=='.deb' and sys.platform.startswith('linux'):
        apt=shutil.which('apt-get')
        if not apt:raise OSError('apt-get absent. Choisissez le format .run.')
        command=[apt,'install','-y',str(path)]
        if os.geteuid()!=0:
            pkexec=shutil.which('pkexec')
            if not pkexec:raise OSError('Autorisation système indisponible (pkexec absent). Utilisez votre gestionnaire de paquets.')
            command=[pkexec]+command
    elif path.suffix=='.run' and sys.platform.startswith('linux'):
        command=['sh',str(path)]
    elif path.suffix=='.exe' and sys.platform=='win32':
        # The offline wizard must finish before initial preferences are committed.
        command=[str(path),'/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART']
    elif path.suffix=='.dmg' and sys.platform=='darwin':
        raise OSError('macOS : ouvrez le DMG hors ligne. Installation automatique non disponible pour ce format.')
    else:raise ValueError('Paquet incompatible avec cette plateforme')
    from .system_env import native_env
    env=native_env()
    env['NOVABAR_BOOTSTRAP']='1'
    if settings is not None:
        from dataclasses import asdict
        env['NOVABAR_BOOTSTRAP_SETTINGS']=json.dumps(asdict(settings))
    result=subprocess.run(command,check=False,env=env)
    if result.returncode:raise OSError(f'Installation interrompue ou refusée (code {result.returncode}).')


def main():
    """Small downloader UI with native-package selection and initial preferences."""
    self_test="--self-test" in sys.argv
    if self_test:os.environ.setdefault("QT_QPA_PLATFORM","offscreen")
    from dataclasses import replace
    from PySide6.QtCore import QThread, Signal
    from PySide6.QtWidgets import (QApplication,QDialog,QVBoxLayout,QFormLayout,QLabel,QComboBox,QSpinBox,QCheckBox,QPushButton)
    from PySide6.QtGui import QDesktopServices
    from PySide6.QtCore import QUrl
    from .config import Settings
    from .branding import BrandHeader
    from .dialogs import STYLE
    from .ui_kit import THEMES,stylesheet,set_theme
    from .help_links import DOC_LINKS

    class Worker(QThread):
        progress=Signal(str);finished_install=Signal(bool,str)
        def __init__(self,settings,preferred):
            super().__init__();self.settings=settings;self.preferred=preferred
        def run(self):
            try:
                self.progress.emit('Recherche de la dernière release stable…')
                asset=latest_package(self.preferred)
                with tempfile.TemporaryDirectory(prefix='novabar-download-') as directory:
                    # apt's sandbox user must be able to read the downloaded DEB.
                    if os.name!='nt':Path(directory).chmod(0o755)
                    path=download(asset,directory,self.progress.emit)
                    self.progress.emit('SHA-256 vérifié · installation native…')
                    install_package(path,self.settings)
                self.settings.save()
                self.finished_install.emit(True,'Installation terminée. Préférences enregistrées. Vous pouvez ouvrir NovaBar.')
            except Exception as error:self.finished_install.emit(False,str(error))

    class Downloader(QDialog):
        def __init__(self):
            super().__init__();self.settings=Settings.load();set_theme(self.settings.theme)
            self.setWindowTitle('NovaBar · Downloader');self.resize(640,650);self.setStyleSheet(stylesheet(STYLE))
            box=QVBoxLayout(self);self.header=BrandHeader();box.addWidget(self.header)
            form=QFormLayout();box.addLayout(form)
            self.format=QComboBox()
            self.format.addItems(['.deb','.run'] if sys.platform.startswith('linux') else ['.exe'] if sys.platform=='win32' else ['.dmg'])
            if sys.platform.startswith('linux') and not shutil.which('dpkg'):self.format.setCurrentText('.run')
            form.addRow('Format',self.format)
            self.theme=QComboBox()
            for key,label in THEMES.items():self.theme.addItem(label,key)
            self.theme.setCurrentIndex(max(0,self.theme.findData(self.settings.theme)));form.addRow('Thème',self.theme)
            self.thickness=QSpinBox();self.thickness.setRange(50,150);self.thickness.setValue(self.settings.thickness);form.addRow('Épaisseur (px)',self.thickness)
            self.position=QComboBox();self.position.addItems(['top','bottom','left','right']);self.position.setCurrentText(self.settings.position);form.addRow('Position',self.position)
            self.retract=QComboBox()
            for label,key in [('Always visible','always'),('Auto retract','auto'),('Manual retract only','manual')]:self.retract.addItem(label,key)
            self.retract.setCurrentIndex(max(0,self.retract.findData(self.settings.retract_mode or ('auto' if self.settings.auto_hide else 'manual'))));form.addRow('Rétractation',self.retract)
            self.top=QCheckBox('Always-on-top');self.top.setChecked(self.settings.always_on_top);form.addRow(self.top)
            self.holo=QCheckBox('Autoriser les panneaux Holo des plugins activés');self.holo.setChecked(self.settings.holo_enabled);form.addRow(self.holo)
            for label,url in list(DOC_LINKS.items())[:2]:
                button=QPushButton(label);button.clicked.connect(lambda checked=False,url=url:QDesktopServices.openUrl(QUrl(url)));box.addWidget(button)
            self.status=QLabel('Télécharge un paquet officiel et vérifie son empreinte avant installation.');self.status.setWordWrap(True);box.addWidget(self.status)
            self.start=QPushButton('TÉLÉCHARGER ET INSTALLER');self.start.clicked.connect(self.begin);box.addWidget(self.start)
            self.worker=None
            if sys.platform=="darwin":
                self.start.setEnabled(False)
                self.status.setText("macOS : utilisez le DMG hors ligne du dépôt. Le downloader automatique cible Linux et Windows.")
        def begin(self):
            settings=replace(self.settings,theme=self.theme.currentData(),thickness=self.thickness.value(),position=self.position.currentText(),retract_mode=self.retract.currentData(),auto_hide=self.retract.currentData()=='auto',always_on_top=self.top.isChecked(),holo_enabled=self.holo.isChecked(),configured=True).validate()
            self.start.setEnabled(False)
            self.worker=Worker(settings,self.format.currentText());self.worker.progress.connect(self.status.setText)
            self.worker.finished_install.connect(self.done_install);self.worker.start()
        def done_install(self,success,message):
            self.status.setText(message);self.start.setEnabled(True)
        def closeEvent(self,event):
            if self.worker and self.worker.isRunning():
                self.status.setText('Installation en cours : attendez sa fin avant de fermer.');event.ignore()
            else:super().closeEvent(event)
    app=QApplication.instance() or QApplication(sys.argv[:1]);dialog=Downloader()
    if self_test:
        dialog.show();app.processEvents()
        valid=not dialog.grab().isNull()
        dialog.close();return 0 if valid else 2
    dialog.exec();return 0
