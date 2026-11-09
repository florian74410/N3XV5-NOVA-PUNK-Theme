"""NovaBar edge docks: user folders and desktop application launchers.

One process, independent dock windows. No shell evaluation, no untrusted
.desktop parsing for arbitrary execution; GIO handles desktop launchers.
"""
from __future__ import annotations
import configparser
import os
import subprocess
import sys
import time
import math
from pathlib import Path

from PySide6.QtCore import QRect, Qt, QTimer, QUrl, QPoint, QPointF, QRectF, Signal, QFileInfo, QSize
from PySide6.QtGui import (QCursor, QDesktopServices, QIcon, QPainter, QPen,
                            QColor, QPolygonF, QPainterPath, QLinearGradient)
from PySide6.QtWidgets import (
    QApplication, QAbstractItemView, QFileIconProvider, QFrame,
    QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QPushButton,
    QMenu, QFileDialog, QVBoxLayout, QWidget, QInputDialog,
)

from .system_env import native_env
from .overlay import apply_priority, apply_all_workspaces
from .xfce_panel_skin import PALETTES
from .redblack_shell import active as redblack_active, paint_surface as redblack_surface


def xdg_folder(name: str) -> Path:
    """Discover localized XDG paths such as Téléchargements, without a shell."""
    if sys.platform.startswith("linux"):
        try:
            result = subprocess.run(["xdg-user-dir", name], text=True,
                                    stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, env=native_env(),
                                    timeout=1, check=False)
            candidate = Path(result.stdout.strip()).expanduser()
            if result.returncode == 0 and candidate.is_dir():
                return candidate
        except (OSError, subprocess.TimeoutExpired, ValueError):
            pass
    names = {
        "DOCUMENTS": ("Documents",),
        "DOWNLOAD": ("Téléchargements", "Downloads"),
        "PICTURES": ("Images", "Pictures"),
        "MUSIC": ("Musique", "Music"),
        "VIDEOS": ("Vidéos", "Videos"),
        "DESKTOP": ("Bureau", "Desktop"),
        "TEMPLATES": ("Modèles", "Templates"),
        "PUBLICSHARE": ("Public",),
    }
    for folder in names.get(name, (name.title(),)):
        candidate = Path.home() / folder
        if candidate.is_dir():
            return candidate
    return Path.home() / names.get(name, (name.title(),))[0]


def default_folders() -> list[str]:
    items = [str(Path.home())]
    for key in ("DOCUMENTS", "DOWNLOAD", "PICTURES", "MUSIC", "VIDEOS", "DESKTOP"):
        path = xdg_folder(key)
        if path.is_dir() and str(path) not in items:
            items.append(str(path))
    items.append("recent:///")
    return items


def desktop_apps() -> list[str]:
    """Discover user desktop launchers (Linux, Windows or macOS)."""
    directory = xdg_folder("DESKTOP")
    if not directory.is_dir():
        return []
    suffixes = (".lnk", ".url") if sys.platform == "win32" else (".app",) if sys.platform == "darwin" else (".desktop",)
    return [str(path) for path in sorted(directory.iterdir(), key=lambda p: p.name.casefold())
            if path.suffix.lower() in suffixes and (path.is_file() or path.is_dir() and sys.platform == "darwin")
            and (path.suffix.lower() != ".desktop" or launcher_metadata(path) is not None)]


def normalized_drop(paths, kind):
    """Only valid absolute folder paths or existing .desktop launchers."""
    accepted = []
    for path in paths:
        p = Path(path).expanduser()
        if kind == "folders" and p.is_dir():
            value = str(p.resolve())
        elif kind == "apps" and (p.is_dir() or
                p.is_file() and p.suffix.lower() in ((".lnk", ".url") if sys.platform == "win32" else (".desktop",))
                or sys.platform == "darwin" and p.is_dir() and p.suffix.lower() == ".app"):
            value = str(p.resolve())
        else:
            continue
        if value not in accepted:
            accepted.append(value)
    return accepted


