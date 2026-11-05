"""Dependency-free behavioral tests for N3XV5 2.2.5 supplemental metrics."""
import sys, json, ast
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
MOD=ROOT/'App/Modules/Top/HUD_Plugins_ViewBar/NativeQt'
sys.path.insert(0,str(MOD))
import n3xvs_metrics as m

def run():
    assert '300 MB/s' in m.storage_caps({'storage_technology':'SATA', 'storage_sata_link':'3.0 Gb/s'})
    assert '600 MB/s' in m.storage_caps({'storage_technology':'SATA', 'storage_sata_link':'6.0 Gb/s'})
    assert 'inconnu' in m.storage_caps({'storage_technology':'SATA'})
    assert m.storage_caps({'storage_technology':'NVMe'}).startswith('NVMe')
    assert m.power_labels({})[0]=='SONDE —'
    assert m.power_labels({'cpu_power_w':49.3,'gpu_power_w':21.7})[0]=='49+22 W'
    assert m.power_labels({'battery_discharge_w':17.6})[0]=='17.6 W'
    assert 'inconnu' in m.power_labels({'cpu_power_w':30})[1]
    ookla=m._parse_speedtest_json(json.dumps({'download':{'bandwidth':12500000},'upload':{'bandwidth':6250000}}),'ookla')
    assert ookla['download_mbps']==100 and ookla['upload_mbps']==50
    legacy=m._parse_speedtest_json(json.dumps({'download':100000000,'upload':50000000}),'legacy')
    assert legacy['download_mbps']==100 and legacy['upload_mbps']==50
    assert m.SPEED_TEST.result is None
    top=(MOD/'n3xvs_top_native.py').read_text()
    ast.parse(top)
    assert "['#24bfff']*10+['#31dc78']*5+['#ff9c37']*3+['#f42b4b']*2" in top
    assert 'telemetry_refresh_s' in top and 'visual_fps' in top
    assert 'QScrollArea(dlg)' in top
    assert 'SPEED_TEST.start' in top
    print('OK — 20 LED arcs, SATA theory, sensor provenance, speedtest parsing, refresh config')

if __name__=='__main__':run()
