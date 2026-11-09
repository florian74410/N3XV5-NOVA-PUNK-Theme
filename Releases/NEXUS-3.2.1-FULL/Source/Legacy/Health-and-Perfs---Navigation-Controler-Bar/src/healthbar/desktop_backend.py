"""X11 task list and reversible native-panel visibility, without deleting XFCE configuration."""
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from .config import data_dir


def x11_ready():
    from PySide6.QtWidgets import QApplication
    return sys.platform.startswith('linux') and bool(os.getenv('DISPLAY')) and QApplication.platformName() == 'xcb'


class DesktopBackend:
    def _connect(self):
        from Xlib import display
        return display.Display()

    @staticmethod
    def prop(con, window, name, default=None):
        value=window.get_full_property(con.intern_atom(name),0)
        return value.value if value is not None else default

    def snapshot(self):
        if not x11_ready():return [],None
        con=None
        try:
            con=self._connect();root=con.screen().root
            active=self.prop(con,root,'_NET_ACTIVE_WINDOW',[])
            desktop=self.prop(con,root,'_NET_CURRENT_DESKTOP',[0])[0]
            rows=[]
            skip=con.intern_atom('_NET_WM_STATE_SKIP_TASKBAR')
            dock=con.intern_atom('_NET_WM_WINDOW_TYPE_DOCK')
            for xid in self.prop(con,root,'_NET_CLIENT_LIST_STACKING',self.prop(con,root,'_NET_CLIENT_LIST',[])):
                try:
                    window=con.create_resource_object('window',int(xid))
                    if skip in self.prop(con,window,'_NET_WM_STATE',[]):continue
                    if dock in self.prop(con,window,'_NET_WM_WINDOW_TYPE',[]):continue
                    if self.prop(con,window,'_NET_WM_PID',[0])[0] == os.getpid():continue
                    if self.prop(con,window,'_NET_WM_DESKTOP',[desktop])[0] not in (desktop,0xffffffff):continue
                    raw=self.prop(con,window,'_NET_WM_NAME')
                    name=bytes(raw).decode('utf-8','replace') if raw is not None else window.get_wm_name()
                    if not name:continue
                    classes=window.get_wm_class() or ('application-x-executable',)
                    rows.append({'id':int(xid),'name':str(name),'icon':classes[0].lower()})
                except Exception:continue
            return rows,int(active[0]) if len(active) else None
        except Exception:return [],None
        finally:
            if con:con.close()

    def window_icon(self,xid):
        """Read the actual EWMH application icon when a theme lookup is insufficient."""
        from PySide6.QtGui import QIcon,QImage,QPixmap
        if not x11_ready():return QIcon()
        con=None
        try:
            con=self._connect();window=con.create_resource_object('window',int(xid))
            values=self.prop(con,window,'_NET_WM_ICON',[]);index=0;icons=[]
            while index+2<=len(values):
                w,h=int(values[index]),int(values[index+1]);index+=2
                if w<=0 or h<=0 or w*h>1024*1024 or index+w*h>len(values):break
                if w<=256 and h<=256:icons.append((w,h,index))
                index+=w*h
            if not icons:return QIcon()
            w,h,index=min(icons,key=lambda v:abs(v[0]-40));image=QImage(w,h,QImage.Format.Format_ARGB32)
            for y in range(h):
                for x in range(w):image.setPixel(x,y,int(values[index+y*w+x]))
            return QIcon(QPixmap.fromImage(image))
        except Exception:return QIcon()
        finally:
            if con:con.close()

    def action(self,xid,close=False,minimize=False):
        if not x11_ready():return False
        from Xlib import X,protocol
        con=None
        try:
            con=self._connect();root=con.screen().root;window=con.create_resource_object('window',int(xid))
            name='_NET_CLOSE_WINDOW' if close else 'WM_CHANGE_STATE' if minimize else '_NET_ACTIVE_WINDOW'
            values=[3,0,0,0,0] if minimize else [0,2,0,0,0] if close else [2,X.CurrentTime,0,0,0]
            root.send_event(protocol.event.ClientMessage(window=window,client_type=con.intern_atom(name),data=(32,values)),
                            event_mask=X.SubstructureRedirectMask|X.SubstructureNotifyMask)
            con.flush();return True
        except Exception:return False
        finally:
            if con:con.close()

    def native_bottom_panels(self,bounds):
        if not x11_ready():return []
        con=None;rows=[]
        try:
            from Xlib import X
            con=self._connect();root=con.screen().root
            ids=set(int(i) for i in self.prop(con,root,'_NET_CLIENT_LIST',[]))
            ids.update(child.id for child in root.query_tree().children)
            for xid in ids:
                try:
                    w=con.create_resource_object('window',xid)
                    classes=w.get_wm_class() or ()
                    if not any('xfce4-panel' in c.lower() for c in classes):continue
                    if w.get_attributes().map_state != X.IsViewable:continue
                    geo=w.get_geometry();point=root.translate_coords(w,0,0)
                    # Coordinates are screen-global, including monitors to the left.
                    if geo.width < 100 or geo.height > 180:continue
                    if point.y+geo.height < bounds.bottom()-6:continue
                    if point.y > bounds.bottom()+2 or point.y < bounds.center().y():continue
                    if point.x+geo.width <= bounds.left() or point.x > bounds.right():continue
                    rows.append({'id':xid,'pid':int(self.prop(con,w,'_NET_WM_PID',[0])[0])})
                except Exception:continue
        except Exception:pass
        finally:
            if con:con.close()
        return rows

    def set_panel_visible(self,rows,visible):
        con=None;ok=True
        try:
            con=self._connect()
            for row in rows:
                try:
                    window=con.create_resource_object('window',int(row['id']))
                    if not any('xfce4-panel' in c.lower() for c in (window.get_wm_class() or ())):continue
                    pid=int(self.prop(con,window,'_NET_WM_PID',[0])[0])
                    if row.get('pid') and pid != row['pid']:continue
                    if visible:window.map()
                    else:window.unmap()
                except Exception:ok=False
            con.sync()
        except Exception:ok=False
        finally:
            if con:con.close()
        return ok


