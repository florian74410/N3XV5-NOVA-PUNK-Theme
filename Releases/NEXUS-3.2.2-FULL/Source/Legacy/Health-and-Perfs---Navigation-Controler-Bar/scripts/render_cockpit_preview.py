"""Render real shipped widgets with explicit demonstration data; no desktop capture."""
import os,tempfile
os.environ['QT_QPA_PLATFORM']='offscreen'
from pathlib import Path
from unittest.mock import patch
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QRect
from healthbar.config import Settings
from healthbar.bottom_dock import BottomDock
from healthbar.app_catalog import ApplicationLauncher,Application
app=QApplication([])
out=Path('Assets/Previews');out.mkdir(exist_ok=True)
with tempfile.TemporaryDirectory() as t,patch.dict(os.environ,HEALTHBAR_DATA_DIR=t):
    paths=[]
    for name,icon in [('Firefox','firefox'),('Fichiers','folder'),('Terminal','utilities-terminal'),('Éditeur','accessories-text-editor')]:
        path=Path(t)/(name+'.desktop');path.write_text('[Desktop Entry]\nType=Application\nName='+name+'\nIcon='+icon+'\nExec=true\n');paths.append(str(path))
    dock=BottomDock(Settings(configured=True,dock_app_paths=paths,xfce_skin_scale_percent=175))
    rows=[{'id':1,'name':'Firefox — NovaBar','icon':'firefox'},{'id':2,'name':'Dossier personnel','icon':'folder'}]
    demo={'network':{'kind':'wifi','name':'Wi-Fi · Démonstration','device':'wlan0'},'volume':64,'muted':False,'bluetooth':True,'battery':{'percent':82,'plugged':False},'vpn':False}
    dock.desktop_state=demo;dock.apply_status(demo)
    with patch.object(dock.backend,'snapshot',return_value=(rows,1)):
        for width in (1280,1920):
            dock.full_rect=QRect(0,0,width,88);dock.setGeometry(dock.full_rect)
            app.processEvents();dock.refresh();app.processEvents();dock.refresh();app.processEvents();dock.clock.setText('12:34')
            dock.grab().save(str(out/f'novabar-v0611-cockpit-{width}.png'))
    entries=[Application('/tmp/f1','Firefox','firefox','internet'),Application('/tmp/f2','Fichiers','folder','system'),Application('/tmp/f3','Terminal','utilities-terminal','system'),Application('/tmp/f4','Éditeur de texte','accessories-text-editor','accessories'),Application('/tmp/f5','Calculatrice','accessories-calculator','accessories'),Application('/tmp/f6','Paramètres','preferences-system','system'),Application('/tmp/f7','Lecteur multimédia','multimedia-video-player','media'),Application('/tmp/f8','Dessin','applications-graphics','graphics')]
    launch=ApplicationLauncher('blue-neon',favorites=['/tmp/f1','/tmp/f3'],entries=entries);launch.show();app.processEvents();launch.grab().save(str(out/'novabar-v0611-nexus.png'));launch.close();dock.close()
