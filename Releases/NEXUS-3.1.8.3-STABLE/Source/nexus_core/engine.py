"""Coordinated periodic scheduler. Qt painting is never invoked from workers.

The host GUI drains queue events on its own thread. No disabled-plugin probe runs.
"""
from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor
from queue import Queue
from threading import Event, Lock, Thread
from time import monotonic, sleep
from . import collectors


class NexusEngine:
    def __init__(self, config, *, clock=monotonic, probes=None):
        self.cfg = config
        self.clock = clock
        self.probes = probes or collectors
        self.events = Queue(maxsize=256)
        self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix='nexus-probe')
        self._stop = Event()
        self._thread = None
        self._lock = Lock()
        self._due = {}
        self._busy = set()
        self._last = {}
        self._diagnostics = {}
        self._network_link_signature = None
        self._layout()

    def _layout(self):
        enabled = self.cfg['enabled']; periods = self.cfg['periods']
        jobs = {}
        if enabled['cpu']:
            jobs['cpu_fast'] = periods['cpu_fast']
        # CPU temperatures run at the FANS cadence. RAM shares that cadence.
        if any(enabled[k] for k in ('cpu','ram','fans')):
            jobs['thermal_fans_ram'] = periods['thermal_fans_ram']
        if enabled['power']: jobs['power'] = periods['power']
        if enabled['network']: jobs['network_ping'] = periods['network_ping']
        if enabled['gpu']: jobs['gpu'] = periods['gpu']
        # No periodic jobs for STORAGE: capacity/inventory is startup-only;
        # neither disk benchmark nor bandwidth tests are scheduled.
        with self._lock:
            old = self._due
            self._due = {name:old.get(name,self.clock()) for name in jobs}
            self._periods = jobs

    def reconfigure(self, config):
        self.cfg = config
        self._layout()

    def scheduled_jobs(self):
        with self._lock: return dict(self._periods)

    def tick(self):
        now = self.clock()
        with self._lock:
            ready = []
            for name, interval in self._periods.items():
                if name not in self._busy and now >= self._due[name]:
                    self._busy.add(name)
                    self._due[name] = now + interval
                    ready.append(name)
        for name in ready:
            self._executor.submit(self._run, name)
        return ready

    def _run(self, name):
        started = self.clock()
        try:
            en = self.cfg['enabled']
            if name == 'cpu_fast': result = self.probes.cpu_fast()
            elif name == 'thermal_fans_ram':
                result = self.probes.thermal_fans_ram(cpu=en['cpu'],ram=en['ram'],fans=en['fans'])
            elif name == 'power': result = self.probes.power()
            elif name == 'network_ping':
                n = self.cfg['network']
                result = self.probes.network_ping(n['ping_host'], n['ping_timeout'])
            elif name == 'gpu': result = self.probes.gpu()
            else: return
            if name == 'network_ping':
                # Detect a link transition using the existing ping cadence.
                # Do not confuse ICMP failure with physical link-down.
                links = result.get('links') or {}
                signature = tuple(sorted(n for n, up in links.items() if up))
                old = self._network_link_signature
                self._network_link_signature = signature
                if old is not None and not old and signature:
                    self.request_network_sample()
            self._diagnostics[name] = {'last_duration_ms': round((self.clock()-started)*1000,2),
                                       'last_updated': self.clock(),
                                       'runs': self._diagnostics.get(name,{}).get('runs',0)+1}
            self._last[name] = {'timestamp': self.clock(), 'data': result}
            self.events.put_nowait({'type':'measurement','name':name,**self._last[name]})
        except Exception as exc:
            try: self.events.put_nowait({'type':'error','name':name,'error':str(exc)[:200]})
            except Exception: pass
        finally:
            with self._lock: self._busy.discard(name)

    def diagnostics(self):
        with self._lock:
            pending = sorted(self._busy)
            periods = dict(self._periods)
        return {'jobs':periods,'busy':pending,
                'measurements':dict(self._diagnostics),
                'queue_depth':self.events.qsize()}

    def request_network_sample(self):
        if not self.cfg['enabled']['network']: return False
        with self._lock:
            if 'network_sample' in self._busy: return False
            self._busy.add('network_sample')
        def worker():
            try:
                result = self.probes.network_burst(duration=1.0)
                self.events.put_nowait({'type':'measurement','name':'network_sample',
                                        'timestamp':self.clock(),'data':result})
            except Exception as exc:
                self.events.put_nowait({'type':'error','name':'network_sample','error':str(exc)[:200]})
            finally:
                with self._lock: self._busy.discard('network_sample')
        self._executor.submit(worker)
        return True

    def notify_network_reconnected(self):
        # Caller must compare link-state transitions; no polling bandwidth in idle.
        return self.request_network_sample()

    def start(self):
        if self._thread and self._thread.is_alive(): return
        self._stop.clear()
        def loop():
            # One immediate sample at theme startup, only if NET is enabled.
            if self.cfg['enabled']['network']: self.request_network_sample()
            while not self._stop.wait(0.1): self.tick()
        self._thread = Thread(target=loop, name='nexus-scheduler',daemon=True)
        self._thread.start()

    def shutdown(self):
        self._stop.set()
        if self._thread: self._thread.join(timeout=3)
        self._executor.shutdown(wait=False, cancel_futures=True)