def launcher_metadata(path: Path):
    display = path.stem
    icon_name = "application-x-executable"
    try:
        config = configparser.ConfigParser(interpolation=None, strict=False)
        config.read(path, encoding="utf-8")
        entry = config["Desktop Entry"]
        if entry.get("Type", "") != "Application" or entry.getboolean("Hidden", False) or entry.getboolean("NoDisplay", False):
            return None
        display = entry.get("Name[fr]", entry.get("Name", display))
        icon_name = entry.get("Icon", icon_name)
    except (OSError, KeyError, ValueError, configparser.Error):
        return None
    return display, icon_name


def launch_item(value: str, kind: str) -> bool:
    """Use native open handlers; desktop files only via GIO, never shell=True."""
    if kind == "folders":
        if value == "recent:///":
            if sys.platform == "darwin":
                return subprocess.Popen(["osascript", "-e", 'tell application "Finder" to open (home as alias)']).pid > 0
            if sys.platform == "win32":
                target = Path(os.getenv("APPDATA", str(Path.home()))) / "Microsoft/Windows/Recent"
                return QDesktopServices.openUrl(QUrl.fromLocalFile(str(target)))
            try:
                subprocess.Popen(["gio", "open", "recent:///"], stdout=subprocess.DEVNULL,
                                 stderr=subprocess.DEVNULL, start_new_session=True, env=native_env())
                return True
            except OSError:
                return QDesktopServices.openUrl(QUrl("recent:///"))
        directory = Path(value)
        return directory.is_dir() and QDesktopServices.openUrl(QUrl.fromLocalFile(str(directory)))
    target = Path(value)
    if sys.platform == "win32":
        if not target.is_file() or target.suffix.lower() not in (".lnk", ".url"):
            return False
        try:
            os.startfile(str(target))
            return True
        except OSError:
            return False
    if sys.platform == "darwin":
        if not target.is_dir() or target.suffix.lower() != ".app":
            return False
        try:
            subprocess.Popen(["open", str(target)], stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL, start_new_session=True, env=native_env())
            return True
        except OSError:
            return False
    if target.is_dir():
        return QDesktopServices.openUrl(QUrl.fromLocalFile(str(target)))
    if not target.is_file() or target.suffix.lower() != ".desktop" or launcher_metadata(target) is None:
        return False
    if sys.platform.startswith("linux"):
        try:
            subprocess.Popen(["gio", "launch", str(target)], stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL, start_new_session=True, env=native_env())
            return True
        except OSError:
            return False
    return QDesktopServices.openUrl(QUrl.fromLocalFile(str(target)))


class DockItems(QListWidget):
    changed = Signal(list)

    def __init__(self, kind, parent=None):
        super().__init__(parent)
        self.kind = kind
        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DragDrop)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setIconSize(QSize(24, 24) if kind=='apps' else QSize(30,30))
        self.setMouseTracking(True)
        self._v317_glitch_since=0.0
        self._v317_hover_row=-1
        self._v317_tick=QTimer(self)
        self._v317_tick.setInterval(48)
        self._v317_tick.timeout.connect(self.viewport().update)
        self.model().rowsMoved.connect(lambda *args: self.changed.emit(self.values()))

    def values(self):
        return [self.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.count())]

    def mouseMoveEvent(self,event):
        if self.kind=='apps' and self.window().isVisible():
            row=self.indexAt(event.position().toPoint()).row()
            if row!=self._v317_hover_row:
                self._v317_hover_row=row
                self._v317_glitch_since=time.monotonic()
            if row>=0 and not self._v317_tick.isActive():self._v317_tick.start()
            if row<0:self._v317_tick.stop()
        return super().mouseMoveEvent(event)

    def mousePressEvent(self,event):
        self._v317_glitch_since=time.monotonic()
        return super().mousePressEvent(event)

    def leaveEvent(self,event):
        self._v317_hover_row=-1
        self._v317_tick.stop()
        return super().leaveEvent(event)

    def paintEvent(self,event):
        super().paintEvent(event)
        if self.kind!='apps' or self._v317_hover_row<0:return
        item=self.item(self._v317_hover_row)
        if item is None:return
        rect=self.visualItemRect(item)
        if not rect.isValid() or not self.viewport().rect().intersects(rect):return
        p=QPainter(self.viewport())
        clip=QRect(rect.left()+3,rect.top()+2,32,max(1,rect.height()-4))
        p.setClipRect(clip)
        elapsed=time.monotonic()-self._v317_glitch_since
        tick=int(elapsed/.048)
        if elapsed<.38:
            for j,color in ((0,QColor(255,30,68,185)),(1,QColor(20,232,255,180))):
                y=rect.top()+3+(tick*7+j*13)%max(1,rect.height()-7)
                p.fillRect(QRect(rect.left()+5+(j*2),y,26,2),color)
        else:
            y=rect.top()+int((time.monotonic()*24)%max(1,rect.height()))
            p.fillRect(QRect(rect.left()+5,y,26,1),QColor(31,213,255,75))
        p.end()

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            found = normalized_drop([url.toLocalFile() for url in event.mimeData().urls()
                                     if url.isLocalFile()], self.kind)
            if found:
                values = self.values()
                insert = self.indexAt(event.position().toPoint()).row()
                if insert < 0: insert = len(values)
                for value in found:
                    if value in values:
                        existing = values.index(value)
                        values.pop(existing)
                        if existing < insert: insert -= 1
                    values.insert(insert, value)
                    insert += 1
                self.changed.emit(values)
                event.acceptProposedAction()
            else:
                event.ignore()
        else:
            super().dropEvent(event)


