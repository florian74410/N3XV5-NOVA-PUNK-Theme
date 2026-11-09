"""Context actions for NEXUS AppLauncher. No system desktop files are modified."""
from __future__ import annotations
import configparser
import json
import os
import shutil
import subprocess
from dataclasses import replace
from pathlib import Path
from PySide6.QtCore import QObject,QEvent,Qt
from PySide6.QtWidgets import QMessageBox,QMenu,QListWidgetItem
from .cockpit_style import app_icon
from .edge_docks import launch_item

CATEGORIES={'internet','office','media','graphics','games','development','system','accessories'}


def _config_path():
    base=Path(os.environ.get('XDG_CONFIG_HOME',str(Path.home()/'.config')))
    return base/'nexus-v3'/'launcher_categories.json'


def load_categories():
    try:
        data=json.loads(_config_path().read_text('utf-8'))
        return {str(k):str(v) for k,v in data.items() if v in CATEGORIES}
    except (OSError,ValueError,TypeError):
        return {}


def save_categories(data):
    path=_config_path();path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix('.json.tmp')
    temp.write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n','utf-8')
    os.replace(temp,path)


def _info(owner,app):
    path=Path(app.path)
    lines=[f'Nom : {app.name}',f'Catégorie : {app.category}',f'Emplacement : {path}',
           f'Fichier : {"oui" if path.is_file() else "non"}',f'Dossier : {"oui" if path.is_dir() else "non"}']
    if path.suffix=='.desktop' and path.is_file():
        try:
            conf=configparser.ConfigParser(interpolation=None,strict=False);conf.read(path,'utf-8')
            if conf.has_section('Desktop Entry'):
                ent=conf['Desktop Entry']
                for key,title in [('Exec','Commande'),('Comment','Description'),('Categories','Catégories XDG'),('Terminal','Terminal')]:
                    if ent.get(key):lines.append(f'{title} : {ent[key]}')
        except (OSError,configparser.Error):pass
    QMessageBox.information(owner,'NEXUS · Informations','\n'.join(lines))


