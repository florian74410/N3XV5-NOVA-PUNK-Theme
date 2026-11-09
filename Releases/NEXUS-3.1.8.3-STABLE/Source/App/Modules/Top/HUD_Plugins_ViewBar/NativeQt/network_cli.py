"""Configuration & nPerf import CLI for N3XV5 without mixing sources."""
from __future__ import annotations
import argparse
from pathlib import Path
from n3xvs_network_archive import CONFIG,_atomic_json,config,import_nperf_json,prune
p=argparse.ArgumentParser(description='N3XV5 Network — providers & journals')
sub=p.add_subparsers(dest='action',required=True)
c=sub.add_parser('provider');c.add_argument('name',choices=['speedtest','nperf'])
s=sub.add_parser('speedtest-client');s.add_argument('name',choices=['ookla','legacy'])
sub.add_parser('status')
sub.add_parser('prune')
i=sub.add_parser('import-nperf');i.add_argument('json_file',type=Path)
a=p.parse_args();cfg=config()
if a.action=='provider':
    cfg['preferred_provider']=a.name;_atomic_json(CONFIG,cfg)
    print('Fournisseur principal :',a.name)
elif a.action=='speedtest-client':
    cfg['preferred_speedtest_client']=a.name;_atomic_json(CONFIG,cfg)
    print('Client Speedtest préféré :',a.name)
elif a.action=='status':
    print('Configuration :',CONFIG)
    print('Principal :',cfg['preferred_provider'])
    print('Client Speedtest :',cfg['preferred_speedtest_client'])
    print('Serveurs verrouillés :',cfg['fixed_servers'])
    print('nPerf : import de fichiers de résultats externes non vérifiés, pas de CLI grand public vérifié')
elif a.action=='prune':print('Journaux éliminés :',prune())
elif a.action=='import-nperf':print('Journal créé :',import_nperf_json(a.json_file))
