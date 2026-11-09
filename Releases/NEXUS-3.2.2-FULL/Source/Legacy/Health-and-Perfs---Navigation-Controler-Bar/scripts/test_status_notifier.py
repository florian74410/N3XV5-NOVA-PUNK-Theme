"""Real private-session D-Bus test: item registration, pixels, activation and DBusMenu."""
import os,sys,tempfile,subprocess,time
from pathlib import Path
from PySide6.QtWidgets import QApplication
from healthbar.status_notifier import StatusNotifierHost,item_icon

CLIENT=r'''
import asyncio,sys
from pathlib import Path
from dbus_next.aio import MessageBus
from dbus_next.service import ServiceInterface,dbus_property,method
from dbus_next.constants import PropertyAccess
from dbus_next import Message,Variant
path=Path(sys.argv[1])
class Item(ServiceInterface):
 def __init__(self):super().__init__('org.kde.StatusNotifierItem')
 @dbus_property(access=PropertyAccess.READ)
 def Id(self)->'s':return 'novabar-qa-applet'
 @dbus_property(access=PropertyAccess.READ)
 def Title(self)->'s':return 'QA Native Applet'
 @dbus_property(access=PropertyAccess.READ)
 def Status(self)->'s':return 'Active'
 @dbus_property(access=PropertyAccess.READ)
 def IconName(self)->'s':return ''
 @dbus_property(access=PropertyAccess.READ)
 def IconPixmap(self)->'a(iiay)':return [[2,2,bytes([255,220,40,10])*4]]
 @dbus_property(access=PropertyAccess.READ)
 def Menu(self)->'o':return '/Menu'
 @method()
 def Activate(self,x:'i',y:'i'):path.write_text('activated')
class Menu(ServiceInterface):
 def __init__(self):super().__init__('com.canonical.dbusmenu')
 @method()
 def AboutToShow(self,parent:'i')->'b':path.write_text('about-to-show');return True
 @method()
 def GetLayout(self,parent:'i',depth:'i',names:'as')->'u(ia{sv}av)':
  assert path.read_text()=='about-to-show','Dynamic menu was not prepared'
  return [1,[0,{},[Variant('(ia{sv}av)',[7,{'label':Variant('s','Action native'),'enabled':Variant('b',True)},[]])]]]
 @method()
 def Event(self,item:'i',event:'s',data:'v',timestamp:'u'):path.write_text('menu-'+str(item))
class XApp(ServiceInterface):
 def __init__(self):super().__init__('org.x.StatusIcon')
 @dbus_property(access=PropertyAccess.READ)
 def Name(self)->'s':return 'Native Mint QA'
 @dbus_property(access=PropertyAccess.READ)
 def TooltipText(self)->'s':return 'Native Mint QA icon'
 @dbus_property(access=PropertyAccess.READ)
 def IconName(self)->'s':return 'utilities-terminal'
 @dbus_property(access=PropertyAccess.READ)
 def Visible(self)->'b':return True
 @method()
 def ButtonPress(self,x:'i',y:'i',button:'u',timestamp:'u',position:'i'):pass
 @method()
 def ButtonRelease(self,x:'i',y:'i',button:'u',timestamp:'u',position:'i'):path.write_text('xapp-'+str(button)+'-'+str(position))
async def run():
 bus=await MessageBus().connect();await bus.request_name('org.kde.StatusNotifierItem.NovaBarQA');bus.export('/StatusNotifierItem',Item());bus.export('/Menu',Menu())
 await bus.request_name('org.x.StatusIcon.NativeQA');bus.export('/org/x/StatusIcon/Icon',XApp())
 for _ in range(100):
  reply=await bus.call(Message(destination='org.kde.StatusNotifierWatcher',path='/StatusNotifierWatcher',interface='org.kde.StatusNotifierWatcher',member='RegisterStatusNotifierItem',signature='s',body=['org.kde.StatusNotifierItem.NovaBarQA']))
  if not reply.error_name:break
  await asyncio.sleep(.1)
 await asyncio.Event().wait()
asyncio.run(run())
'''

def wait_for(predicate,app,timeout=16):
 deadline=time.monotonic()+timeout
 while time.monotonic()<deadline:
  app.processEvents()
  if predicate():return
  time.sleep(.05)
 raise AssertionError('StatusNotifier D-Bus integration timed out')

def main():
 app=QApplication([]);host=StatusNotifierHost();rows=[];menus=[]
 host.items_changed.connect(lambda value:rows.__setitem__(slice(None),value));host.menu_ready.connect(lambda *args:menus.append(args));host.start()
 with tempfile.TemporaryDirectory() as temp:
  output=Path(temp)/'event';client=subprocess.Popen([sys.executable,'-c',CLIENT,str(output)])
  try:
   wait_for(lambda:any(r.get('Id')=='novabar-qa-applet' for r in rows),app)
   row=next(r for r in rows if r.get('Id')=='novabar-qa-applet')
   assert item_icon(row).pixmap(2,2).toImage().pixelColor(0,0).red()==220
   host.activate(row['key'],100,100);wait_for(lambda:output.exists() and output.read_text()=='activated',app)
   host.activate(row['key'],100,100,True);wait_for(lambda:bool(menus),app)
   assert menus[0][1][2][0][1]['label']=='Action native'
   host.menu_event(row['key'],7);wait_for(lambda:output.read_text()=='menu-7',app)
   wait_for(lambda:any(r.get('Id')=='Native Mint QA' for r in rows),app)
   xapp=next(r for r in rows if r.get('Id')=='Native Mint QA')
   host.activate(xapp['key'],100,100);wait_for(lambda:output.read_text()=='xapp-1-3',app)
   host.activate(xapp['key'],100,100,True);wait_for(lambda:output.read_text()=='xapp-3-3',app)
   client.terminate();client.wait(timeout=5)
   wait_for(lambda:not any(r.get('Id')=='novabar-qa-applet' for r in rows),app)
   print('PASS: real SNI registration, ARGB icon, activation, DBusMenu, XApp left/right clicks and removal')
  finally:
   if client.poll() is None:client.terminate();client.wait(timeout=5)
   host.stop()
   assert not host.isRunning()
if __name__=='__main__':main()
