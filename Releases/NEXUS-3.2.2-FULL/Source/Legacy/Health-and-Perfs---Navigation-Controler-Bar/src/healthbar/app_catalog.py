"""Freedesktop application catalog, categories and a searchable large-icon launcher."""
import configparser
import os
import shutil
from dataclasses import dataclass, replace
from pathlib import Path
from PySide6.QtCore import Qt,QSize,Signal,QTimer
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QLabel,QLineEdit,QListWidget,QListWidgetItem,QPushButton,QAbstractItemView,QApplication,QMenu)
from .cockpit_style import CockpitFrame,app_icon,symbol_icon
from .edge_docks import launch_item
from .xfce_panel_skin import PALETTES
from .redblack_shell import active as redblack_active, control_stylesheet

CATEGORIES=[('all','Toutes les apps','apps',set()),('favorites','Favoris','apps',set()),
 ('internet','Internet','browser',{'Network','WebBrowser','Email','InstantMessaging'}),
 ('office','Bureautique','document',{'Office'}),('media','Multimédia','volume',{'AudioVideo','Audio','Video'}),
 ('graphics','Graphisme','application',{'Graphics'}),('games','Jeux','apps',{'Game'}),
 ('development','Développement','terminal',{'Development'}),('system','Système','settings',{'System','Settings'}),
 ('accessories','Accessoires','folder',{'Utility','Education','Science'})]

@dataclass(frozen=True)
class Application:
    path:str
    name:str
    icon:str
    category:str
    keywords:str=''


def application_roots():
    data=os.environ.get('XDG_DATA_HOME',str(Path.home()/'.local/share'))
    dirs=os.environ.get('XDG_DATA_DIRS','/usr/local/share:/usr/share').split(os.pathsep)
    return list(dict.fromkeys([str(Path(data)/'applications'),*[str(Path(p)/'applications') for p in dirs if p],
            str(Path.home()/'.local/share/flatpak/exports/share/applications'),'/var/lib/flatpak/exports/share/applications']))


def catalog(roots=None):
    result=[];seen=set();desktops=set(os.environ.get('XDG_CURRENT_DESKTOP','XFCE').split(':'))
    for base in roots or application_roots():
        root=Path(base)
        for path in sorted(root.rglob('*.desktop')):
            desktop_id=str(path.relative_to(root)).replace(os.sep,'-')
            if desktop_id in seen:continue
            seen.add(desktop_id)  # Hidden user entries intentionally suppress system duplicates.
            try:
                parser=configparser.ConfigParser(interpolation=None,strict=False);parser.read(path,encoding='utf-8');e=parser['Desktop Entry']
                if e.get('Type')!='Application' or e.getboolean('Hidden',False) or e.getboolean('NoDisplay',False):continue
                if not e.get('Exec') and not e.getboolean('DBusActivatable',False):continue
                only=set(filter(None,e.get('OnlyShowIn','').split(';')));exclude=set(filter(None,e.get('NotShowIn','').split(';')))
                if (only and not only.intersection(desktops)) or exclude.intersection(desktops):continue
                if e.get('TryExec') and not shutil.which(e['TryExec']):continue
                cats=set(e.get('Categories','').split(';'))
                category=next((key for key,_label,_icon,match in CATEGORIES[2:] if cats.intersection(match)),'accessories')
                result.append(Application(str(path),e.get('Name[fr]',e.get('Name',path.stem)),e.get('Icon',''),category,
                                          e.get('Keywords[fr]',e.get('Keywords',''))+' '+e.get('GenericName','')+' '+e.get('Comment','')))
            except (OSError,ValueError,configparser.Error,KeyError):continue
    return sorted(result,key=lambda a:a.name.casefold())


