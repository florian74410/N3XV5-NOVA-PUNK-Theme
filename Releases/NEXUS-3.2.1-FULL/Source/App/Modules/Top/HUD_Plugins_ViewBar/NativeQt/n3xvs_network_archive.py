"""N3XV5 network provenance, fixed server and 24h archives (no fake nPerf CLI).

The user can select nperf or speedtest as preferred provider. nPerf results
may be imported from an external measurement export; public
nPerf consumer CLI is not documented, so automated tests safely fall back to
Speedtest with an explicit fallback status rather than mislabelling results.
"""
from __future__ import annotations
import datetime as dt
import json
import math
import os
from pathlib import Path
import re
import shutil
import statistics
import subprocess
import threading
import time

ROOT = Path.home() / '.config/n3xvs-hud/Sauvegardes/Parametres'
PLUGINS = ('CPU','GPU','RAM','SSD','FANS','Network','POWER')
NETWORK = ROOT/'Plugins/Network'
STATS = NETWORK/'Statistiques'
CONFIG = NETWORK/'provider.json'
SOURCE_TAG = {'ookla':'Speedtest_Ookla','legacy':'Speedtest_CLI','nperf':'nPerf'}


def initialize():
    ROOT.mkdir(parents=True,exist_ok=True)
    try: ROOT.chmod(0o700)
    except OSError: pass
    (ROOT/'General').mkdir(exist_ok=True)
    for plugin in PLUGINS:
        (ROOT/'Plugins'/plugin).mkdir(parents=True,exist_ok=True)
    STATS.mkdir(parents=True,exist_ok=True)
    try: STATS.chmod(0o700)
    except OSError: pass
    if not CONFIG.is_file():
        _atomic_json(CONFIG,{'preferred_provider':'speedtest','preferred_speedtest_client':'ookla',
                             'fallback_when_unavailable':True,'fixed_servers':{},
                             'nperf_note':'Import de mesures nPerf uniquement : pas de CLI grand public officiel vérifié.'})
    # Do not alter the live settings schema; keep a dated snapshot for restoration.
    candidates=[Path.home()/'.config/n3xvs-hud/n3xvs-unified.json',
                Path.home()/'.config/n3xvs-hud-preview/n3xvs-top.json',
                Path.home()/'.config/health-perfs-bar/settings.json']
    for origin in candidates:
        if origin.is_file():
            dest=ROOT/'General'/('snapshot-'+origin.parent.name+'-'+origin.name)
            if not dest.exists():
                shutil.copy2(origin,dest)


def backup_runtime_preferences(path, prefs):
    """Keep live settings in place; export separate per-plugin snapshots on Apply."""
    initialize()
    general=ROOT/'General'
    stamp=dt.datetime.now().strftime('%Y%m%d-%H%M%S')
    if Path(path).is_file():
        dest=general/('N3XV5-'+stamp+'.json')
        shutil.copy2(path,dest)
        dest.chmod(0o600)
    hidden=set(prefs.get('hidden_modules',[]))
    for plugin in PLUGINS:
        slot={'SSD':'storage','Network':'network','FANS':'fans','POWER':'power'}.get(plugin,plugin.lower())
        settings={'enabled':slot not in hidden}
        if plugin=='FANS':settings['fan_max_rpm']=prefs.get('fan_max_rpm',{})
        if plugin=='Network':settings['net_speedtest_hourly']=prefs.get('net_speedtest_hourly',False)
        _atomic_json(ROOT/'Plugins'/plugin/'settings.json',settings)


