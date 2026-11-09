"""Hourly throttled 1 GiB sequential read/write benchmark on HOME filesystem.

No sudo, no raw disk access, no arbitrary target selection.
First run at app startup if manufacturer data missing, then no more often than hourly.
Write time includes fsync. Cached reads are mitigated via POSIX_FADV_DONTNEED
when supported but cannot be guaranteed to reflect physical disk throughput.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
import shutil
import tempfile
import threading
import time
import fcntl

SIZE = 1024 ** 3
BLOCK = 4 * 1024 ** 2
HOME = Path.home()
RESULT_PATH = HOME / '.config/n3xvs-hud/storage-benchmark.json'
ATTEMPT_PATH = HOME / '.config/n3xvs-hud/storage-benchmark-attempt.json'
LOCK_PATH = HOME / '.config/n3xvs-hud/storage-benchmark.lock'
COOLDOWN_S = 3600

class StorageBenchmark:
    def __init__(self):
        self.lock = threading.RLock()
        self.running = False
        self.error = None
        self.result = None
        self.progress = 'Non testé'
        self.last_attempt_at = 0.0
        self._read_last_attempt()
        self._load()

    def _load(self):
        try:
            d = json.loads(RESULT_PATH.read_text(encoding='utf-8'))
            if isinstance(d, dict) and all(isinstance(d.get(k), (int,float)) for k in ('read_mbs','write_mbs','at')):
                self.result = d
        except (OSError, ValueError, TypeError):
            pass

    def _read_last_attempt(self):
        try:
            data = json.loads(ATTEMPT_PATH.read_text(encoding='utf-8'))
            self.last_attempt_at = float(data.get('at', 0))
        except (OSError, ValueError, TypeError, OverflowError):
            # Upgrade migration: an existing successful benchmark counts as
            # the last attempt so an update does not immediately repeat it.
            self.last_attempt_at = float((self.result or {}).get('at', 0))

    def seconds_remaining(self):
        with self.lock:
            return max(0, int(COOLDOWN_S - (time.time() - self.last_attempt_at) + .999))

    def start(self, automatic=False):
        """Persistent per-user rate limit shared by manual, timer and restarts.

        Locks a dedicated file while recording the attempt timestamp *before*
        starting any IO, so crashes, errors and simultaneous launches cannot
        trigger repeated 1 GiB writes. No test on restart within 60 minutes.
        """
        with self.lock:
            if self.running:
                return False
            LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
            try:
                with open(LOCK_PATH, 'a+b') as lockfile:
                    fcntl.flock(lockfile.fileno(), fcntl.LOCK_EX)
                    try:
                        self._read_last_attempt()
                        now = time.time()
                        if now - self.last_attempt_at < COOLDOWN_S:
                            self.progress = 'Limite : un test maximum par heure'
                            return False
                        # Handle unexpected backward clock changes conservatively.
                        temp = ATTEMPT_PATH.with_suffix('.tmp')
                        temp.write_text(json.dumps({'at': now, 'origin': 'automatic' if automatic else 'manual'})+'\n', encoding='utf-8')
                        os.replace(temp, ATTEMPT_PATH)
                        self.last_attempt_at = now
                        self.running = True
                        self.error = None
                        self.progress = 'Préparation du test 1 Gio…'
                    finally:
                        fcntl.flock(lockfile.fileno(), fcntl.LOCK_UN)
            except OSError as exc:
                self.error = f'Impossible de protéger le test : {exc}'
                return False
        threading.Thread(target=self._work, daemon=True, name='n3xvs-storage-benchmark').start()
        return True

    def _work(self):
        filename = None
        try:
            # The tested target is explicitly HOME, not necessarily the system disk.
            target = HOME
            free = shutil.disk_usage(target).free
            if free < SIZE + 2 * 1024 ** 3:
                raise RuntimeError('Espace libre insuffisant : 3 Gio requis pour tester 1 Gio sans risque de remplissage.')
            fd, filename = tempfile.mkstemp(prefix='.n3xvs-benchmark-', suffix='.bin', dir=str(target))
            payload = os.urandom(BLOCK)
            try:
                with os.fdopen(fd, 'wb', buffering=0) as f:
                    with self.lock: self.progress = 'Écriture de 1 Gio (fsync inclus)…'
                    started = time.monotonic()
                    for i in range(SIZE // BLOCK):
                        f.write(payload)
                    f.flush()
                    os.fsync(f.fileno())
                    write_seconds = max(time.monotonic() - started, 1e-6)
                    # Minimise page-cache effects on next read without privileges.
                    if hasattr(os, 'posix_fadvise') and hasattr(os, 'POSIX_FADV_DONTNEED'):
                        try: os.posix_fadvise(f.fileno(), 0, 0, os.POSIX_FADV_DONTNEED)
                        except OSError: pass
                with self.lock: self.progress = 'Lecture de 1 Gio…'
                with open(filename, 'rb', buffering=0) as f:
                    started = time.monotonic()
                    total = 0
                    while True:
                        buf = f.read(BLOCK)
                        if not buf: break
                        total += len(buf)
                    read_seconds = max(time.monotonic() - started, 1e-6)
                if total != SIZE:
                    raise RuntimeError('Lecture incomplète : mesure rejetée.')
            finally:
                try: os.unlink(filename)
                finally: filename = None
            result = {
                'read_mbs': round(SIZE/read_seconds/1_000_000,1),
                'write_mbs': round(SIZE/write_seconds/1_000_000,1),
                'at': time.time(),
                'bytes': SIZE,
                'mount': str(target),
                'note': 'Benchmark local séquentiel, non constructeur. Lecture potentiellement influencée par le cache Linux.'
            }
            RESULT_PATH.parent.mkdir(parents=True, exist_ok=True)
            temp = RESULT_PATH.with_suffix('.tmp')
            temp.write_text(json.dumps(result, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
            os.replace(temp, RESULT_PATH)
            with self.lock:
                self.result = result
                self.progress = 'Test terminé'
        except Exception as exc:
            with self.lock:
                self.error = str(exc)[:240]
                self.progress = 'Test échoué'
        finally:
            if filename:
                try: os.unlink(filename)
                except OSError: pass
            with self.lock: self.running = False

    def summary(self):
        with self.lock:
            if self.running: return self.progress
            if self.result:
                age = self.seconds_remaining()
                tail = f' · nouveau test dans {age//60 + (1 if age%60 else 0)} min' if age else ' · test autorisé'
                return f"MESURÉ 1 Gio: {self.result['read_mbs']:.0f}↓/{self.result['write_mbs']:.0f}↑ MB/s{tail}"
            return 'TEST 1 Gio DISPONIBLE DANS HOLO SSD'

STORAGE_BENCH = StorageBenchmark()
