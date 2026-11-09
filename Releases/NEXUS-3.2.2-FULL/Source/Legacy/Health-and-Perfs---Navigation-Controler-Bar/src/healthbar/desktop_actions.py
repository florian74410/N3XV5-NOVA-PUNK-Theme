"""Native freedesktop launcher actions. No shell and no system-file writes.

Renaming creates an XDG user-level override. Uninstallation requires explicit
confirmation and host polkit authorisation for an unambiguous APT owner.
"""
import configparser
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from PySide6.QtWidgets import QMessageBox,QInputDialog
from PySide6.QtCore import QThread,Signal
from .system_env import native_env

_ACTIVE_UNINSTALLS=set()
_PACKAGE=re.compile(r"^[a-z0-9][a-z0-9+.-]{0,99}(?::[a-z0-9]+)?$")


def rename_launcher(path,parent=None):
    """Retitle only user's shortcut; never mutate root-owned /usr/share."""
    src=Path(path)
    if not src.is_file() or src.suffix.lower()!=".desktop":
        return None
    name,ok=QInputDialog.getText(parent,"NEXUS / Renommer","Nouveau nom de l'application :")
    if not ok:
        return None
    name=name.strip()
    if not (1<=len(name)<=80) or any(ord(c)<32 for c in name):
        QMessageBox.warning(parent,"NEXUS","Nom invalide (80 caractères maximum).")
        return None
    cfg=configparser.ConfigParser(interpolation=None,strict=False)
    cfg.optionxform=str  # Freedesktop keys, e.g. Exec, are case sensitive.
    try:
        cfg.read(src,encoding="utf-8")
        if cfg["Desktop Entry"].get("Type")!="Application":
            raise ValueError("Ce fichier n'est pas un lanceur d'application")
        cfg["Desktop Entry"]["Name"]=name
        cfg["Desktop Entry"]["Name[fr]"]=name
        dest=Path(os.environ.get("XDG_DATA_HOME",str(Path.home()/".local/share")))/"applications"/src.name
        dest.parent.mkdir(parents=True,exist_ok=True)
        fd,tmp=tempfile.mkstemp(dir=dest.parent,prefix=".novabar-rename-",suffix=".desktop")
        try:
            with os.fdopen(fd,"w",encoding="utf-8") as stream:
                cfg.write(stream,space_around_delimiters=False)
                stream.flush()
                os.fsync(stream.fileno())
            os.chmod(tmp,0o644)
            os.replace(tmp,dest)
        finally:
            if os.path.exists(tmp):os.unlink(tmp)
        return str(dest)
    except (OSError,ValueError,KeyError,configparser.Error) as exc:
        QMessageBox.warning(parent,"NEXUS","Renommage impossible : "+str(exc))
        return None


def apt_owner(launcher):
    """Return an APT package only if dpkg owns exactly one launcher."""
    if not shutil.which("dpkg-query"):
        return None
    path=Path(launcher)
    if not path.is_file() or not str(path).startswith("/usr/share/"):
        return None
    try:
        result=subprocess.run(["dpkg-query","-S",str(path)],
                              capture_output=True,text=True,timeout=3,env=native_env())
        if result.returncode:
            return None
        packages=set()
        for line in result.stdout.splitlines():
            header,sep,_=line.partition(": ")
            if sep:
                for candidate in header.split(","):
                    package=candidate.strip()
                    if _PACKAGE.fullmatch(package):
                        packages.add(package)
        return next(iter(packages)) if len(packages)==1 else None
    except (OSError,subprocess.TimeoutExpired):
        return None


class _RemovePackageWorker(QThread):
    completed=Signal(bool,str)
    def __init__(self,package):
        super().__init__()
        self.package=package
    def run(self):
        try:
            result=subprocess.run(["pkexec","/usr/bin/apt-get","remove","-y","--",self.package],
                                  stdin=subprocess.DEVNULL,capture_output=True,text=True,
                                  timeout=360,env=native_env())
            message=(result.stderr or result.stdout).strip()[-1300:]
            self.completed.emit(result.returncode==0,message or
                                ("Suppression APT terminée" if result.returncode==0 else "APT a refusé"))
        except (OSError,subprocess.TimeoutExpired) as exc:
            self.completed.emit(False,str(exc))


def request_uninstall(launcher,parent=None):
    """The user selects the exact package, then authenticates with polkit."""
    package=apt_owner(launcher)
    if package is None:
        QMessageBox.information(parent,"NEXUS / Désinstallation",
            "Aucun paquet APT unique n'a été trouvé pour ce lanceur. "
            "Utilise le Gestionnaire de logiciels Mint pour Flatpak ou une installation manuelle.")
        if shutil.which("mintinstall"):
            subprocess.Popen(["mintinstall"],env=native_env(),
                             stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        return
    if not shutil.which("pkexec"):
        QMessageBox.warning(parent,"NEXUS","Polkit (pkexec) est nécessaire.")
        return
    answer=QMessageBox.question(parent,"Désinstaller l'application",
          "Désinstaller le paquet APT « "+package+" » ?\n"
          "APT peut également retirer des composants qui en dépendent. "
          "Une autorisation administrateur sera demandée.",
          QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,
          QMessageBox.StandardButton.No)
    if answer!=QMessageBox.StandardButton.Yes:
        return
    worker=_RemovePackageWorker(package)
    _ACTIVE_UNINSTALLS.add(worker)
    def finished(ok,message):
        QMessageBox.information(None,"NEXUS · APT" if ok else "NEXUS · Échec APT",
                                ("Désinstallation confirmée.\n" if ok else "Échec / refus.\n")+message)
    worker.completed.connect(finished)
    worker.finished.connect(lambda w=worker:(_ACTIVE_UNINSTALLS.discard(w),w.deleteLater()))
    worker.start()
