import json
import tempfile
import time
import unittest
from pathlib import Path
from threading import Event
from nexus_core.config import normalize, ConfigStore
from nexus_core.engine import NexusEngine
from nexus_core.qt_graphics_cache import GraphicsCache
from nexus_core.holo import HoloController
from nexus_core.benchmarks import StorageBenchmark
from nexus_core.inventory import InventoryCache


class FakeProbes:
    def __init__(self): self.calls=[]
    def cpu_fast(self): self.calls.append('cpu_fast'); return {'hz':1}
    def thermal_fans_ram(self, **kwargs): self.calls.append(('thermal', kwargs)); return kwargs
    def power(self): self.calls.append('power'); return {'watts':None}
    def network_ping(self, *args): self.calls.append('ping'); return {'ping_ms':1}
    def gpu(self): self.calls.append('gpu'); return {'available':False}
    def network_burst(self, **kwargs): self.calls.append('network_sample'); return {'sample_seconds':1}


class CoreTests(unittest.TestCase):
    def test_disabled_plugins_do_not_schedule_probes(self):
        cfg=normalize(None)
        cfg['enabled']={k:False for k in cfg['enabled']}
        engine=NexusEngine(cfg,probes=FakeProbes())
        self.assertEqual({},engine.scheduled_jobs())
        self.assertFalse(engine.request_network_sample())
        self.assertEqual([],engine.tick())
        engine.shutdown()

    def test_fans_ram_cpu_shared_cycle(self):
        cfg=normalize(None)
        cfg['enabled']={k:False for k in cfg['enabled']}
        cfg['enabled']['ram']=True
        cfg['enabled']['fans']=True
        engine=NexusEngine(cfg,probes=FakeProbes())
        self.assertEqual({'thermal_fans_ram':3.0},engine.scheduled_jobs())
        engine.shutdown()

    def test_cpu_independent_fast_cycle(self):
        cfg=normalize(None)
        cfg['enabled']={k:False for k in cfg['enabled']}
        cfg['enabled']['cpu']=True
        engine=NexusEngine(cfg,probes=FakeProbes())
        self.assertEqual({'cpu_fast':1.0,'thermal_fans_ram':3.0},engine.scheduled_jobs())
        engine.shutdown()

    def test_no_automatic_benchmarks(self):
        cfg=normalize({'benchmarks':{'automatic':True}})
        self.assertFalse(cfg['benchmarks']['automatic'])
        engine=NexusEngine(cfg)
        self.assertNotIn('storage_benchmark',engine.scheduled_jobs())
        self.assertNotIn('network_speedtest',engine.scheduled_jobs())
        engine.shutdown()

    def test_three_layer_graphics_cache(self):
        cache=GraphicsCache(); counter=[]
        def render(): counter.append(1);return object()
        self.assertIs(cache.chassis(('blue',1280,100),render),cache.chassis(('blue',1280,100),render))
        self.assertEqual(1,len(counter))
        cache.instruments('cpu','45%',render)
        cache.instruments('cpu','45%',render)
        cache.instruments('cpu','46%',render)
        self.assertEqual(3,len(counter))
        cache.clear()
        self.assertEqual(0,cache.stats()['chassis_entries'])

    def test_single_lazy_holo(self):
        counts=[]
        class View:
            def close(self): counts.append('close')
        registry=HoloController()
        registry.register('cpu',lambda data:(counts.append('cpu') or View()))
        registry.register('ram',lambda data:(counts.append('ram') or View()))
        self.assertEqual([],counts)
        registry.open('cpu',{})
        registry.open('ram',{})
        self.assertEqual(['cpu','close','ram'],counts)
        registry.open('ram',{})
        self.assertEqual(['cpu','close','ram','close'],counts)

    def test_config_is_isolated(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'preview.json'; store=ConfigStore(p)
            cfg=store.load();cfg['enabled']['power']=False
            store.save(cfg)
            self.assertFalse(store.load()['enabled']['power'])
            self.assertFalse(store.load()['benchmarks']['automatic'])

    def test_inventory_cached_same_boot(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'hardware.json'; cache=InventoryCache(p)
            data=cache.get();self.assertEqual(data,cache.get())
            self.assertIsNone(data['memory_sticks'])

    def test_benchmark_small_file_and_progress(self):
        with tempfile.TemporaryDirectory() as td:
            events=[]
            b=StorageBenchmark(events.append,directory=td)
            # small file works, but disk space guard requires >= 2 GiB free
            self.assertTrue(b.start(256*1024))
            b._thread.join(5)
            self.assertFalse(b.running)
            if events[-1]['state']=='success':
                self.assertEqual(100,events[-1]['percent'])
                self.assertTrue(any(e['state']=='writing' for e in events))
                self.assertTrue(any(e['state']=='reading' for e in events))
            else:
                self.assertEqual('error',events[-1]['state'])
            self.assertFalse(list(Path(td).glob('.nexus-ssd-test-*')))

if __name__=='__main__': unittest.main()
