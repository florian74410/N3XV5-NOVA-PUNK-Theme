"""Explicit-only cancellable SSD benchmark with progress events.
No automatic timers. Cache effects and filesystem location are disclosed.
"""
from __future__ import annotations
import os
import shutil
import tempfile
import time
from pathlib import Path
from threading import Event, Lock, Thread

CHUNK_BYTES = 4 * 1024 * 1024


class BenchmarkCancelled(Exception): pass


class StorageBenchmark:
    def __init__(self, on_event=None, *, directory=None):
        self.on_event = on_event or (lambda *_: None)
        self.directory = Path(directory or Path.home())
        self._cancel = Event()
        self._lock = Lock()
        self._running = False
        self._thread = None

    @property
    def running(self):
        with self._lock: return self._running

    def start(self, size_bytes=1024**3):
        if size_bytes <= 0: raise ValueError('Benchmark size must be positive')
        with self._lock:
            if self._running: return False
            self._running = True
        self._cancel.clear()
        self._thread = Thread(target=self._work, args=(size_bytes,),daemon=True,name='nexus-ssd-bench')
        self._thread.start()
        return True

    def stop(self):
        # Stop means cancellation; never treat a partial benchmark as a valid measurement.
        self._cancel.set()

    def _emit(self, state, **kwargs): self.on_event({'state':state, **kwargs})

    def _work(self, size_bytes):
        path = None
        try:
            free = shutil.disk_usage(self.directory).free
            if free < size_bytes + 2 * 1024**3: raise OSError('Pas assez d’espace libre pour tester sans risque')
            with tempfile.NamedTemporaryFile(prefix='.nexus-ssd-test-',dir=self.directory,delete=False) as file:
                path = Path(file.name)
                chunk = b'\xA5' * CHUNK_BYTES
                written = 0; start = time.monotonic()
                while written < size_bytes:
                    if self._cancel.is_set(): raise BenchmarkCancelled()
                    count = min(CHUNK_BYTES, size_bytes-written)
                    file.write(chunk[:count]); written += count
                    self._emit('writing',percent=round(written/size_bytes*50,1))
                file.flush(); os.fsync(file.fileno())
            write_time = max(.00001,time.monotonic()-start)
            read = 0; start = time.monotonic()
            with path.open('rb', buffering=0) as file:
                while read < size_bytes:
                    if self._cancel.is_set(): raise BenchmarkCancelled()
                    payload = file.read(min(CHUNK_BYTES,size_bytes-read))
                    if not payload: raise OSError('Lecture incomplète')
                    read += len(payload)
                    self._emit('reading',percent=round(50+read/size_bytes*50,1))
            read_time = max(.00001,time.monotonic()-start)
            self._emit('success',percent=100.0,write_MBps=round(size_bytes/write_time/1e6,1),
                       read_MBps=round(size_bytes/read_time/1e6,1),
                       note='Lecture pouvant bénéficier du cache Linux; valeurs locales non constructeur')
        except BenchmarkCancelled:
            self._emit('cancelled',percent=0.0)
        except Exception as exc:
            self._emit('error',error=str(exc)[:200])
        finally:
            if path is not None:
                try:path.unlink(missing_ok=True)
                except OSError:pass
            with self._lock:self._running=False