def _atomic_json(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_name(path.name+'.tmp-'+str(os.getpid()))
    tmp.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    os.replace(tmp,path)


def config():
    initialize()
    try: item=json.loads(CONFIG.read_text(encoding='utf-8'))
    except (ValueError,OSError): item={}
    if not isinstance(item,dict): item={}
    if item.get('preferred_provider') not in ('nperf','speedtest'): item['preferred_provider']='speedtest'
    if item.get('preferred_speedtest_client') not in ('ookla','legacy'): item['preferred_speedtest_client']='ookla'
    if not isinstance(item.get('fixed_servers'),dict):item['fixed_servers']={}
    return item


def _clean(value,maxlen=60):
    s=re.sub(r'[^a-zA-Z0-9._-]+','-',str(value or 'unknown')).strip('._-')
    return (s[:maxlen] or 'unknown')


def _score(row):
    # Download as primary metric, upload secondary for a clear stable comparison.
    return float(row['download_mbps']) + 0.25*float(row['upload_mbps'])


def _is_suspicious_min(rows,minimum):
    """Only reject a low sample with sufficient same-provider/server evidence.
    Must be both under 35% of the median and far from the median by robust MAD.
    If distribution is broad, keep the minimum rather than conceal poor service.
    """
    if len(rows)<5:return False
    scores=[_score(r) for r in rows]
    med=statistics.median(scores)
    if med<=0:return False
    mad=statistics.median([abs(s-med) for s in scores])
    low=_score(minimum)
    return low<med*.35 and (med-low)>max(3*1.4826*mad,med*.45)


def _read_log(path):
    try:
        raw=path.read_text(encoding='utf-8')
        # Text format, human readable, with a JSON footer for precise restore.
        for line in raw.splitlines():
            if line.startswith('N3XV5_JSON='):
                entry=json.loads(line[len('N3XV5_JSON='):]);return entry if isinstance(entry,dict) else None
    except (OSError,ValueError,TypeError):pass
    return None


def prune(now=None):
    """Close complete 24h buckets aligned to the first test in each group.

    Each (provider, server ID) has independent buckets. For a closed window,
    retain best and robust worst; failed attempts are never scored as 0 Mbps.
    """
    now=float(now if now is not None else time.time())
    grouped={}
    for path in STATS.glob('*.log'):
        entry=_read_log(path)
        if not entry or entry.get('status')!='success':continue
        try: ts=float(entry['timestamp']); key=(entry['provider'],entry['server_id'])
        except (KeyError,ValueError,TypeError):continue
        if ts>now+300:continue
        grouped.setdefault(key,[]).append((ts,path,entry))
    count=0
    for key,records in grouped.items():
        records.sort(key=lambda r:r[0]);t0=records[0][0]
        buckets={}
        for rec in records:
            index=int((rec[0]-t0)//86400)
            buckets.setdefault(index,[]).append(rec)
        for index,group in buckets.items():
            if t0+(index+1)*86400>now:continue
            # Files created after compaction are naturally retained in current bucket.
            if len(group)<=2:continue
            rows=[r[2] for r in group]
            best=max(group,key=lambda r:_score(r[2]))
            minimum=min(group,key=lambda r:_score(r[2]))
            selected_rows=[r for r in group if r is not minimum] if _is_suspicious_min(rows,minimum[2]) else group
            worst=min(selected_rows,key=lambda r:_score(r[2])) if selected_rows else minimum
            for rec in group:
                if rec is best or rec is worst:continue
                try:rec[1].unlink();count+=1
                except OSError:pass
    # Errors never masquerade as throughput; only preserve recent failures.
    for path in STATS.glob('*.log'):
        entry=_read_log(path)
        if entry and entry.get('status')=='error':
            try:
                if float(entry.get('timestamp',now)) < now-86400:
                    path.unlink();count+=1
            except (ValueError,TypeError,OSError):pass
    return count


def log_measurement(*,provider,down=None,up=None,server_name=None,server_id=None,server_ip=None,
                    host=None,latency=None,error=None,when=None,fallback=False):
    initialize()
    when=float(when if when is not None else time.time())
    entry={'timestamp':when,'date_local':dt.datetime.fromtimestamp(when).isoformat(timespec='seconds'),
           'provider':str(provider),'source':SOURCE_TAG.get(provider,str(provider)),
           'server_id':str(server_id or 'unknown'),'server_name':str(server_name or 'unknown'),
           'server_ip':str(server_ip or 'unknown'),'server_host':str(host or 'unknown'),
           'status':'error' if error else 'success','fallback':bool(fallback)}
    if error:entry['error']=str(error)[:600]
    else:
        if not all(type(v) in (int,float) and math.isfinite(v) and v>=0 for v in (down,up)):
            raise ValueError('Invalid measured bandwidth')
        entry.update(download_mbps=round(float(down),4),upload_mbps=round(float(up),4),latency_ms=latency)
    stamp=dt.datetime.fromtimestamp(when).strftime('%Y-%m-%d:%H-%M-%S')
    basename='_'.join((stamp,_clean(entry['source']),_clean(entry['server_name']),
                       'Server'+_clean(entry['server_id']),_clean(entry['server_ip'])))
    filename=STATS/(basename+'.log')
    index=2
    while filename.exists():
        filename=STATS/(basename+f'-{index}.log');index+=1
    text=(f"Date: {entry['date_local']}\nSource: {entry['source']}\n"
          f"Serveur: {entry['server_name']}\nServerID: {entry['server_id']}\n"
          f"IP serveur: {entry['server_ip']}\nHote: {entry['server_host']}\n"
          f"Etat: {entry['status']}\nSecours: {'oui' if fallback else 'non'}\n")
    if error:text+=f'Erreur: {entry["error"]}\n'
    else:text+=(f'Download: {entry["download_mbps"]:.4f} Mbit/s\n'
                f'Upload: {entry["upload_mbps"]:.4f} Mbit/s\n'
                f'Latence: {latency if latency is not None else "inconnue"} ms\n')
    text+='N3XV5_JSON='+json.dumps(entry,ensure_ascii=False,sort_keys=True)+'\n'
    filename.write_text(text,encoding='utf-8')
    filename.chmod(0o600)
    prune(now=when)
    return filename


def import_nperf_json(path):
    """Import externally supplied nPerf measurements; origin must be verified by user.
    Must explicitly declare its source and server. No automatic nPerf test claimed.
    """
    item=json.loads(Path(path).read_text(encoding='utf-8'))
    if not isinstance(item,dict) or str(item.get('provider','')).lower()!='nperf':
        raise ValueError('Le fichier doit identifier la source officielle nPerf.')
    for k in ('download_mbps','upload_mbps','server_id','server_name'):
        if k not in item:raise ValueError('Champ absent : '+k)
    # Import cannot independently verify authenticity of a user supplied file.
    return log_measurement(provider='nperf',down=item['download_mbps'],up=item['upload_mbps'],
                           server_id=item['server_id'],server_name=item['server_name'],
                           server_ip=item.get('server_ip'),host=item.get('server_host'),
                           latency=item.get('latency_ms'),when=item.get('timestamp'))


def _available_clients(identify):
    found={}
    for name in ('speedtest','speedtest-cli'):
        exe=shutil.which(name)
        if not exe:continue
        kind=identify(exe)
        if kind in ('ookla','legacy') and kind not in found:found[kind]=exe
    return found


def install_worker(klass,parser,identify):
    """Replace only the test worker; leave Qt-facing start/summary API untouched."""
    def worker(self):
        preferred='speedtest';source='ookla';fallback=False
        try:
            cfg=config();preferred=cfg['preferred_provider']
            clients=_available_clients(identify)
            # nPerf consumer app offers no verified command/API for unattended tests.
            # No fake JSON or aliasing nPerf -> Ookla; explicitly mark fallback.
            if preferred=='nperf':
                if not cfg.get('fallback_when_unavailable',True):
                    raise RuntimeError('nPerf CLI non disponible : import JSON nPerf ou activer secours Speedtest.')
                fallback=True
            source=cfg['preferred_speedtest_client']
            if source not in clients:
                alternative='legacy' if source=='ookla' else 'ookla'
                if cfg.get('fallback_when_unavailable',True) and alternative in clients:
                    source=alternative;fallback=True
                else:raise RuntimeError('Client Speedtest sélectionné indisponible : installer Ookla CLI ou speedtest-cli.')
            exe=clients[source]
            locks=cfg['fixed_servers'];serverid=locks.get(source)
            if source=='ookla':
                cmd=[exe,'--accept-license','--accept-gdpr','--format=json']
                if serverid:cmd+=['--server-id='+str(serverid)]
            else:
                cmd=[exe,'--json','--secure']
                if serverid:cmd+=['--server',str(serverid)]
            p=subprocess.run(cmd,capture_output=True,text=True,timeout=150,check=False)
            if p.returncode:
                raise RuntimeError('Test '+SOURCE_TAG[source]+' échoué : '+(' '.join((p.stderr or p.stdout or '').split())[:180] or str(p.returncode)))
            # Ookla may emit a JSON log record before the final JSON result.
            raw=p.stdout.strip()
            if source=='ookla':
                records=[]
                for line in raw.splitlines():
                    try:
                        doc=json.loads(line)
                        if isinstance(doc,dict):records.append(doc)
                    except ValueError:pass
                done=next((v for v in reversed(records) if v.get('type')=='result'),None)
                if done is not None:raw=json.dumps(done)
            result=parser(raw,source)
            doc=json.loads(raw)
            server=doc.get('server') if isinstance(doc.get('server'),dict) else {}
            actual_id=str(server.get('id') or 'unknown')
            if serverid and actual_id!=str(serverid):
                raise RuntimeError('ServerID changé : attendu '+str(serverid)+', reçu '+actual_id)
            result.update(server_id=actual_id,server_ip=server.get('ip') or 'unknown',
                          server_host=server.get('host') or 'unknown',
                          server=server.get('name') or result.get('server') or 'unknown',
                          provider='speedtest',fallback=fallback)
            if not serverid and actual_id!='unknown':
                locks[source]=actual_id;cfg['fixed_servers']=locks;_atomic_json(CONFIG,cfg)
            log_measurement(provider=source,down=result['download_mbps'],up=result['upload_mbps'],
                            server_name=result['server'],server_id=actual_id,
                            server_ip=result['server_ip'],host=result['server_host'],
                            latency=result.get('latency_ms'),fallback=fallback)
            with self.lock:self.result=result;self.error=None
        except (OSError,ValueError,RuntimeError,subprocess.TimeoutExpired) as exc:
            message=str(exc)[:245]
            try:log_measurement(provider=source,error=message,fallback=fallback)
            except (OSError,ValueError):pass
            with self.lock:self.error=message
        finally:
            with self.lock:self.running=False
    klass._work=worker
    # Housekeeping even when hourly bandwidth tests are disabled.
    def housekeeping():
        while True:
            try:
                initialize();prune()
            except (OSError,ValueError):pass
            time.sleep(3600)
    thread=threading.Thread(target=housekeeping,daemon=True,name='n3xvs-network-retention')
    thread.start()
