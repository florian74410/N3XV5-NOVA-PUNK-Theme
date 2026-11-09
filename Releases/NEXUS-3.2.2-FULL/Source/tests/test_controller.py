import unittest
from nexus_core.config import normalize
from nexus_v3.controller import ThemeController

class ControllerTests(unittest.TestCase):
    def setUp(self):
        self.cfg=normalize(None);self.c=ThemeController(self.cfg)
    def test_single_holo_switch_and_toggle(self):
        self.assertTrue(self.c.open_holo('cpu'))
        self.assertEqual('cpu',self.c.holo)
        self.assertTrue(self.c.open_holo('ram'))
        self.assertEqual('ram',self.c.holo)
        self.c.open_holo('ram');self.assertIsNone(self.c.holo)
    def test_disabled_plugin_cannot_open(self):
        cfg=normalize(None);cfg['enabled']['fans']=False
        self.c.reconfigure(cfg)
        self.assertFalse(self.c.open_holo('fans'))
    def test_top_transition_central(self):
        states=[];self.c.subscribe('state',states.append)
        self.c.set_top(False);self.assertEqual('retracted',states[-1].top)
        self.assertFalse(self.c.set_top(False))
        self.c.set_top(True);self.assertEqual('expanded',states[-1].top)
    def test_data_and_errors(self):
        changed=[];self.c.subscribe('data',changed.append)
        self.c.ingest({'type':'measurement','name':'cpu_fast','timestamp':1,'data':{'freq':2}})
        self.assertEqual({'freq':2},self.c.data['cpu_fast'])
        self.c.ingest({'type':'error','name':'cpu_fast','error':'unavailable'})
        self.assertEqual('unavailable',self.c.errors['cpu_fast'])
        self.assertEqual(['cpu_fast','cpu_fast'],changed)
    def test_stop_disables_transitions(self):
        self.c.stop();self.assertFalse(self.c.open_holo('cpu'))
        self.assertFalse(self.c.set_top(False))
