"""Read real desktop state outside the GUI thread. Never invent unavailable values."""
import os
import re
import shutil
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
import psutil
from .system_env import native_env


def query(command):
    if not shutil.which(command[0]):return None
    try:
        result=subprocess.run(command,env=dict(native_env(),LC_ALL='C'),capture_output=True,text=True,timeout=1.4)
        return result.stdout.strip() if result.returncode==0 else None
    except (OSError,subprocess.TimeoutExpired):return None


def fields(line):
    return [s.replace('\\:',':').replace('\\\\','\\') for s in re.split(r'(?<!\\):',line)]


def read_status():
    result={'network':None,'volume':None,'muted':None,'bluetooth':None,'battery':None,'vpn':False}
    devices=query(['nmcli','-t','-f','DEVICE,TYPE,STATE,CONNECTION','device','status'])
    if devices is not None:
        rows=[fields(line) for line in devices.splitlines()]
        connected=[r for r in rows if len(r)>=4 and r[2]=='connected' and r[1] in ('wifi','ethernet')]
        result['network']={'kind':connected[0][1],'name':connected[0][3],'device':connected[0][0]} if connected else {'kind':'disconnected','name':'Déconnecté'}
        result['vpn']=any(len(r)>2 and r[2]=='connected' and r[1] in ('tun','wireguard','vpn') for r in rows)
    volume=query(['pactl','get-sink-volume','@DEFAULT_SINK@'])
    if volume is not None:
        values=re.findall(r'(\d+)%',volume)
        if values:result['volume']=min(150,max(0,round(sum(map(int,values))/len(values))))
    mute=query(['pactl','get-sink-mute','@DEFAULT_SINK@'])
    if mute is not None:result['muted']=mute.endswith('yes')
    bt=query(['bluetoothctl','show'])
    if bt:result['bluetooth']='Powered: yes' in bt
    try:
        battery=psutil.sensors_battery()
        if battery:result['battery']={'percent':round(battery.percent),'plugged':battery.power_plugged}
    except (AttributeError,OSError):pass
    return result


class DesktopStatus:
    def __init__(self):
        self.executor=ThreadPoolExecutor(max_workers=1,thread_name_prefix='NovaBar-status');self.future=None;self.next_poll=0
        self.value={'network':None,'volume':None,'muted':None,'bluetooth':None,'battery':None,'vpn':False}
    def poll(self):
        if self.future is not None and self.future.done():
            try:self.value=self.future.result()
            except Exception:pass
            self.future=None;self.next_poll=time.monotonic()+3
        if self.future is None and time.monotonic()>=self.next_poll:self.future=self.executor.submit(read_status)
        return self.value
    def close(self):self.executor.shutdown(wait=False,cancel_futures=True)