def install(launcher):
    if getattr(launcher,'_n3xvs_v31_launcher',False):return
    original_init=launcher.__init__
    original_filter=launcher.filter
    original_launch=launcher.launch

    class CategoryDropFilter(QObject):
        def eventFilter(self,obj,event):
            if event.type() in (QEvent.Type.DragEnter,QEvent.Type.DragMove):
                if event.source() is self.owner.grid and self.owner.grid.currentItem():
                    event.acceptProposedAction();return True
            if event.type()==QEvent.Type.Drop and event.source() is self.owner.grid:
                item=self.owner.categories.itemAt(event.position().toPoint())
                current=self.owner.grid.currentItem()
                if item and current:
                    category=item.data(Qt.ItemDataRole.UserRole)
                    path=current.data(Qt.ItemDataRole.UserRole)
                    self.owner._n3xvs_move_category(path,category)
                    event.acceptProposedAction()
                    return True
            return False

    def init(self,*args,**kwargs):
        original_init(self,*args,**kwargs)
        self._n3xvs_categories=load_categories()
        # Include user-picked files/folders from favorite paths when supplied.
        from .app_catalog import Application
        already={a.path for a in self.entries}
        for path in list(self.favorites):
            p=Path(path)
            if p.exists() and (p.is_dir() or p.suffix.lower()!='.desktop') and str(p) not in already:
                self.entries.append(Application(str(p),p.name,'folder' if p.is_dir() else 'document','accessories'))
                already.add(str(p))
        self.grid.setDragEnabled(True)
        self.grid.setDragDropMode(self.grid.DragDropMode.DragOnly)
        self.categories.setAcceptDrops(True)
        self.categories.viewport().setAcceptDrops(True)
        self._n3xvs_drop_filter=CategoryDropFilter(self)
        self._n3xvs_drop_filter.owner=self
        self.categories.viewport().installEventFilter(self._n3xvs_drop_filter)
        self.filter()

    def current_category(self,app):
        return self._n3xvs_categories.get(app.path,app.category)

    def move_category(self,path,category):
        if category=='favorites':
            self.favorites.add(path)
            self.shortcut_requested.emit('sidebar',path)
        elif category in CATEGORIES:
            self._n3xvs_categories[path]=category
            save_categories(self._n3xvs_categories)
        else:
            return
        self.filter()

    def filter_items(self,*args):
        # Mirrors original launcher filtering without editing .desktop files.
        phrase=self.search.text().casefold().strip();self.grid.clear()
        for app in self.entries:
            cat=self._n3xvs_categories.get(app.path,app.category) if hasattr(self,'_n3xvs_categories') else app.category
            if self.category=='favorites' and app.path not in self.favorites:continue
            if self.category not in ('all','favorites') and cat!=self.category:continue
            if phrase and phrase not in (app.name+' '+app.keywords).casefold():continue
            item=QListWidgetItem(app_icon(app.icon),app.name)
            item.setToolTip(app.name)
            item.setData(Qt.ItemDataRole.UserRole,app.path)
            self.grid.addItem(item)
        self.count.setText(f'{self.grid.count()} élément(s)')

    def context(self,item):
        if item is None:return
        self._click_timer.stop();self._queued_path=None
        path=item.data(Qt.ItemDataRole.UserRole)
        app=next((a for a in self.entries if a.path==path),None)
        if app is None:return
        is_file=Path(path).is_file() and not str(path).endswith('.desktop')
        is_dir=Path(path).is_dir()
        menu=QMenu(self)
        menu.setStyleSheet('QMenu{background:#06172A;color:#E9F6FF;border:1px solid #18CFFF;padding:6px}'
                           'QMenu::item{padding:7px 16px}QMenu::item:selected{background:#144761}')
        start=menu.addAction('▶ Ouvrir')
        menu.addSeparator()
        move=menu.addMenu('Déplacer vers…')
        categories=[('Favoris','favorites'),('Internet','internet'),('Bureautique','office'),
                    ('Multimédia','media'),('Graphisme','graphics'),('Jeux','games'),
                    ('Développement','development'),('Système','system'),('Accessoires','accessories')]
        for name,key in categories:
            move.addAction(name,lambda checked=False,k=key,p=path:self._n3xvs_move_category(p,k))
        pin=menu.addAction('◈ Épingler à la BottomBar')
        info=menu.addAction('ⓘ Informations')
        menu.addSeparator()
        rename=menu.addAction('✎ Renommer le raccourci…')
        if is_dir or is_file:
            delete=menu.addAction('Mettre à la corbeille…')
        else:
            delete=menu.addAction('Désinstaller… (gestionnaire Mint)')
        selected=menu.exec(self.grid.mapToGlobal(self.grid.visualItemRect(item).bottomLeft()))
        if selected==start:
            if is_file and shutil.which('xdg-open'):
                subprocess.Popen(['xdg-open',path],start_new_session=True)
                self.close()
            elif launch_item(path,'folders' if is_dir else 'apps'):
                self.close()
        elif selected==pin:
            self.shortcut_requested.emit('bottom',path)
        elif selected==info:
            _info(self,app)
        elif selected==rename:
            from .desktop_actions import rename_launcher
            target=rename_launcher(path,self)
            if target:
                from .edge_docks import launcher_metadata
                meta=launcher_metadata(Path(target))
                self.entries=[replace(a,path=target,name=meta[0]) if a.path==path and meta else a for a in self.entries]
                if path in self.favorites:
                    self.favorites.remove(path);self.favorites.add(target)
                if path in self._n3xvs_categories:
                    self._n3xvs_categories[target]=self._n3xvs_categories.pop(path)
                    save_categories(self._n3xvs_categories)
                self.shortcut_renamed.emit(path,target);self.filter()
        elif selected==delete:
            if is_dir or is_file:
                choice=QMessageBox.question(self,'Mettre à la corbeille',f'Déplacer vers la corbeille ?\n{path}',
                    QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,QMessageBox.StandardButton.No)
                if choice==QMessageBox.StandardButton.Yes:
                    p=Path(path).resolve()
                    if str(p).startswith(str(Path.home().resolve())+'/') and shutil.which('gio'):
                        subprocess.Popen(['gio','trash',str(p)],start_new_session=True)
                    else:
                        QMessageBox.warning(self,'NEXUS','Seuls les fichiers utilisateur peuvent être mis à la corbeille.')
            else:
                from .desktop_actions import request_uninstall
                request_uninstall(path,self)

    def launch_queued(self):
        path=self._queued_path;self._queued_path=None
        if path:
            p=Path(path)
            if p.is_file() and p.suffix.lower()!='.desktop' and shutil.which('xdg-open'):
                subprocess.Popen(['xdg-open',path],start_new_session=True)
                self.close()
            elif launch_item(path,'folders' if p.is_dir() else 'apps'):
                self.close()

    launcher.launch_queued=launch_queued
    launcher.__init__=init
    launcher.filter=filter_items
    launcher.show_item_context=context
    launcher._n3xvs_move_category=move_category
    launcher._n3xvs_v31_launcher=True