class DockGrip(QLabel):
    """Drag the dock title from one edge to the other; no native window dragging."""
    switch_requested = Signal()
    def __init__(self, side, parent=None):
        super().__init__("⠿  DÉPLACER  ↔", parent)
        self.side = side
        self.origin = None
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self.setToolTip("Glisser cette poignée vers l'autre moitié de l'écran pour déplacer le dock")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.origin = event.globalPosition().toPoint()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if self.origin is not None:
            final = event.globalPosition().toPoint()
            screen = QApplication.screenAt(final) or QApplication.primaryScreen()
            if (final - self.origin).manhattanLength() > 80 and screen:
                mid = screen.geometry().center().x()
                if (self.side == "left" and final.x() > mid or
                    self.side == "right" and final.x() < mid):
                    self.switch_requested.emit()
        self.origin = None
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        super().mouseReleaseEvent(event)


def dock_colors(theme):
    primary, secondary, _rgb = PALETTES.get(theme, PALETTES["blue-neon"])
    return primary, secondary


def dock_stylesheet(theme):
    if redblack_active(theme):
        return """
        QFrame#dockBody {background:transparent;border:0;}
        QFrame#dockBody QLabel {color:#FFDDE2;background:transparent;font-weight:700;}
        QFrame#dockBody QPushButton {color:#FFE7EB;background:#250912;
           border:1px solid #E02443;padding:5px;}
        QFrame#dockBody QPushButton:hover {background:#681529;border-color:#FF6374;}
        QFrame#dockBody QListWidget {background:#090508;color:#FFF0F2;
           border:1px solid #8D1730;outline:0;padding:4px;}
        QFrame#dockBody QListWidget::item {min-height:45px;margin:2px;
           padding:5px;border-bottom:1px solid #40101C;}
        QFrame#dockBody QListWidget::item:hover {background:#380D1C;}
        QFrame#dockBody QListWidget::item:selected {
           background:#6E1027;color:white;border-left:3px solid #FF3753;}
        """
    accent, secondary = dock_colors(theme)
    return f"""
        QFrame#dockBody {{ background: transparent; border: none; }}
        QFrame#dockBody QLabel {{ color: #d9edfa; font-size: 11px; background: transparent; }}
        QFrame#dockBody QPushButton {{
            background: rgba(8,29,48,185); color: #e7fbff;
            border: 1px solid {secondary}; border-radius: 3px; padding: 4px;
        }}
        QFrame#dockBody QPushButton:hover {{
            background: rgba(18,63,83,220); border-color: {accent};
        }}
        QFrame#dockBody QListWidget {{
            background: rgba(3,13,26,184); border: 1px solid {secondary};
            border-radius: 3px; color: #e7f5ff; outline: none;
            font-size: 11px; padding: 3px;
        }}
        QFrame#dockBody QListWidget::item {{
            min-height: 45px; border-bottom: 1px solid #16344d;
            margin: 2px; padding: 4px; border-radius: 2px;
        }}
        QFrame#dockBody QListWidget::item:hover {{
            background: rgba(34,95,111,190); border-left: 2px solid {accent};
        }}
        QFrame#dockBody QListWidget::item:selected {{
            background: rgba(16,77,104,210); border-left: 2px solid {accent};
        }}
    """


