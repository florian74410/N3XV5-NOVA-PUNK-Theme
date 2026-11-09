"""Narrow OS backends: report the effective boost state, never emulate hardware."""
import os
import sys
from pathlib import Path

class UnsupportedBackend:
    def read(self):
        raise OSError("Contrôle Turbo indisponible sur ce système : aucun backend matériel pris en charge. Aucun changement effectué.")
    def write(self, enabled):
        self.read()

class LinuxBoostBackend:
    """Use the kernel boost switch, with Intel's inverted no_turbo semantics.

    Rights must be granted by the administrator outside NovaBar. We never invoke
    sudo, weaken sysfs permissions, or write any frequency/voltage parameters.
    """
    def __init__(self, root=Path('/sys/devices/system/cpu')):
        root=Path(root)
        self.path=next((p for p in (root/'intel_pstate/no_turbo', root/'cpufreq/boost') if p.is_file()), None)
        self.inverted=self.path is not None and self.path.name=='no_turbo'

    def read(self):
        if self.path is None:raise OSError("Le noyau n’expose aucun contrôle Turbo (intel_pstate/no_turbo ou cpufreq/boost).")
        value=self.path.read_text().strip()
        if value not in ('0','1'):raise OSError("État Turbo du noyau non reconnu.")
        return (value=='0') if self.inverted else (value=='1')

    def write(self, enabled):
        if type(enabled) is not bool:raise ValueError('Expected a boolean boost request')
        if self.read()==enabled:return enabled
        if not os.access(self.path,os.W_OK):
            raise PermissionError("Contrôle Turbo en lecture seule. Un administrateur doit autoriser l’écriture du commutateur sysfs ; NovaBar reste sans privilèges.")
        self.path.write_text(('0' if enabled else '1') if self.inverted else ('1' if enabled else '0'))
        actual=self.read()
        if actual!=enabled:raise OSError("Le noyau n’a pas appliqué la demande Turbo.")
        return actual

def system_backend():
    return LinuxBoostBackend() if sys.platform.startswith('linux') else UnsupportedBackend()
