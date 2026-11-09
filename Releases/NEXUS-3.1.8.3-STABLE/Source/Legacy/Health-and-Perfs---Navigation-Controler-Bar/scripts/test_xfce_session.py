"""Isolated real X11/XFCE integration, run inside xvfb-run + dbus-run-session."""
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
from Xlib import X
from healthbar.config import Settings
from healthbar.desktop_backend import DesktopBackend
from healthbar.bottom_dock import BottomDock


def wait_for(check,app,timeout=12):
    deadline=time.monotonic()+timeout
    while time.monotonic()<deadline:
        app.processEvents()
        value=check()
        if value:return value
        time.sleep(.1)
    raise AssertionError('Timed out waiting for isolated XFCE session')


def main():
    processes=[]
    with tempfile.TemporaryDirectory(prefix='novabar-xfce-') as temp:
        os.environ.update(XDG_CONFIG_HOME=temp+'/config',HEALTHBAR_DATA_DIR=temp+'/data',QT_QPA_PLATFORM='xcb')
        Path(os.environ['XDG_CONFIG_HOME']).mkdir()
        def setting(path,kind,value,array=False):
            command=['xfconf-query','-c','xfce4-panel','-p',path,'-n','-t',kind,'-s',str(value)]
            if array:command.append('-a')
            subprocess.run(command,check=True,timeout=15)
        setting('/panels','int',1,True)
        setting('/panels/panel-1/position','string','p=10;x=640;y=700')
        setting('/panels/panel-1/size','uint',48)
        setting('/panels/panel-1/length','uint',100)
        setting('/panels/panel-1/position-locked','bool','true')
        setting('/panels/panel-1/plugin-ids','int',1,True)
        setting('/plugins/plugin-1','string','applicationsmenu')
        app=QApplication([]);app.setQuitOnLastWindowClosed(False)
        backend=DesktopBackend();dock=None
        try:
            processes.append(subprocess.Popen(['xfwm4','--compositor=off'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL))
            processes.append(subprocess.Popen(['xfce4-panel','--disable-wm-check'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL))
            bounds=app.primaryScreen().geometry()
            panels=wait_for(lambda:backend.native_bottom_panels(bounds),app)
            dock=BottomDock(Settings(configured=True,dock_app_paths=[]))
            wait_for(lambda:dock.native.rows,app)
            con=backend._connect()
            assert all(con.create_resource_object('window',r['id']).get_attributes().map_state==X.IsUnmapped for r in panels)
            code="from PySide6.QtWidgets import QApplication,QWidget; a=QApplication([]); w=QWidget(); w.setWindowTitle('NovaBar QA task'); w.resize(300,200); w.show(); a.exec()"
            processes.append(subprocess.Popen([sys.executable,'-c',code],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL))
            row=wait_for(lambda:next((r for r in backend.snapshot()[0] if r['name']=='NovaBar QA task'),None),app)
            assert backend.action(row['id'])
            wait_for(lambda:backend.snapshot()[1]==row['id'],app)
            assert backend.action(row['id'],minimize=True)
            wait_for(lambda:con.create_resource_object('window',row['id']).get_attributes().map_state==X.IsUnmapped,app)
            assert backend.action(row['id'])
            wait_for(lambda:con.create_resource_object('window',row['id']).get_attributes().map_state==X.IsViewable,app)
            dock.collapse();assert not dock.isVisible()
            dock.expand();assert dock.isVisible()
            dock.close()
            wait_for(lambda:all(con.create_resource_object('window',r['id']).get_attributes().map_state==X.IsViewable for r in panels),app)
            assert not dock.native.path.exists()
            # Kill a separate NovaBar surface without closeEvent: its watchdog must recover XFCE.
            crash_code="from PySide6.QtWidgets import QApplication; from PySide6.QtCore import QTimer; from healthbar.bottom_dock import BottomDock; from healthbar.config import Settings; import os; a=QApplication([]); d=BottomDock(Settings(configured=True,dock_app_paths=[])); QTimer.singleShot(1800,lambda:os._exit(9)); a.exec()"
            crashed=subprocess.Popen([sys.executable,'-c',crash_code],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            processes.append(crashed)
            wait_for(lambda:all(con.create_resource_object('window',r['id']).get_attributes().map_state==X.IsUnmapped for r in panels),app)
            assert crashed.wait(timeout=8)==9
            wait_for(lambda:all(con.create_resource_object('window',r['id']).get_attributes().map_state==X.IsViewable for r in panels),app)
            assert not dock.native.path.exists()
            con.close()
            print('PASS: real XFCE hidden/restored after close AND crash; task activation/minimize; autonomous dock')
        finally:
            if dock:dock.close()
            for process in reversed(processes):
                process.terminate()
                try:process.wait(timeout=5)
                except subprocess.TimeoutExpired:process.kill()

if __name__=='__main__':main()
