"""StatusNotifier host: display existing desktop items without taking XFCE's watcher away.

Uses a private asyncio D-Bus connection in a worker; all widget work stays in Qt.
"""
import asyncio
import os
import queue
import time
from PySide6.QtCore import QThread,Signal
from PySide6.QtGui import QImage,QPixmap,QIcon
from .cockpit_style import app_icon,lookup_icon

WATCHERS=('org.kde.StatusNotifierWatcher','org.freedesktop.StatusNotifierWatcher')


def unwrap(value):
    if hasattr(value,'signature') and hasattr(value,'value'):return unwrap(value.value)
    if isinstance(value,dict):return {k:unwrap(v) for k,v in value.items()}
    if isinstance(value,(list,tuple)):return [unwrap(v) for v in value]
    return value


def item_address(key):
    service,sep,path=key.partition('/')
    return service,'/'+path if sep else '/StatusNotifierItem'


def item_icon(record):
    name=record.get('AttentionIconName') if record.get('Status')=='NeedsAttention' else record.get('IconName')
    if name:
        icon=lookup_icon(name)
        if icon.isNull() and record.get('IconThemePath'):
            from pathlib import Path
            root=Path(record['IconThemePath'])
            for suffix in ('.png','.svg','.xpm'):
                path=root/(name+suffix)
                if path.is_file():icon=QIcon(str(path));break
        if not icon.isNull():return icon
    images=record.get('AttentionIconPixmap') if record.get('Status')=='NeedsAttention' else record.get('IconPixmap')
    images=images or record.get('IconPixmap') or []
    valid=[v for v in images if isinstance(v,(list,tuple)) and len(v)==3 and isinstance(v[0],int) and isinstance(v[1],int) and 0<v[0]<=512 and 0<v[1]<=512 and len(v[2])==v[0]*v[1]*4]
    if valid:
        w,h,data=min(valid,key=lambda v:abs(v[0]-32));src=bytes(data);rgba=bytearray(src)
        rgba[0::4]=src[1::4];rgba[1::4]=src[2::4];rgba[2::4]=src[3::4];rgba[3::4]=src[0::4]
        return QIcon(QPixmap.fromImage(QImage(bytes(rgba),w,h,w*4,QImage.Format.Format_RGBA8888).copy()))
    return app_icon('', 'application')


