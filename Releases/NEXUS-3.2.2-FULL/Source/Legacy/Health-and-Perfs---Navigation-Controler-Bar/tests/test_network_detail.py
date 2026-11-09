import subprocess
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from healthbar.network_detail import NetworkSampler, PingProbe, format_rate
from healthbar.telemetry import Telemetry


def counter(received, sent):
    return SimpleNamespace(bytes_recv=received, bytes_sent=sent)


class NetworkDetailTests(unittest.TestCase):
    def test_small_traffic_remains_visible_and_missing_is_distinct_from_idle(self):
        self.assertEqual(format_rate(None), '—')
        self.assertEqual(format_rate(0), '0 B/s')
        self.assertEqual(format_rate(.00012), '120 B/s')
        self.assertEqual(format_rate(.012), '12.0 kB/s')
        self.assertEqual(format_rate(2.7), '2.70 MB/s')

    def test_active_route_first_and_no_docker_double_count(self):
        sampler=NetworkSampler()
        stats={'docker0':SimpleNamespace(isup=True,speed=1000), 'wlan0':SimpleNamespace(isup=True,speed=100)}
        api=SimpleNamespace(net_if_stats=lambda:stats)
        with patch('healthbar.network_detail.default_interface',return_value='wlan0'):
            api.net_io_counters=lambda pernic=True:{'docker0':counter(0,0),'wlan0':counter(0,0)}
            self.assertIsNone(sampler.sample(api,10)['net_down_mbs'])
            api.net_io_counters=lambda pernic=True:{'docker0':counter(1000000,2000000),'wlan0':counter(1000,2000)}
            data=sampler.sample(api,11)
            self.assertEqual(data['net_interfaces'][0]['name'],'wlan0')
            self.assertEqual(data['net_interface'],'wlan0')
            self.assertEqual(data['net_down_mbs'],.001)
            self.assertEqual(data['net_up_mbs'],.002)
            api.net_io_counters=lambda pernic=True:{'wlan0':counter(10,20)}
            self.assertIsNone(sampler.sample(api,12)['net_down_mbs'])

    def test_ping_is_icmp_bounded_cached_and_not_a_fake_zero(self):
        probe=PingProbe()
        with patch('healthbar.network_detail.subprocess.run',return_value=SimpleNamespace(returncode=0,stdout='64 bytes: time=23.4 ms')) as run:
            self.assertEqual(probe.sample(10)['net_ping_ms'],23.4)
            self.assertEqual(probe.sample(15)['net_ping_ms'],23.4)
            self.assertEqual(run.call_count,1)
            self.assertEqual(run.call_args.kwargs['timeout'],1.5)
            self.assertIn('1.1.1.1',run.call_args.args[0])
        with patch('healthbar.network_detail.subprocess.run',side_effect=subprocess.TimeoutExpired('ping',1.5)):
            self.assertIsNone(probe.sample(21)['net_ping_ms'])
            self.assertEqual(probe.result['net_ping_status'],'ICMP indisponible')

    def test_network_continues_when_cpu_probe_fails(self):
        sampler=Telemetry()
        with patch('healthbar.telemetry.psutil.cpu_percent',side_effect=OSError), \
             patch.object(sampler.network,'sample',return_value={'net_down_mbs':.1,'net_up_mbs':.01}), \
             patch.object(sampler.ping,'sample',return_value={'net_ping_ms':None}), \
             patch('healthbar.telemetry.nvidia_gpu',return_value={}):
            data=sampler.sample()
        self.assertEqual(data['net_down_mbs'],.1)
        self.assertEqual(data['net_up_mbs'],.01)
