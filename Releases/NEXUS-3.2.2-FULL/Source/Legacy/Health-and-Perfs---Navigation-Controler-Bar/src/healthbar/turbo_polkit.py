"""User-session polkit controller for NovaBar's fixed, root-owned CPU helper."""
import os
import shutil
import subprocess
import sys
from PySide6.QtCore import QThread, Signal
from .system_env import native_env

# Worker lifetime is independent from the HUD window, including during quit.
_workers=set()
HELPER="/usr/libexec/novabar-turbo-helper"


class TurboAuthWorker(QThread):
    completed=Signal(bool,str)
    def __init__(self,enabled):
        super().__init__()
        self.enabled=bool(enabled)

    def run(self):
        if not sys.platform.startswith("linux"):
            self.completed.emit(False,"Mode Turbo administrateur disponible uniquement sous Linux")
            return
        if not shutil.which("pkexec"):
            self.completed.emit(False,"pkexec est absent : installer le composant Polkit du système")
            return
        if not os.path.isfile(HELPER):
            self.completed.emit(False,"Assistant Turbo manquant : réinstaller le paquet NovaBar .deb")
            return
        try:
            proc=subprocess.run(["pkexec",HELPER,"on" if self.enabled else "off"],
                               text=True,stdin=subprocess.DEVNULL,
                               stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                               timeout=120,check=False,env=native_env())
            if proc.returncode:
                self.completed.emit(False,proc.stderr.strip() or
                                    "Autorisation refusée ou Turbo indisponible")
                return
            from .cpu_backends import system_backend
            actual=system_backend().read()
            if actual != self.enabled:
                self.completed.emit(False,"Le noyau n'a pas confirmé le changement Turbo")
                return
            self.completed.emit(True,"TURBO ON" if actual else "NORMAL MODE")
        except (OSError,ValueError,subprocess.TimeoutExpired) as exc:
            self.completed.emit(False,str(exc))


def request_turbo(enabled,callback):
    worker=TurboAuthWorker(enabled)
    _workers.add(worker)
    worker.completed.connect(callback)
    def release():
        _workers.discard(worker)
        worker.deleteLater()
    worker.finished.connect(release)
    worker.start()
    return worker
