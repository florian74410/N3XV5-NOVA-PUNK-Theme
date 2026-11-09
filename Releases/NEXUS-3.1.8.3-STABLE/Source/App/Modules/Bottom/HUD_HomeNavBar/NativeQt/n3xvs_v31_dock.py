"""V3.1 dock group by verified X11 WM_CLASS (not by a window's title)."""
from __future__ import annotations
import re
from collections import OrderedDict
from PySide6.QtCore import QPoint
from PySide6.QtWidgets import QToolButton


def _classes(ids):
    result = {}
    try:
        from Xlib import display
        d = display.Display()
        try:
            for xid in ids:
                try:
                    value = d.create_resource_object('window', int(xid)).get_wm_class()
                    if value:
                        result[xid] = '|'.join(str(x).strip().lower() for x in value if x)
                except Exception:
                    continue
        finally:
            d.close()
    except Exception:
        pass
    return result


def install(bottom_dock):
    klass = bottom_dock.BottomDock
    if getattr(klass, '_n3xvs_v31_grouping', False):
        return

    def group_rows(self, rows, active):
        classes = _classes([r['id'] for r in rows])
        groups = OrderedDict()
        for row in rows:
            # Unknown WM_CLASS: do not group unrelated windows by accident.
            key = classes.get(row['id']) or ('window:' + str(row['id']))
            groups.setdefault(key, []).append(row)
        result=[]
        for entries in groups.values():
            current = next((r for r in entries if r['id'] == active), entries[0])
            new_row = dict(current)
            new_row['_n3xvs_group_members'] = list(entries)
            if len(entries)>1:
                # Identify application by WM_CLASS; name from representative window.
                app_name=(classes.get(current['id']) or '').split('|')[-1] or new_row['name']
                app_name=re.sub(r'[-_.]+',' ',app_name).strip().title()
                new_row['name'] = f'{app_name}  ({len(entries)})'
            result.append(new_row)
        return result

    def activate_group(self, row):
        members = row.get('_n3xvs_group_members') or [row]
        if len(members)==1:
            xid=members[0]['id']
            return self.backend.action(xid,minimize=xid==self._active)
        menu=self.themed_menu()
        menu.setTitle('Fenêtres de cette application')
        for entry in members:
            title=str(entry.get('name') or 'Fenêtre')
            action=menu.addAction(('● ' if entry['id']==self._active else '   ')+title)
            action.triggered.connect(lambda checked=False,x=entry['id']:self.backend.action(x))
        menu.addSeparator()
        menu.addAction('Tout réduire', lambda:[self.backend.action(e['id'],minimize=True) for e in members])
        # Parent to the dock and show at cursor, preserving task-button click behavior.
        from PySide6.QtGui import QCursor
        menu.exec(QCursor.pos())

    def group_task_menu(self, button, row):
        members=row.get('_n3xvs_group_members') or [row]
        if len(members)==1:
            return original_menu(self,button,row)
        menu=self.themed_menu()
        for member in members:
            sub=menu.addAction('◈  '+str(member.get('name') or 'Fenêtre'))
            sub.triggered.connect(lambda checked=False,r=member:original_menu(self,button,r))
        menu.addSeparator()
        menu.addAction('Afficher les fenêtres', lambda:self._n3xvs_activate_group(row))
        menu.exec(button.mapToGlobal(button.rect().topLeft()))

    original_menu=klass.task_menu
    klass._n3xvs_group_rows=group_rows
    klass._n3xvs_activate_group=activate_group
    klass.task_menu=group_task_menu
    klass._n3xvs_v31_grouping=True