class PCBDockFrame(QFrame):
    """Cut-corner circuit board body, painted beneath real clickable widgets."""

    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.phase = 0.0
        self.setObjectName("dockBody")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAutoFillBackground(False)

    def paintEvent(self, event):
        if redblack_active(self.settings.theme):
            p=QPainter(self)
            p.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
            p.fillRect(self.rect(),Qt.GlobalColor.transparent)
            p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
            redblack_surface(p,QRectF(self.rect()).adjusted(2,2,-2,-2),
                             "dock",self.phase)
            p.end()
            return
        p = QPainter(self)
        # Explicit ARGB clear: the cut-off corners must reveal the desktop,
        # not uninitialised black pixels or a rectangular QFrame backing.
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
        p.fillRect(self.rect(), Qt.GlobalColor.transparent)
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        if w < 40 or h < 30:
            p.end()
            return
        accent_text, secondary_text = dock_colors(self.settings.theme)
        accent = QColor(accent_text)
        secondary = QColor(secondary_text)
        shell = QPainterPath()
        shell.addPolygon(QPolygonF([
            QPointF(2, 18), QPointF(18, 2), QPointF(w-23, 2),
            QPointF(w-2, 23), QPointF(w-2, h-25),
            QPointF(w-23, h-2), QPointF(17, h-2), QPointF(2, h-17)]))
        shell.closeSubpath()
        p.setPen(QPen(accent, 1.8))
        p.setBrush(QColor(4, 14, 29, 237))
        p.drawPath(shell)
        p.setClipPath(shell)
        p.setPen(QPen(secondary, 1))
        p.setBrush(Qt.BrushStyle.NoBrush)
        inner = shell.toFillPolygon()
        p.drawLine(QPointF(24, 10), QPointF(w-28, 10))
        p.drawLine(QPointF(19, h-10), QPointF(w-27, h-10))
        # Two tall PCI-style conductors run along the outside of the controls.
        for side in (9, w-10):
            for y in range(34, h-30, 42):
                shift = 11 if side < w/2 else -11
                p.setPen(QPen(secondary, 1))
                p.drawLine(QPointF(side, y), QPointF(side, y+12))
                p.drawLine(QPointF(side, y+12), QPointF(side+shift, y+21))
                p.setPen(QPen(accent, 1))
                p.drawEllipse(QPointF(side+shift, y+21), 1.7, 1.7)
        # Animated microprocessor blocks, live traces, and small LEDs.
        pulse_y = 36 + self.phase * max(1, h-72)
        for side in (9, w-10):
            p.setPen(QPen(QColor(accent.red(), accent.green(), accent.blue(), 65), 4))
            p.drawLine(QPointF(side, max(15,pulse_y-32)), QPointF(side, pulse_y))
            p.setPen(QPen(accent, 2.1))
            p.drawEllipse(QPointF(side, pulse_y), 2.6, 2.6)
        for x in range(39, w-28, 33):
            p.setPen(QPen(secondary, .8))
            p.drawLine(QPointF(x, 13), QPointF(x+9, 13))
            p.drawLine(QPointF(x+9, 13), QPointF(x+13, 18))
            p.drawLine(QPointF(x+13, 18), QPointF(x+21, 18))
            if int(self.phase*15+x/7)%3 == 0:
                p.setPen(QPen(accent, 1.5))
                p.drawEllipse(QPointF(x+21, 18), 1.5, 1.5)
        p.end()


