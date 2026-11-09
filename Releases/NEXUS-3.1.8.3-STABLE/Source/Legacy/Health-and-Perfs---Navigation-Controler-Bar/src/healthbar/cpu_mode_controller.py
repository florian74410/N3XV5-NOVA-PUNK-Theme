"""CPU mode policy independent of Qt; hardware requests are verified by the backend."""
import math
import threading
from .cpu_backends import system_backend

class CpuModeController:
    MODES={'off':'Turbo Off','on':'Turbo On','auto':'Auto (85°C)'}
    def __init__(self, backend=None, threshold=85, hysteresis=5):
        if not 50 <= threshold <= 100 or not 1 <= hysteresis <= 15:raise ValueError('Invalid thermal policy')
        self.backend=backend or system_backend()
        self.threshold=threshold;self.hysteresis=hysteresis
        self.mode=None  # Launching the HUD never changes the existing CPU policy.
        self._lock=threading.Lock()
        self.status='CPU Mode : état en attente'

    def select(self, mode):
        if mode not in self.MODES:raise ValueError('Unknown CPU mode')
        with self._lock:self.mode=mode

    def sample(self, temperature):
        """Called on the telemetry worker, never blocks the Qt thread.

        Missing/invalid temperature in Auto requests boost OFF and reports the
        missing sensor. CPU firmware thermal protection remains authoritative.
        """
        with self._lock:
            try:
                actual=self.backend.read()
                desired=actual
                missing=not isinstance(temperature,(int,float)) or isinstance(temperature,bool) or not math.isfinite(temperature) or not -20 <= temperature <= 150
                if self.mode=='on':desired=True
                elif self.mode=='off':desired=False
                elif self.mode=='auto':
                    if missing or temperature>=self.threshold:desired=False
                    elif temperature<=self.threshold-self.hysteresis:desired=True
                if desired!=actual:actual=self.backend.write(desired)
                self.status=('Auto : température indisponible, Turbo Off' if self.mode=='auto' and missing else
                    (self.MODES.get(self.mode,'État système')+' · '+('Turbo On' if actual else 'Turbo Off')))
                return {'mode':self.mode,'enabled':actual,'error':None,'message':self.status}
            except (OSError,ValueError) as error:
                self.status=str(error)
                return {'mode':self.mode,'enabled':None,'error':str(error),'message':str(error)}