class StatusNotifierHost(QThread):
    items_changed=Signal(list);menu_ready=Signal(str,object,int,int)
    def __init__(self,parent=None):
        super().__init__(parent);self.actions=queue.SimpleQueue();self._closed=False;self.records={};self._last=None
    def activate(self,key,x,y,context=False):self.actions.put(('context' if context else 'activate',key,x,y))
    def menu_event(self,key,item_id):self.actions.put(('menu',key,item_id,0))
    def stop(self):
        self._closed=True;self.requestInterruption();self.wait(6000)
    def run(self):
        try:asyncio.run(self.session())
        except Exception:pass  # Desktop without a session bus still has native status controls.

    async def call(self,service,path,interface,member,signature='',body=None):
        from dbus_next import Message,MessageType
        reply=await asyncio.wait_for(self.bus.call(Message(destination=service,path=path,interface=interface,member=member,signature=signature,body=body or [])),timeout=1.2)
        if reply.message_type==MessageType.ERROR:raise RuntimeError(reply.error_name)
        return unwrap(reply.body)

    async def xapp_records(self):
        """Linux Mint's native XApp indicators use ObjectManager, not SNI."""
        records={}
        try:names=(await self.call('org.freedesktop.DBus','/org/freedesktop/DBus','org.freedesktop.DBus','ListNames'))[0]
        except Exception:return records
        for service in [s for s in names if s.startswith('org.x.StatusIcon.')][:64]:
            if self._closed:break
            try:
                objects=(await self.call(service,'/org/x/StatusIcon','org.freedesktop.DBus.ObjectManager','GetManagedObjects'))[0]
                for path,interfaces in objects.items():
                    props=interfaces.get('org.x.StatusIcon')
                    if not props or not props.get('Visible',True):continue
                    key=service+path
                    records[key]={'key':key,'service':service,'path':path,'interface':'org.x.StatusIcon',
                        'Id':props.get('Name',service),'Title':props.get('TooltipText') or props.get('Label') or props.get('Name',service),
                        'IconName':props.get('IconName',''),'Status':'Active',
                        '_menu_open':props.get('PrimaryMenuIsOpen',False) or props.get('SecondaryMenuIsOpen',False)}
            except Exception:continue
        return records

    async def session(self):
        from dbus_next.aio import MessageBus
        from dbus_next import BusType,Message,MessageType,Variant,NameFlag,RequestNameReply
        from dbus_next.service import ServiceInterface,dbus_property,method,signal
        from dbus_next.constants import PropertyAccess
        self.bus=await asyncio.wait_for(MessageBus(bus_type=BusType.SESSION).connect(),timeout=2)
        host_name=f'org.kde.StatusNotifierHost-NovaBar{os.getpid()}'
        await self.bus.request_name(host_name)
        await self.bus.request_name(f'org.x.StatusIconMonitor.NovaBar_{os.getpid()}')
        registered=set();owned_items=set()
        class Watcher(ServiceInterface):
            def __init__(self):super().__init__('org.kde.StatusNotifierWatcher')
            @dbus_property(access=PropertyAccess.READ)
            def RegisteredStatusNotifierItems(self)->'as':return list(owned_items)
            @dbus_property(access=PropertyAccess.READ)
            def IsStatusNotifierHostRegistered(self)->'b':return True
            @dbus_property(access=PropertyAccess.READ)
            def ProtocolVersion(self)->'i':return 0
            @method()
            def RegisterStatusNotifierItem(self,service:'s'):pass
            @method()
            def RegisterStatusNotifierHost(self,service:'s'):pass
            @signal()
            def StatusNotifierItemRegistered(self,key)->'s':return key
            @signal()
            def StatusNotifierItemUnregistered(self,key)->'s':return key
            @signal()
            def StatusNotifierHostRegistered(self):pass
        watcher=Watcher();owns=False
        def register_message(message):
            if owns and message.path=='/StatusNotifierWatcher' and message.interface=='org.kde.StatusNotifierWatcher' and message.member=='RegisterStatusNotifierItem' and message.signature=='s':
                raw=message.body[0];key=(message.sender+raw) if raw.startswith('/') else raw if '/' in raw else raw+'/StatusNotifierItem'
                if key not in owned_items:owned_items.add(key);watcher.StatusNotifierItemRegistered(key)
                return Message.new_method_return(message)
        self.bus.add_message_handler(register_message)
        try:
            next_poll=0
            while not self._closed:
                if time.monotonic()>=next_poll:
                    keys=set();found=False
                    for service in WATCHERS:
                        try:
                            values=await self.call(service,'/StatusNotifierWatcher','org.freedesktop.DBus.Properties','Get','ss',[service,'RegisteredStatusNotifierItems'])
                            keys.update(values[0] or []);found=True
                            owner=(await self.call('org.freedesktop.DBus','/org/freedesktop/DBus','org.freedesktop.DBus','GetNameOwner','s',[service]))[0]
                            if (service,owner) not in registered:
                                await self.call(service,'/StatusNotifierWatcher',service,'RegisterStatusNotifierHost','s',[host_name]);registered.add((service,owner))
                        except Exception:continue
                    if not found and not owns:
                        reply=await self.bus.request_name(WATCHERS[0],NameFlag.DO_NOT_QUEUE)
                        if reply==RequestNameReply.PRIMARY_OWNER:
                            self.bus.export('/StatusNotifierWatcher',watcher);owns=True
                    records={}
                    for key in sorted(keys)[:64]:
                        if self._closed:break
                        service,path=item_address(key)
                        for interface in ('org.kde.StatusNotifierItem','org.freedesktop.StatusNotifierItem'):
                            try:
                                props=(await self.call(service,path,'org.freedesktop.DBus.Properties','GetAll','s',[interface]))[0]
                                if not props:continue
                                props.update(key=key,service=service,path=path,interface=interface)
                                if props.get('Status')!='Passive':records[key]=props
                                break
                            except Exception:continue
                        else:
                            if key in owned_items:owned_items.discard(key);watcher.StatusNotifierItemUnregistered(key)
                    records.update(await self.xapp_records())
                    self.records=records
                    serial=repr(records)
                    if serial!=self._last:self._last=serial;self.items_changed.emit(list(records.values()))
                    next_poll=time.monotonic()+2
                # Bound work and cancellation latency even for a busy applet.
                for _ in range(12):
                    if self._closed:break
                    try:action,key,x,y=self.actions.get_nowait()
                    except queue.Empty:break
                    record=self.records.get(key)
                    if not record:continue
                    try:
                        if record.get('interface')=='org.x.StatusIcon':
                            button=3 if action=='context' else 1
                            await self.call(record['service'],record['path'],'org.x.StatusIcon','ButtonPress','iiuui',[x,y,button,0,3])
                            await self.call(record['service'],record['path'],'org.x.StatusIcon','ButtonRelease','iiuui',[x,y,button,0,3])
                        elif action=='menu':
                            await self.call(record['service'],record.get('Menu','/MenuBar'),'com.canonical.dbusmenu','Event','isvu',[x,'clicked',Variant('i',0),0])
                        elif action=='context' or record.get('ItemIsMenu'):
                            menu=record.get('Menu')
                            if menu and menu!='/':
                                try:await self.call(record['service'],menu,'com.canonical.dbusmenu','AboutToShow','i',[0])
                                except Exception:pass
                                layout=(await self.call(record['service'],menu,'com.canonical.dbusmenu','GetLayout','iias',[0,-1,[]]))[1]
                                self.menu_ready.emit(key,layout,x,y)
                            else:await self.call(record['service'],record['path'],record['interface'],'ContextMenu','ii',[x,y])
                        else:await self.call(record['service'],record['path'],record['interface'],'Activate','ii',[x,y])
                    except Exception:pass
                await asyncio.sleep(.1)
        finally:self.bus.disconnect()
