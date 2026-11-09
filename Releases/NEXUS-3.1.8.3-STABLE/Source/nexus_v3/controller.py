"""Central state controller. No Qt or system side effects: UI receives notifications.

One owner for TopBar, BottomBar, Holo and data availability. No duplicated
open/close timers in individual plugins.
"""
from __future__ import annotations
from collections import defaultdict
from dataclasses import dataclass
from time import monotonic

PLUGINS = ('cpu','gpu','ram','storage','fans','network','power')

@dataclass(frozen=True)
class Snapshot:
    top: str
    bottom: str
    holo: str | None
    closing: bool
    revision: int

class ThemeController:
    def __init__(self, config):
        self.config = config
        self.top = 'expanded'
        self.bottom = 'visible'
        self.holo = None
        self.closing = False
        self.revision = 0
        self.data = {}
        self.data_times = {}
        self.errors = {}
        self._subscribers = defaultdict(list)
        self.last_interaction = monotonic()

    def subscribe(self, event, callback):
        self._subscribers[event].append(callback)

    def _emit(self, event, payload):
        for subscriber in tuple(self._subscribers[event]):
            subscriber(payload)

    def _change(self):
        self.revision += 1
        self._emit('state', self.snapshot())

    def snapshot(self):
        return Snapshot(self.top,self.bottom,self.holo,self.closing,self.revision)

    def interact(self):
        self.last_interaction = monotonic()

    def set_top(self, expanded):
        if self.closing:return False
        target = 'expanded' if expanded else 'retracted'
        if self.top == target:return False
        self.top = target
        self.interact()
        self._change()
        return True

    def set_bottom(self, show):
        if self.closing:return False
        target = 'visible' if show else 'hidden'
        if self.bottom == target:return False
        self.bottom = target
        self._change()
        return True

    def open_holo(self, plugin):
        if self.closing or plugin not in PLUGINS or not self.config['enabled'].get(plugin,False):
            return False
        self.holo = None if self.holo == plugin else plugin
        self.interact()
        self._change()
        return True

    def close_holo(self):
        if self.holo is not None:
            self.holo = None
            self._change()

    def reconfigure(self, cfg):
        self.config = cfg
        if self.holo and not cfg['enabled'].get(self.holo,False):self.holo = None
        self._change()

    def ingest(self, event):
        name = event.get('name')
        if not name:return
        if event.get('type') == 'measurement':
            self.data[name] = event.get('data') or {}
            self.data_times[name] = event.get('timestamp',monotonic())
            self.errors.pop(name,None)
            self._emit('data',name)
        elif event.get('type') == 'error':
            self.errors[name] = event.get('error','Erreur de collecte')
            self._emit('data',name)

    def stop(self):
        self.closing = True
        self.holo = None
        self._change()