class EdgeDock(QWidget):
    """Independent 3-second auto-hiding top-level panel, preserving the edge trigger."""
    moved_to_other_side = Signal(str)
    entries_changed = Signal(str, list)
    settings_requested = Signal()
    shortcut_requested = Signal(str,str)
    alias_changed = Signal(str,str)

    def __init__(self, side: str, kind: str, settings, parent=None):
        super().__init__(None)
        assert side in ("left", "right")
        assert kind in ("folders", "apps")
        self.side = side
        self.kind = kind
        self.settings = settings
        self.collapsed = True
        self.edge_width = 10
        self.panel_width = 174 if kind == 'apps' and side == 'left' else 250
        self.full_rect = None
        self.setWindowTitle(f"NovaBar • {kind} • {side}")
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint |
                            Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAcceptDrops(True)
        self.setMouseTracking(True)

        self.root = QVBoxLayout(self)
        self.root.setContentsMargins(0, 0, 0, 0)
        self.root.setSpacing(0)
        self.content = PCBDockFrame(settings)
        self.content.setStyleSheet(dock_stylesheet(settings.theme) +
            ("QFrame#dockBody QListWidget::item {min-height:26px;margin:0px;padding:1px 3px;}"
             if kind=='apps' and side=='left' else ""))
        layout = QVBoxLayout(self.content)
        layout.setContentsMargins(8 if kind=='apps' else 13, 9, 8 if kind=='apps' else 13, 8)
        layout.setSpacing(3 if kind=='apps' else 6)
        title = QHBoxLayout()
        title.setSpacing(4)
        self.grip = DockGrip(side)
        self.grip.switch_requested.connect(lambda: self.moved_to_other_side.emit(self.side))
        title.addWidget(self.grip, 1)
        self.swap = QPushButton("↔")
        self.swap.setToolTip("Échanger la position des docks")
        self.swap.setFixedWidth(28)
        self.swap.clicked.connect(lambda: self.moved_to_other_side.emit(self.side))
        title.addWidget(self.swap)
        layout.addLayout(title)
        self.heading = QLabel("DOSSIERS" if kind == "folders" else "APPLICATIONS")
        self.heading.setStyleSheet(f"color: {dock_colors(settings.theme)[0]}; "
                                   "font-size: 13px; font-weight: bold; letter-spacing: 1px;")
        layout.addWidget(self.heading)
        self.items = DockItems(kind)
        self._open_pending = None
        self._open_timer = QTimer(self)
        self._open_timer.setSingleShot(True)
        self._open_timer.timeout.connect(self.launch_pending)
        self.items.itemClicked.connect(self.queue_open_item)
        self.items.itemDoubleClicked.connect(
            lambda item:self.show_item_menu(self.items.visualItemRect(item).center()))
        self.items.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.items.customContextMenuRequested.connect(self.show_item_menu)
        self.items.changed.connect(lambda values: self.entries_changed.emit(self.kind, values))
        layout.addWidget(self.items, 1)
        tip = QLabel("Déposez des dossiers ici" if kind == "folders" else "Déposez vos raccourcis .desktop ici")
        tip.setStyleSheet("color: #91adbf; font-size: 10px;")
        tip.setWordWrap(True)
        layout.addWidget(tip)
        self.root.addWidget(self.content)
        self.hide_timer = QTimer(self)
        self.hide_timer.setSingleShot(True)
        self.hide_timer.setInterval(3000)
        self.hide_timer.timeout.connect(self.collapse)
        self.pointer_timer = QTimer(self)
        self._edge_entered_at = None
        self.pointer_timer.setInterval(40)
        self.pointer_timer.timeout.connect(self.check_pointer)
        self.pointer_timer.start()
        self.fx_timer = QTimer(self)
        self.fx_timer.setInterval(70)
        self.fx_timer.timeout.connect(self.animate_circuit)
        self.items_list = []
        self.set_items(self.default_items())
        self.place()

    def animate_circuit(self):
        if self.isVisible() and not self.collapsed:
            self.content.phase = (self.content.phase + .012) % 1
            self.content.update()
        else:
            self.fx_timer.stop()

    def apply_theme(self):
        """Repaint every neon surface when the global HUD palette changes."""
        self.content.settings = self.settings
        self.content.setStyleSheet(dock_stylesheet(self.settings.theme) +
            ("QFrame#dockBody QListWidget::item {min-height:26px;margin:0px;padding:1px 3px;}"
             if self.kind=='apps' and self.side=='left' else ""))
        self.heading.setStyleSheet(
            f"color: {dock_colors(self.settings.theme)[0]}; "
            "font-size: 13px; font-weight: bold; letter-spacing: 1px;")
        self.content.update()
        self.update()

    def default_items(self):
        saved = self.settings.dock_folder_paths if self.kind == "folders" else self.settings.dock_app_paths
        return list(saved) if saved is not None else (default_folders() if self.kind == "folders" else desktop_apps())

    def set_items(self, values):
        paths = []
        for value in values:
            if value == "recent:///" and self.kind == "folders":
                paths.append(value)
            elif value in normalized_drop([value], self.kind):
                paths.append(value)
        self.items.clear()
        provider = QFileIconProvider()
        for value in dict.fromkeys(paths):
            if value == "recent:///":
                label, ico = "Récents", QIcon.fromTheme("document-open-recent")
            elif self.kind == "folders":
                p = Path(value)
                label, ico = ("Dossier personnel" if p == Path.home() else p.name), provider.icon(QFileInfo(str(p)))
            else:
                p = Path(value)
                if p.suffix.lower() == ".desktop":
                    metadata = launcher_metadata(p)
                    if metadata is None:
                        continue
                    label, icon_name = metadata
                    ico = QIcon(icon_name) if icon_name.startswith("/") else QIcon.fromTheme(icon_name)
                    if ico.isNull(): ico = provider.icon(QFileInfo(str(p)))
                else:
                    label, ico = p.stem, provider.icon(QFileInfo(str(p)))
            label=self.settings.dock_aliases.get(value,label)
            item = QListWidgetItem(ico, label)
            item.setData(Qt.ItemDataRole.UserRole, value)
            item.setToolTip(value)
            self.items.addItem(item)

    def queue_open_item(self,item):
        self._open_pending=item.data(Qt.ItemDataRole.UserRole)
        delay=max(260,QApplication.styleHints().mouseDoubleClickInterval()+35)
        self._open_timer.start(delay)

    def launch_pending(self):
        path=self._open_pending
        self._open_pending=None
        if path:
            launch_item(path,self.kind)
            self.hide_timer.start(3000)

    def open_item(self,item):
        launch_item(item.data(Qt.ItemDataRole.UserRole),self.kind)
        self.hide_timer.start(3000)

    def show_item_menu(self,pos):
        # Both right-click and double-click open this menu. A pending single
        # click must not open the folder before a double click is recognised.
        self._open_timer.stop()
        self._open_pending=None
        menu=QMenu(self.items)
        menu.setStyleSheet(dock_stylesheet(self.settings.theme)+
            "QMenu {background:#071B2B;color:#E9F7FF;border:1px solid #14BDEB;}"
            "QMenu::item {padding:8px 16px;}"
            "QMenu::item:selected {background:#124969;}")
        selected=self.items.itemAt(pos)
        open_action=menu.addAction("Ouvrir") if selected else None
        rename_action=menu.addAction("✎ Renommer le raccourci…") if selected else None
        pin_action=menu.addAction("◈ Ajouter à la barre de navigation") if selected else None
        fav_action=menu.addAction("★ Ajouter aux favoris (Applications)") if selected else None
        add=menu.addAction("Ajouter un raccourci…")
        remove=menu.addAction("Retirer ce raccourci") if selected else None
        action=menu.exec(self.items.mapToGlobal(pos))
        if selected is not None:
            path=selected.data(Qt.ItemDataRole.UserRole)
            if action==open_action:
                launch_item(path,self.kind)
                return
            if action==pin_action:
                self.shortcut_requested.emit("bottom",path)
                return
            if action==fav_action:
                self.shortcut_requested.emit("sidebar",path)
                return
            if action==rename_action:
                alias,ok=QInputDialog.getText(self,"Renommer le raccourci",
                                             "Nom affiché (le dossier original reste intact) :",
                                             text=selected.text())
                if ok:
                    alias=alias.strip()
                    if 1<=len(alias)<=80 and all(ord(c)>=32 for c in alias):
                        self.alias_changed.emit(path,alias)
                return
        if action==add:
            if self.kind=="folders":
                chosen=QFileDialog.getExistingDirectory(self,"Ajouter un dossier",str(Path.home()))
            else:
                filters="Raccourcis (*.desktop)" if sys.platform.startswith("linux") else (
                    "Raccourcis (*.lnk *.url)" if sys.platform=="win32" else "Applications (*.app)")
                chosen,_=QFileDialog.getOpenFileName(self,"Ajouter une application",
                                                      str(xdg_folder("DESKTOP")),filters)
            if chosen:
                self.entries_changed.emit(self.kind,self.items.values()+[chosen])
        elif remove is not None and action==remove:
            values=self.items.values()
            values.remove(selected.data(Qt.ItemDataRole.UserRole))
            self.entries_changed.emit(self.kind,values)

    def place(self):
        screens = QApplication.screens()
        if not screens: return
        screen = screens[min(self.settings.screen, len(screens)-1)]
        bounds = screen.geometry()
        # Sidebars stay below a top HUD and above a bottom HUD when enabled.
        top = bounds.top() + (self.settings.thickness if self.settings.hud_enabled and self.settings.position == "top" else 0)
        bottom = bounds.bottom() - (self.settings.thickness if self.settings.hud_enabled and self.settings.position == "bottom" else 0)
        if getattr(self.settings, "bottom_dock_enabled", False):
            from .bottom_dock import bottom_height
            bottom -= bottom_height(self.settings)
        height = max(120, bottom-top+1)
        x = bounds.left() if self.side == "left" else bounds.right()-self.panel_width+1
        self.full_rect = (x, top, self.panel_width, height)
        self.collapse()
        if self.isVisible():
            from .overlay import schedule_all_workspaces
            schedule_all_workspaces(self)

    def expand(self):
        if not self.collapsed or not self.full_rect: return
        self.collapsed = False
        self.hide_timer.stop()
        # Release the edge-only width constraint before showing the content.
        self.setMinimumWidth(0)
        self.setMaximumWidth(16777215)
        self.setGeometry(*self.full_rect)
        self.content.show()
        self.show()
        self.fx_timer.start()
        self.update()

    def collapse(self):
        if not self.full_rect: return
        self.collapsed = True
        self._edge_entered_at = None
        self.hide_timer.stop()
        x, y, width, height = self.full_rect
        self.content.hide()
        self.fx_timer.stop()
        # QWidget layout hints can otherwise keep a 170+ px invisible dock
        # even after the entire body has been hidden.
        self.setFixedWidth(self.edge_width)
        self.setGeometry(x if self.side == "left" else x+width-self.edge_width, y, self.edge_width, height)
        self.hide()
        self.update()

    def edge_trigger_rect(self):
        if not self.full_rect:
            return QRect()
        x, y, width, height = self.full_rect
        return QRect(x if self.side == "left" else x+width-10, y, 10, height)

    def check_pointer(self):
        if not self.full_rect:
            return
        if QApplication.activePopupWidget() is not None:
            self.hide_timer.stop()
            return
        inside = (self.edge_trigger_rect() if self.collapsed else self.geometry()).contains(QCursor.pos())
        if self.collapsed:
            if inside:
                if self._edge_entered_at is None:
                    self._edge_entered_at = time.monotonic()
                elif time.monotonic() - self._edge_entered_at >= 1.0:
                    self._edge_entered_at = None
                    self.expand()
            else:
                self._edge_entered_at = None
        elif inside:
            self.hide_timer.stop()
        elif not self.hide_timer.isActive():
            self.hide_timer.start(3000)

    def enterEvent(self, event):
        if not self.collapsed: self.hide_timer.stop()
        super().enterEvent(event)

    def leaveEvent(self, event):
        if not self.collapsed: self.hide_timer.start(3000)
        super().leaveEvent(event)

    def paintEvent(self, event):
        # A collapsed dock is hidden. No painted grip and no input-catching strip.
        pass

    def showEvent(self, event):
        super().showEvent(event)
        apply_priority(self, self.settings.always_on_top)
        from .overlay import schedule_all_workspaces
        schedule_all_workspaces(self)

    def closeEvent(self, event):
        self.hide_timer.stop()
        self.pointer_timer.stop()
        self.fx_timer.stop()
        super().closeEvent(event)