class NativePanelGuard:
    def __init__(self,backend=None):
        self.backend=backend or DesktopBackend()
        self.path=data_dir()/'native-panel-visibility.json'
        self.rows=[];self.reveal_until=0;self.watchdog=None
        if self.path.exists():
            try:
                import psutil
                state=json.loads(self.path.read_text())
                try:alive=psutil.Process(state['owner']).create_time()==state.get('owner_started')
                except psutil.Error:alive=False
                if not alive and state.get('display')==os.getenv('DISPLAY'):
                    if self.backend.set_panel_visible(state.get('panels',[]),True):self.path.unlink(missing_ok=True)
                    else:self.rows=state.get('panels',[])
            except (OSError,ValueError,KeyError,TypeError):pass

    def hide(self,bounds):
        if not x11_ready() or time.monotonic()<self.reveal_until:return
        found=self.backend.native_bottom_panels(bounds)
        known={r['id'] for r in self.rows}
        added=[r for r in found if r['id'] not in known]
        if added or (self.rows and self.watchdog is None):
            rows=self.rows+added
            self.path.parent.mkdir(parents=True,exist_ok=True)
            temp=self.path.with_suffix('.tmp')
            import psutil
            try:started=psutil.Process().create_time()
            except psutil.Error:return  # Never hide without a usable recovery identity.
            temp.write_text(json.dumps({'owner':os.getpid(),'owner_started':started,
                                        'display':os.getenv('DISPLAY'),'panels':rows}))
            temp.replace(self.path)  # Backup BEFORE unmapping anything.
            self.rows=rows
            if self.watchdog is None:
                command=([sys.executable] if getattr(sys,'frozen',False) else [sys.executable,'-m','healthbar'])
                try:self.watchdog=subprocess.Popen(command+['--restore-xfce-after-pid',str(os.getpid())],
                        stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
                except OSError:
                    self.path.unlink(missing_ok=True);self.rows=[];return
        if self.rows:self.backend.set_panel_visible(self.rows,False)

    def reveal(self):
        self.reveal_until=time.monotonic()+30
        self.backend.set_panel_visible(self.rows,True)

    def restore(self):
        if self.rows and not self.backend.set_panel_visible(self.rows,True):return False
        self.path.unlink(missing_ok=True);self.rows=[]
        return True


def restore_after_exit(pid):
    """Separate unprivileged watchdog restores the original even after a crash."""
    import psutil
    path=data_dir()/'native-panel-visibility.json'
    try:
        while path.exists():
            state=json.loads(path.read_text())
            if state.get('owner')!=pid:return
            try:alive=psutil.Process(pid).create_time()==state.get('owner_started')
            except psutil.Error:alive=False
            if not alive:
                os.environ['DISPLAY']=state.get('display') or os.environ.get('DISPLAY','')
                if DesktopBackend().set_panel_visible(state.get('panels',[]),True):path.unlink(missing_ok=True)
                return
            time.sleep(1)
    except (OSError,ValueError,TypeError):return