class ApplicationLauncher(QWidget):
    settings_requested=Signal();quit_requested=Signal()
    shortcut_requested=Signal(str,str)  # destination: bottom or sidebar
    shortcut_renamed=Signal(str,str)
    def __init__(self,theme,favorites=None,entries=None,parent=None):
        super().__init__(parent,Qt.WindowType.Popup|Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground);self.setWindowTitle('NEXUS · Applications')
        self.entries=list(entries) if entries is not None else catalog();self.favorites=set(favorites or []);self.category='all'
        if entries is None:
            from .edge_docks import launcher_metadata
            for path in list(self.favorites):
                info=launcher_metadata(Path(path))
                if not info:continue
                match=next((a for a in self.entries if (a.name,a.icon)==info),None)
                if match:self.favorites.add(match.path)
                elif Path(path).is_file():self.entries.extend(a for a in catalog([Path(path).parent]) if a.path==path)
        outer=QVBoxLayout(self);outer.setContentsMargins(0,0,0,0)
        self.frame=CockpitFrame(theme);outer.addWidget(self.frame)
        box=QVBoxLayout(self.frame);box.setContentsMargins(26,23,26,24);box.setSpacing(12)
        title=QHBoxLayout();label=QLabel('NEXUS  /  APPLICATIONS');label.setObjectName('launcherTitle');title.addWidget(label);title.addStretch()
        close=QPushButton('×');close.setFixedSize(28,28);close.clicked.connect(self.close);title.addWidget(close);box.addLayout(title)
        self.search=QLineEdit();self.search.setPlaceholderText('Rechercher une application…');self.search.setClearButtonEnabled(True);box.addWidget(self.search)
        content=QHBoxLayout();self.categories=QListWidget();self.categories.setFixedWidth(194);self.categories.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        for key,label,icon,_ in CATEGORIES:
            count=len(self.entries) if key=='all' else sum(a.path in self.favorites for a in self.entries) if key=='favorites' else sum(a.category==key for a in self.entries)
            item=QListWidgetItem(symbol_icon(icon),f'{label}  {count}');item.setData(Qt.ItemDataRole.UserRole,key);self.categories.addItem(item)
        self.categories.setCurrentRow(0);content.addWidget(self.categories)
        self.grid=QListWidget();self.grid.setViewMode(QListWidget.ViewMode.IconMode);self.grid.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.grid.setMovement(QListWidget.Movement.Static);self.grid.setIconSize(QSize(44,44));self.grid.setGridSize(QSize(116,92));self.grid.setSpacing(4)
        self.grid.setWordWrap(True);self.grid.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        content.addWidget(self.grid,1);box.addLayout(content,1)
        footer=QHBoxLayout();self.count=QLabel();footer.addWidget(self.count,1)
        # N3XV5 V2.4.7 START MENU
        import shutil as _n3xvs_shutil
        import subprocess as _n3xvs_subprocess
        from PySide6.QtWidgets import QMessageBox as _N3xvsMessageBox
        from .system_env import native_env as _n3xvs_native_env
        def _n3xvs_command(argv):
            if not _n3xvs_shutil.which(argv[0]):
                _N3xvsMessageBox.warning(self, 'N3XV5', 'Programme introuvable : '+argv[0])
                return
            try:
                _n3xvs_subprocess.Popen(argv, env=_n3xvs_native_env(),
                    stdin=_n3xvs_subprocess.DEVNULL, stdout=_n3xvs_subprocess.DEVNULL,
                    stderr=_n3xvs_subprocess.DEVNULL, start_new_session=True)
                self.close()
            except OSError as err:
                _N3xvsMessageBox.warning(self, 'N3XV5', str(err))
        def _n3xvs_power(restart):
            verb='redémarrer' if restart else 'éteindre'
            result=_N3xvsMessageBox.question(self, 'N3XV5 · Confirmation',
                'Voulez-vous vraiment '+verb+' cet ordinateur ?\n'
                'Enregistrez les documents ouverts avant de continuer.',
                _N3xvsMessageBox.StandardButton.Yes | _N3xvsMessageBox.StandardButton.No,
                _N3xvsMessageBox.StandardButton.No)
            if result==_N3xvsMessageBox.StandardButton.Yes:
                _n3xvs_command(['xfce4-session-logout', '--reboot' if restart else '--halt'])
        shutdown=QPushButton('Éteindre');shutdown.setIcon(symbol_icon('power'))
        shutdown.clicked.connect(lambda:_n3xvs_power(False));footer.addWidget(shutdown)
        restart=QPushButton('Redémarrer');restart.setIcon(symbol_icon('refresh'))
        restart.clicked.connect(lambda:_n3xvs_power(True));footer.addWidget(restart)
        execute=QPushButton('Exécuter');execute.setIcon(symbol_icon('terminal'))
        execute.clicked.connect(lambda:_n3xvs_command(['xfce4-appfinder','--collapsed']))
        footer.addWidget(execute);box.addLayout(footer)
        primary,secondary,_=PALETTES.get(theme,PALETTES['blue-neon'])
        self.setStyleSheet(control_stylesheet() if redblack_active(theme) else f'''QWidget {{font-family:Sans;color:#e1edf6;font-size:12px;}} QLabel#launcherTitle {{color:{primary};font-weight:bold;letter-spacing:2px;}}
            QLineEdit {{background:#081b2c;border:1px solid {secondary};border-radius:4px;padding:10px;}}
            QListWidget {{background:transparent;border:0;outline:0;}} QListWidget::item {{padding:5px;border:1px solid transparent;}}
            QListWidget::item:selected,QListWidget::item:hover {{background:#153c53;border:1px solid {primary};border-radius:5px;}}
            QPushButton {{background:#102d40;border:1px solid {secondary};border-radius:4px;padding:7px;}} QPushButton:hover {{border-color:{primary};}}
            QScrollBar:vertical {{background:#071724;width:7px;}} QScrollBar::handle:vertical {{background:{secondary};min-height:25px;}} QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical {{height:0;}}''')
        self.search.textChanged.connect(self.filter);self.categories.currentItemChanged.connect(self.select_category)
        self._queued_path=None
        self._click_timer=QTimer(self)
        self._click_timer.setSingleShot(True)
        self._click_timer.timeout.connect(self.launch_queued)
        self.grid.itemClicked.connect(self.queue_launch)
        self.grid.itemDoubleClicked.connect(self.show_item_context)
        self.grid.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.grid.customContextMenuRequested.connect(self.show_context_at)
        self.filter()
        self.resize(790,510)

    def select_category(self,current,previous):
        if current:self.category=current.data(Qt.ItemDataRole.UserRole);self.filter()

    def filter(self,*args):
        text=self.search.text().casefold().strip();self.grid.clear()
        for app in self.entries:
            if self.category=='favorites' and app.path not in self.favorites:continue
            if self.category not in ('all','favorites') and app.category!=self.category:continue
            if text and text not in (app.name+' '+app.keywords).casefold():continue
            item=QListWidgetItem(app_icon(app.icon),app.name);item.setToolTip(app.name);item.setData(Qt.ItemDataRole.UserRole,app.path);self.grid.addItem(item)
        self.count.setText(f'{self.grid.count()} application(s)')

    def launch(self,item):
        if launch_item(item.data(Qt.ItemDataRole.UserRole),'apps'):self.close()

    def queue_launch(self,item):
        self._queued_path=item.data(Qt.ItemDataRole.UserRole)
        delay=max(260,QApplication.styleHints().mouseDoubleClickInterval()+35)
        self._click_timer.start(delay)

    def launch_queued(self):
        path=self._queued_path
        self._queued_path=None
        if path and launch_item(path,"apps"):
            self.close()

    def show_context_at(self,pos):
        item=self.grid.itemAt(pos)
        if item:
            self.show_item_context(item)

    def show_item_context(self,item):
        """Right-click or double-click reveals exactly the selected app actions."""
        if item is None:
            return
        self._click_timer.stop()
        self._queued_path=None
        path=item.data(Qt.ItemDataRole.UserRole)
        if not path:
            return
        app=next((a for a in self.entries if a.path==path),None)
        if app is None:
            return
        menu=QMenu(self)
        primary,secondary,_=PALETTES.get(self.frame.theme,PALETTES["blue-neon"])
        menu.setStyleSheet(control_stylesheet() if redblack_active(self.frame.theme) else
            "QMenu {background:#06172A;color:#E9F6FF;border:1px solid "+primary+
            ";padding:6px;} QMenu::item {padding:8px 16px;}"
            "QMenu::item:selected {background:#144761;}")
        start=menu.addAction("▶ Ouvrir l'application")
        rename=menu.addAction("✎ Renommer le raccourci…")
        favorite=menu.addAction("★ Ajouter aux favoris (barre latérale)")
        pin=menu.addAction("◈ Ajouter à la barre de navigation")
        menu.addSeparator()
        remove=menu.addAction("Désinstaller… (APT / gestionnaire Mint)")
        result=menu.exec(self.grid.mapToGlobal(self.grid.visualItemRect(item).bottomLeft()))
        if result==start:
            if launch_item(path,"apps"):self.close()
        elif result==rename:
            from .desktop_actions import rename_launcher
            target=rename_launcher(path,self)
            if target:
                metadata=__import__("healthbar.edge_docks",fromlist=["launcher_metadata"]).launcher_metadata(Path(target))
                self.entries=[replace(a,path=target,name=metadata[0]) if a.path==path and metadata else a
                              for a in self.entries]
                if path in self.favorites:
                    self.favorites.remove(path)
                    self.favorites.add(target)
                self.shortcut_renamed.emit(path,target)
                self.filter()
        elif result==favorite:
            self.favorites.add(path)
            self.shortcut_requested.emit("sidebar",path)
            self.filter()
        elif result==pin:
            self.shortcut_requested.emit("bottom",path)
        elif result==remove:
            from .desktop_actions import request_uninstall
            request_uninstall(path,self)

    def show_above(self,button):
        screen=QApplication.screenAt(button.mapToGlobal(button.rect().center())) or QApplication.primaryScreen();bounds=screen.availableGeometry()
        self.resize(min(790,bounds.width()-16),min(510,bounds.height()-100))
        point=button.mapToGlobal(button.rect().topLeft());self.move(max(bounds.left()+4,min(point.x(),bounds.right()-self.width()-4)),max(bounds.top()+4,point.y()-self.height()-8))
        self.show();self.search.setFocus()

# NEXUS_V313_LAUNCHER_CONTEXT
from .n3xvs_v31_launcher import install as _nexus_v31_install_launcher
_nexus_v31_install_launcher(ApplicationLauncher)
