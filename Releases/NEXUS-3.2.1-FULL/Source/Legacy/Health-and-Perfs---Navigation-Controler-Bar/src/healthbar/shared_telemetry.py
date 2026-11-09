"""Single read-only telemetry service for HUD/Holo and module subscribers.

Uses the existing psutil-powered Telemetry collector. Unsupported GPU/power
fields continue to use the existing dedicated adapters, without new APIs.
"""
from __future__ import annotations
import threading
import time
from .telemetry import Telemetry
from .module_preferences import load, FIELDS

class SharedTelemetry:
    def __init__(self, sampler=None, clock=None):
        self.sampler = sampler or Telemetry()
        self.clock = clock or time.monotonic
        self.lock = threading.RLock()
        self.last_at = 0.0
        self.snapshot = None
        self.prefs = load()
        self._apply_intervals()

    def _apply_intervals(self):
        if hasattr(self.sampler, 'module_intervals'):
            self.sampler.module_intervals.update({key: self.prefs[key]['refresh_seconds']
                for key in ('gpu', 'fans', 'power')})

    def reload_preferences(self):
        with self.lock:
            self.prefs = load()
            self._apply_intervals()

    def interval(self):
        # The highest-frequency enabled subscriber determines sample rate.
        return min(value["refresh_seconds"] for value in self.prefs.values())

    def sample(self, force=False):
        with self.lock:
            now = self.clock()
            if not force and self.snapshot is not None and now-self.last_at < self.interval():
                return self.snapshot.copy()
            # Existing Telemetry covers all modules in one sampling pass.
            fresh = self.sampler.sample()
            self.snapshot = fresh
            self.last_at = self.clock()
            return fresh.copy()

    def module_data(self, name):
        if name not in FIELDS:
            raise KeyError(name)
        with self.lock:
            if self.snapshot is None:
                return None
            return {key:self.snapshot.get(key) for key in self.prefs[name]["details"]}
