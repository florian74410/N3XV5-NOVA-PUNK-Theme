"""Native transparent PCB-style HUD with nonblocking read-only sensor polling."""
import argparse
import os
import sys
import time
import subprocess
import shutil
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from PySide6.QtCore import Qt, QTimer, QRect, QPropertyAnimation, QEasingCurve, QLockFile
from PySide6.QtGui import (QColor, QCursor, QDesktopServices, QIcon, QPainter, QPen,
                          QPixmap, QPainterPath)
from PySide6.QtCore import QPointF, QRectF, QUrl
from PySide6.QtWidgets import (QApplication, QWidget, QHBoxLayout, QVBoxLayout,
    QPushButton, QMenu, QSystemTrayIcon, QDialog, QMessageBox)
from .config import Settings, data_dir
from .dialogs import SettingsDialog, PluginsDialog, STYLE
from .plugins import PluginRegistry
from .hud import HudCanvas
from .holo import CpuHoloPanel
from .shared_telemetry import SharedTelemetry
from .help_links import WIKI_URL
from .system_env import native_env
from .edge_docks import EdgeDock
from .app_icon import novabar_icon
from .x11_workarea import reserve_edge


from .ui_kit import QColor

def button_icon(kind):
    pix = QPixmap(40, 40)
    pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(QPen(QColor("#F25067"), 2))
    if kind == "terminal":
        p.drawLine(10, 11, 18, 19)
        p.drawLine(18, 19, 10, 27)
        p.drawLine(21, 28, 32, 28)
    elif kind == "folder":
        path = QPainterPath(QPointF(6, 31))
        for x, y in [(6, 10), (17, 10), (21, 14), (34, 14), (31, 31), (6, 31)]:
            path.lineTo(x, y)
        p.drawPath(path)
    elif kind == "grid":
        for x in (8, 23):
            for y in (8, 23):
                p.drawRoundedRect(QRectF(x, y, 10, 10), 1, 1)
    elif kind == "settings":
        p.drawEllipse(11, 11, 18, 18)
        p.drawEllipse(16, 16, 8, 8)
        for i in range(8):
            p.save()
            p.translate(20, 20)
            p.rotate(i*45)
            p.drawRect(QRectF(-2, -15, 4, 6))
            p.restore()
    elif kind == "wiki":
        p.drawRoundedRect(QRectF(8, 6, 24, 29), 4, 4)
        p.drawArc(QRectF(15, 9, 13, 14), 5*16, 265*16)
        p.drawPoint(21, 28)
    elif kind == "quit":
        p.setPen(QPen(QColor("#ff8197"),3))
        p.drawLine(11,11,29,29)
        p.drawLine(29,11,11,29)
    elif kind == "expand":
        p.drawLine(20, 12, 20, 29)
        p.drawLine(12, 20, 20, 12)
        p.drawLine(20, 12, 28, 20)
    else:
        p.drawEllipse(9, 6, 23, 23)
        p.drawLine(10, 28, 5, 35)
        p.drawLine(16, 30, 11, 36)
        p.drawEllipse(18, 12, 7, 7)
    p.end()
    return QIcon(pix)


class NeonButton(QPushButton):
    """Paint the background ourselves, avoiding opaque native Windows QPushButton fills."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.panel_opacity = 88
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground,True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground,True)
        self.setAutoFillBackground(False)
        self.setStyleSheet("background:transparent;border:0;")

    def paintEvent(self, event):
        from .redblack_shell import active as redblack_active, paint_button as draw_redblack_button
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        if redblack_active():
            draw_redblack_button(p,self)
        else:
            background=QColor("#061020")
            background.setAlpha(round(255*self.panel_opacity/100))
            edge=QColor("#33dfff" if self.underMouse() else "#068cff")
            panel=QRectF(self.rect()).adjusted(1.2,1.2,-1.2,-1.2)
            cut=min(8.0,panel.height()*.27,panel.width()*.25)
            path=QPainterPath()
            path.moveTo(panel.left()+cut,panel.top())
            for x,y in ((panel.right()-cut,panel.top()),
                        (panel.right(),panel.top()+cut),
                        (panel.right(),panel.bottom()-cut),
                        (panel.right()-cut,panel.bottom()),
                        (panel.left()+cut,panel.bottom()),
                        (panel.left(),panel.bottom()-cut),
                        (panel.left(),panel.top()+cut)):
                path.lineTo(x,y)
            path.closeSubpath()
            p.fillPath(path,background)
            p.setPen(QPen(edge,1.6));p.setBrush(Qt.BrushStyle.NoBrush);p.drawPath(path)
        icon=self.icon()
        if not icon.isNull():
            size=min(32,max(18,min(self.width(),self.height())-14))
            x=8 if self.text() else (self.width()-size)//2
            icon.paint(p,QRect(x,(self.height()-size)//2,size,size))
        if self.text():
            p.setPen(QColor("#FFE6EA" if redblack_active() else "#e7f3ff"))
            p.setFont(self.font())
            left=43 if not icon.isNull() else 4
            p.drawText(QRect(left,0,max(0,self.width()-left-2),self.height()),
                       Qt.AlignmentFlag.AlignVCenter,self.text())
        p.end()

class Bar(QWidget):
    def __init__(self, settings):
        super().__init__()
        from .ui_kit import set_theme
        set_theme(settings.theme)
        self.settings = settings
        from .bundled_plugins import seed_bundled_plugins
        if getattr(sys,"frozen",False): seed_bundled_plugins(settings)
        self.registry = PluginRegistry()
        from .cpu_mode_controller import CpuModeController
        self.cpu_controller = CpuModeController()
        self.retracted = False
        self._edge_armed = False
        self.expanded = False
        self.busy = False
        self.setWindowTitle("NovaBar • Hardware Health Controller")
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet(STYLE + """
            QPushButton#nav { border: 1px solid #008fff; border-radius: 9px;
                background: rgba(2,15,34,170); padding: 3px; }
            QPushButton#nav:hover { border: 2px solid #48eaff; background: #0b345a; }
            QMenu { background: #061427; color: #e2efff; border: 1px solid #009dff; padding: 6px; }
            QMenu::item { padding: 12px 22px; }
            QMenu::item:selected { background: #114fe3; border-radius: 5px; }
            QMenu::item:disabled { color: #6986a3; }
        """)
        self.root = QHBoxLayout(self)
        self.root.setContentsMargins(0, 0, 0, 0)
        self.root.setSpacing(8)
        self.canvas = HudCanvas(self.registry)
        self.canvas.set_telemetry({})  # No illustrative values before the first real sample.
        self.canvas.slot_order = (settings.slot_order or self.canvas.ORIGINAL).copy()
        self.canvas.hidden_modules = list(settings.hidden_modules)
        self.canvas.layout_changed.connect(self.save_layout)
        self.canvas.module_activated.connect(self.open_module_holo)
        self.root.addWidget(self.canvas, 1)
        self.actions = QWidget()
        self.action_layout = QVBoxLayout(self.actions)
        self.action_layout.setContentsMargins(6, 4, 4, 4)
        self.action_layout.setSpacing(0)
        self.buttons = QWidget()
        self.button_layout = QHBoxLayout(self.buttons)
        self.button_layout.setContentsMargins(0, 0, 0, 0)
        self.button_layout.setSpacing(5)
        self.turbo = self.make_button("turbo", "CPU Mode · contrôle matériel selon OS et permissions", self.turbo_menu)
        self.turbo.setText("CPU Mode")
        self.turbo.setIcon(QIcon())
        self.turbo.setFixedWidth(155)
        self.turbo.setObjectName("cpuModeButton")
        self.make_button("terminal", "Ouvrir un terminal système", self.open_terminal)
        self.make_button("grid", "Extensions • ajouter et mettre à jour", self.plugins)
        self.make_button("settings", "Préférences / installation", self.preferences)
        self.action_layout.addWidget(self.buttons)
        self.expand_button = NeonButton()
        self.expand_button.setObjectName("nav")
        self.expand_button.setIcon(button_icon("expand"))
        self.expand_button.setFixedSize(34, 29)
        self.expand_button.setToolTip("Minimiser manuellement la barre")
        self.expand_button.clicked.connect(lambda: self.retract(manual=True))
        self.button_layout.addWidget(self.expand_button)
        self.quit_button = self.make_button("quit", "Quitter NovaBar (Ctrl+Q)", self.quit_app)
        self.quit_button.setAccessibleName("Quitter NovaBar")
        self.quit_button.hide()  # Closing is via tray or Ctrl+Q, never an intrusive HUD X.
        from PySide6.QtGui import QShortcut, QKeySequence
        self.quit_shortcut = QShortcut(QKeySequence("Ctrl+Q"),self)
        self.quit_shortcut.activated.connect(self.quit_app)
        from .ui_kit import ChipLogo
        self.chip_logo = ChipLogo()
        self.action_layout.addWidget(self.chip_logo, 1)
        self.root.addWidget(self.actions)
        self.animation = QPropertyAnimation(self, b"geometry", self)
        self.animation.setDuration(260)
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.animation.finished.connect(self._finish_transition)
        self.hide_timer = QTimer(self)
        self.hide_timer.setSingleShot(True)
        self.hide_timer.timeout.connect(self.retract)
        self.edge_timer = QTimer(self)
        self.edge_timer.setInterval(50)
        self.edge_timer.timeout.connect(self.check_edge)
        self.edge_timer.start()
        # XFCE can reassign Qt.Tool windows to one desktop during virtual desktop switching.
        self.workspace_timer = QTimer(self)
        self.workspace_timer.setInterval(2500)
        self.workspace_timer.timeout.connect(self.keep_visible_everywhere)
        self.workspace_timer.start()
        self.xfce_skin_status = "Habillage non activé"
        self.tray = QSystemTrayIcon(novabar_icon(settings.theme), self)
        self.tray.setToolTip("NovaBar • CYBER NEXUS HUD")
        self.tray_menu = QMenu(self)
        self.tray.setContextMenu(self.tray_menu)
        self.tray.activated.connect(self.tray_activated)
        self.build_tray_menu()
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray.show()
        app = QApplication.instance()
        app.screenAdded.connect(lambda screen: self.apply_settings())
        app.screenRemoved.connect(lambda screen: self.apply_settings())
        for screen in app.screens():
            screen.geometryChanged.connect(lambda rect: self.apply_settings())
        self.apply_settings()
        self.holo = CpuHoloPanel(self)
        from .holo import SensorHoloPanel
        self.module_holos = {slot: SensorHoloPanel(slot, self) for slot in SensorHoloPanel.FIELDS}
        for panel in [self.holo,*self.module_holos.values()]:
            panel.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint,settings.always_on_top)
        self.sensors = SharedTelemetry()
        self.sensor_worker = ThreadPoolExecutor(max_workers=1, thread_name_prefix="novabar-sensors")
        self.sensor_future = None
        self.last_sensor_request = 0.0
        self.last_cpu_error = None
        self.sensor_timer = QTimer(self)
        self.sensor_timer.setInterval(250)
        self.sensor_timer.timeout.connect(self.poll_sensors)
        self.sensor_timer.start()
        from .hotkeys import HotkeyController
        self.hotkeys = HotkeyController(self)
        self.hotkeys.configure(self.settings.shortcuts)
        self.sidebars = {}
        self.sync_sidebars()
        self.xfce_skin_fx = None
        self.bottom_dock = None
        self._xfce_skin_was_active = False
        self.xfce_skin_status = "Non activé"
        self.sync_xfce_skin()

    def keep_visible_everywhere(self):
        from .overlay import maintain_all_workspaces
        maintain_all_workspaces(self)
        for dock in getattr(self, "sidebars", {}).values():
            maintain_all_workspaces(dock)
        bottom = getattr(self, "bottom_dock", None)
        if bottom is not None:
            maintain_all_workspaces(bottom)
        panel = getattr(self, "xfce_skin_fx", None)
        if panel is not None:
            maintain_all_workspaces(panel)

    def sync_sidebars(self):
        """Create/hide the independent edge launchers without spawning processes."""
        enabled = {"left": self.settings.dock_left_enabled,
                   "right": self.settings.dock_right_enabled}
        kinds = {"left": self.settings.dock_left_kind,
                 "right": self.settings.dock_right_kind}
        for side in ("left", "right"):
            existing = self.sidebars.get(side)
            if not enabled[side]:
                if existing is not None:
                    existing.close()
                    existing.deleteLater()
                    self.sidebars.pop(side, None)
                continue
            if existing is not None and existing.kind != kinds[side]:
                existing.close()
                existing.deleteLater()
                self.sidebars.pop(side, None)
                existing = None
            if existing is None:
                dock = EdgeDock(side, kinds[side], self.settings)
                dock.moved_to_other_side.connect(self.move_dock)
                dock.entries_changed.connect(self.save_dock_entries)
                dock.settings_requested.connect(self.preferences)
                dock.shortcut_requested.connect(self.add_dock_shortcut)
                dock.alias_changed.connect(self.save_dock_alias)
                self.sidebars[side] = dock
            else:
                existing.settings = self.settings
                existing.apply_theme()
                existing.set_items(existing.default_items())
                existing.place()

    def move_dock(self, from_side):
        """Dragging to the opposite edge switches, or relocates a lone dock."""
        if from_side not in ("left", "right"):
            return
        left, right = self.settings.dock_left_kind, self.settings.dock_right_kind
        self.settings.dock_left_kind, self.settings.dock_right_kind = right, left
        if not (self.settings.dock_left_enabled and self.settings.dock_right_enabled):
            self.settings.dock_left_enabled, self.settings.dock_right_enabled = (
                self.settings.dock_right_enabled, self.settings.dock_left_enabled)
        self.settings.save()
        self.sync_sidebars()

    def save_dock_entries(self, kind, values):
        from .edge_docks import normalized_drop
        if kind == "folders":
            clean = [x for x in values if x == "recent:///" or
                     x in normalized_drop([x], "folders")]
            self.settings.dock_folder_paths = list(dict.fromkeys(clean))[:128]
        elif kind == "apps":
            self.settings.dock_app_paths = list(dict.fromkeys(normalized_drop(values, "apps")))[:128]
        self.settings.save()
        for dock in self.sidebars.values():
            if dock.kind == kind:
                dock.set_items(dock.default_items())

    def save_dock_alias(self,path,name):
        if not isinstance(path,str) or not isinstance(name,str):
            return
        self.settings.dock_aliases[path]=name
        self.settings.save()
        for dock in self.sidebars.values():
            dock.set_items(dock.default_items())

    def add_dock_shortcut(self,destination,path):
        """Persist one explicit user-selected shortcut; never install anything."""
        from .edge_docks import normalized_drop
        from .bottom_dock import pinned_apps
        if destination not in ("bottom","sidebar","unpin") or not isinstance(path,str):
            return
        if destination=="unpin":
            paths=(self.settings.bottom_pinned_apps if self.settings.bottom_pinned_apps is not None
                   else pinned_apps(self.settings))
            self.settings.bottom_pinned_apps=[p for p in paths if p!=path]
        else:
            target=Path(path).expanduser()
            if target.is_dir():
                clean=normalized_drop([str(target)],"folders")
            else:
                clean=normalized_drop([str(target)],"apps")
            if not clean:
                QMessageBox.warning(self,"NovaBar / Raccourcis","Le raccourci sélectionné est inaccessible.")
                return
            value=clean[0]
            if destination=="bottom":
                paths=(list(self.settings.bottom_pinned_apps) if self.settings.bottom_pinned_apps is not None
                       else pinned_apps(self.settings))
                self.settings.bottom_pinned_apps=list(dict.fromkeys([*paths,value]))[:10]
            else:
                # Freeze inherited dock pins before editing independent sidebar
                # favourites: adding a right-side favourite must not pin bottom.
                if self.settings.bottom_pinned_apps is None:
                    self.settings.bottom_pinned_apps=pinned_apps(self.settings)
                paths=list(self.settings.dock_app_paths or [])
                self.settings.dock_app_paths=list(dict.fromkeys([*paths,value]))[:128]
        self.settings.save()
        if self.bottom_dock is not None:
            self.bottom_dock.apply_settings(self.settings)
        self.sync_sidebars()

    def rename_app_shortcut(self,old_path,new_path):
        """Replace references after writing a user-local .desktop override."""
        from .edge_docks import normalized_drop
        if new_path not in normalized_drop([new_path],"apps"):
            return
        changed=False
        for key in ("dock_app_paths","bottom_pinned_apps"):
            paths=getattr(self.settings,key)
            if paths is None or old_path not in paths:
                continue
            setattr(self.settings,key,list(dict.fromkeys(
                new_path if item==old_path else item for item in paths)))
            changed=True
        if old_path in self.settings.dock_aliases:
            self.settings.dock_aliases[new_path]=self.settings.dock_aliases.pop(old_path)
            changed=True
        if changed:
            self.settings.save()
            if self.bottom_dock is not None:
                self.bottom_dock.apply_settings(self.settings)
            self.sync_sidebars()

    def sync_xfce_skin(self):
        """Manage the native Xfce panel without taking ownership of its icons."""
        from .xfce_panel_skin import apply_skin, remove_skin, backup_path
        if self.settings.bottom_dock_enabled and sys.platform.startswith("linux"):
            if self._xfce_skin_was_active or backup_path().exists():
                ok, message = remove_skin()
                self._xfce_skin_was_active = not ok
            if self.xfce_skin_fx is not None:
                self.xfce_skin_fx.close();self.xfce_skin_fx.deleteLater();self.xfce_skin_fx=None
            if self.bottom_dock is None:
                from .bottom_dock import BottomDock
                self.bottom_dock=BottomDock(self.settings)
                self.bottom_dock.settings_requested.connect(self.preferences)
                self.bottom_dock.quit_requested.connect(self.quit_app)
                self.bottom_dock.shortcut_requested.connect(self.add_dock_shortcut)
                self.bottom_dock.shortcut_renamed.connect(self.rename_app_shortcut)
            else:self.bottom_dock.apply_settings(self.settings)
            self.xfce_skin_status="Barre inférieure NovaBar active · original XFCE masqué pendant la session"
            return
        if self.bottom_dock is not None:
            self.bottom_dock.close();self.bottom_dock.deleteLater();self.bottom_dock=None
        enabled = bool(self.settings.xfce_skin_enabled)
        if enabled:
            ok, message = apply_skin(self.settings.theme, self.settings.xfce_skin_delay_seconds,
                                     self.settings.xfce_skin_scale_percent)
            self.xfce_skin_status = message
            if ok:
                self._xfce_skin_was_active = True
                if self.xfce_skin_fx is None:
                    from .xfce_panel_effects import XFCEPanelCircuitEffects
                    self.xfce_skin_fx = XFCEPanelCircuitEffects(self.settings)
                self.xfce_skin_fx.settings = self.settings
                self.xfce_skin_fx.locate_native_panel()
            elif self.xfce_skin_fx is not None:
                self.xfce_skin_fx.hide()
        else:
            if self._xfce_skin_was_active or backup_path().exists():
                _ok, self.xfce_skin_status = remove_skin()
                self._xfce_skin_was_active = not _ok
            if self.xfce_skin_fx is not None:
                self.xfce_skin_fx.close()
                self.xfce_skin_fx.deleteLater()
                self.xfce_skin_fx = None

    def offer_xfce_cyber(self):
        """Ask once whether to skin the user's actual system panel after upgrade."""
        from .xfce_panel_skin import available
        if (self.settings.bottom_dock_enabled or not available() or self.settings.xfce_skin_enabled
                or self.settings.xfce_skin_offer_done):
            return
        response = QMessageBox.question(
            None, "CYBER NEXUS • Barre système",
            "Activer le nouvel habillage CYBER NEXUS de la barre système XFCE ?\\n\\n"
            "Les icônes, applications ouvertes, Wi-Fi et notifications restent natives. "
            "Le panneau original sera sauvegardé et restaurable depuis les préférences.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes)
        self.settings.xfce_skin_offer_done = True
        self.settings.xfce_skin_enabled = response == QMessageBox.StandardButton.Yes
        self.settings.save()
        self.sync_xfce_skin()
        self.build_tray_menu()
        if self.settings.xfce_skin_enabled and "actif" not in self.xfce_skin_status:
            QMessageBox.warning(None, "CYBER NEXUS", self.xfce_skin_status)

    def xfce_panel_diagnostics(self):
        """Explain why the fourth surface is not visible without altering XFCE."""
        from .xfce_panel_skin import available, bottom_panel_id, panel_setting
        from .xfce_panel_effects import panel_x11_bounds
        from PySide6.QtWidgets import QApplication
        if self.bottom_dock is not None:
            dock=self.bottom_dock
            result=(f"Barre CYBER NEXUS : active\nGéométrie : {dock.full_rect.width()} × {dock.full_rect.height()} px"
                    f"\nPanneaux XFCE masqués : {len(dock.native.rows)}\n"
                    "Le HUD inférieur fonctionne indépendamment de la détection du panneau XFCE.")
            QMessageBox.information(None,"CYBER NEXUS • Diagnostic panneau inférieur",result)
            return
        if not available():
            result = "La session XFCE/X11 ou ses commandes ne sont pas disponibles."
        else:
            number = bottom_panel_id()
            if number is None:
                result = ("Aucun panneau XFCE fixé au bord inférieur n'a été trouvé. "
                          "Ouvrez les préférences du panneau XFCE et vérifiez sa position.")
            else:
                screen = QApplication.screens()[min(self.settings.screen, len(QApplication.screens())-1)]
                rect = panel_x11_bounds(screen.geometry())
                state = panel_setting(number, "autohide-behavior")
                height = panel_setting(number, "size")
                result = (f"Panneau natif : panel-{number}\\n"
                          f"Masquage XFCE : {state or 'indisponible'}\\n"
                          f"Épaisseur native : {height or 'indisponible'} px\\n"
                          f"Détection X11 : {'visible' if rect is not None else 'masqué / introuvable'}\\n"
                          f"Habillage NovaBar : {'activé' if self.settings.xfce_skin_enabled else 'désactivé'}\\n"
                          f"État : {self.xfce_skin_status}")
        QMessageBox.information(None, "CYBER NEXUS • Diagnostic panneau inférieur", result)

    def xfce_panel_preferences(self):
        from .xfce_panel_skin import available
        if not available():
            QMessageBox.information(None, "XFCE", "Le panneau XFCE n'est pas disponible dans cette session.")
            return
        try:
            subprocess.Popen(["xfce4-panel", "--preferences"],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                             start_new_session=True, env=native_env())
        except OSError as error:
            QMessageBox.warning(None, "XFCE", str(error))

    def tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.setVisible(True)
            self.reveal()
        elif reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.build_tray_menu()
            self.tray_menu.popup(QCursor.pos())

    def quick_settings(self, **updates):
        from dataclasses import replace
        try:
            changed = replace(self.settings, **updates).validate()
            changed.save()
        except (ValueError, OSError) as error:
            QMessageBox.warning(None, "NovaBar", str(error))
            return
        self.settings.__dict__.update(changed.__dict__)
        from .ui_kit import set_theme
        set_theme(self.settings.theme)
        self.apply_settings()
        self.setVisible(self.settings.hud_enabled)
        self.build_tray_menu()
        if updates.get("theme")=="redblack-0822":
            self.show_redblack_toast("STYLE ACTIVÉ","NOVA REDBLACK 0.8.2.2 • Nouveau design prêt")

    def show_redblack_toast(self,title,message):
        """Small red NOVA notice, without touching host system notifications."""
        from .redblack_shell import active as redblack_active, NovaRedToast
        if not redblack_active():return
        old=getattr(self,"_redblack_toast",None)
        if old is not None:old.close()
        self._redblack_toast=NovaRedToast(title,message,self)
        screen=self.screen() or QApplication.primaryScreen()
        if screen:
            available=screen.availableGeometry()
            self._redblack_toast.move(available.right()-450,available.bottom()-155)
        self._redblack_toast.show()

    def tray_toggle(self, panel):
        field = {"hud": "hud_enabled", "left": "dock_left_enabled",
                 "right": "dock_right_enabled"}[panel]
        self.quick_settings(**{field: not getattr(self.settings, field)})

    def tray_dock_side(self, kind, target):
        current_side = ("left" if self.settings.dock_left_kind == kind else "right")
        if current_side != target:
            self.move_dock(current_side)
        self.build_tray_menu()

    def show_dock(self, kind):
        dock = next((d for d in self.sidebars.values() if d.kind == kind), None)
        if dock:
            dock.expand()
            dock.raise_()

    def build_tray_menu(self):
        menu = self.tray_menu
        menu.clear()
        menu.addAction("◈ Afficher le HUD", lambda: (self.setVisible(True), self.reveal()))
        menu.addAction("📁 Afficher les dossiers", lambda: self.show_dock("folders"))
        menu.addAction("▦ Afficher les applications", lambda: self.show_dock("apps"))
        menu.addSeparator()
        panels = menu.addMenu("◉ Barres actives")
        for name, key in (("HUD télémétrie", "hud"), ("Dock gauche", "left"),
                          ("Dock droit", "right")):
            setting = {"hud":"hud_enabled", "left":"dock_left_enabled", "right":"dock_right_enabled"}[key]
            action = panels.addAction(name)
            action.setCheckable(True)
            action.setChecked(getattr(self.settings, setting))
            action.triggered.connect(lambda checked=False, k=key: self.tray_toggle(k))
        themes = menu.addMenu("🎨 Thème couleur")
        from .ui_kit import THEMES
        for key, title in THEMES.items():
            act = themes.addAction(title)
            act.setCheckable(True)
            act.setChecked(self.settings.theme == key or
                           key == "blue-neon" and self.settings.theme == "cyber-futuriste")
            act.triggered.connect(lambda checked=False, k=key: self.quick_settings(theme=k))
        positions = menu.addMenu("◈ Positions")
        hud_positions = positions.addMenu("Barre télémétrie")
        for key, title in (("top", "Haut"), ("bottom", "Bas"),
                           ("left", "Gauche (verticale)"), ("right", "Droite (verticale)")):
            action = hud_positions.addAction(title)
            action.setCheckable(True)
            action.setChecked(self.settings.position == key)
            action.triggered.connect(lambda checked=False, k=key: self.quick_settings(position=k))
        for kind, title in (("folders", "Dossiers"), ("apps", "Applications")):
            dock_menu = positions.addMenu(title)
            for side, side_name in (("left", "À gauche"), ("right", "À droite")):
                action = dock_menu.addAction(side_name)
                action.setCheckable(True)
                action.setChecked((self.settings.dock_left_kind if side == "left"
                                   else self.settings.dock_right_kind) == kind)
                action.triggered.connect(lambda checked=False, k=kind, x=side:
                                         self.tray_dock_side(k, x))
        menu.addSeparator()
        from .xfce_panel_skin import available as xfce_available
        xfce = menu.addMenu("⚡ Barre système XFCE")
        lower = xfce.addAction("Barre inférieure CYBER NEXUS")
        lower.setCheckable(True);lower.setChecked(self.settings.bottom_dock_enabled)
        lower.triggered.connect(lambda checked:self.quick_settings(bottom_dock_enabled=bool(checked)))
        toggle = xfce.addAction("Habillage XFCE historique")
        toggle.setCheckable(True)
        toggle.setChecked(self.settings.xfce_skin_enabled)
        toggle.setEnabled(xfce_available() and not self.settings.bottom_dock_enabled)
        toggle.triggered.connect(
            lambda checked: self.quick_settings(xfce_skin_enabled=bool(checked)))
        xfce.addAction("Gérer les icônes et raccourcis…", self.xfce_panel_preferences).setEnabled(xfce_available())
        xfce.addAction("🔎 Diagnostiquer le panneau inférieur", self.xfce_panel_diagnostics)
        shortcuts = xfce.addMenu("Rétraction rapide")
        for seconds in (3, 5, 10, 15, 30, 60):
            action = shortcuts.addAction(f"{seconds} secondes")
            action.setCheckable(True)
            action.setChecked(self.settings.xfce_skin_delay_seconds == seconds)
            action.triggered.connect(lambda checked=False, n=seconds:
                                     self.quick_settings(xfce_skin_delay_seconds=n))
        thickness = xfce.addMenu("Épaisseur")
        for percent in (100, 125, 150, 175, 200):
            action = thickness.addAction(f"{percent} %")
            action.setCheckable(True)
            action.setChecked(self.settings.xfce_skin_scale_percent == percent)
            action.triggered.connect(lambda checked=False, n=percent:
                                     self.quick_settings(xfce_skin_scale_percent=n))
        note = xfce.addAction(
            f"Délai : {self.settings.xfce_skin_delay_seconds} s · "
            f"épaisseur : {self.settings.xfce_skin_scale_percent} %")
        note.setEnabled(False)
        status = xfce.addAction(f"État : {self.xfce_skin_status[:76]}")
        status.setEnabled(False)
        menu.addAction("⚙ Préférences…", self.preferences)
        menu.addAction("◈ Plugin Manager…", self.plugins)
        menu.addAction("📖 Wiki NovaBar", self.open_wiki)
        menu.addSeparator()
        menu.addAction("⏻ Quitter NovaBar", self.quit_app)
        self.tray.setIcon(novabar_icon(self.settings.theme))

    def sample_sensors(self):
        readings = self.sensors.sample()
        return readings, self.cpu_controller.sample(readings.get("cpu_temperature_c"))

    def poll_sensors(self):
        if self.sensor_future is not None and self.sensor_future.done():
            try:
                readings, cpu_state = self.sensor_future.result()
                self.turbo.setToolTip(cpu_state["message"])
                if cpu_state["error"] and self.cpu_controller.mode is not None and cpu_state["error"] != self.last_cpu_error:
                    self.last_cpu_error = cpu_state["error"]
                    QMessageBox.warning(self,"CPU Mode indisponible",cpu_state["error"])
                elif not cpu_state["error"]: self.last_cpu_error = None
                if cpu_state["enabled"] is not None and not cpu_state["error"]:
                    self._set_turbo_indicator(cpu_state["enabled"])
                self.canvas.set_telemetry(readings)
                for slot, panel in self.module_holos.items():
                    if panel.isVisible():
                        panel.set_telemetry(readings)
                    elif slot == 'network':
                        panel.record_sample(readings)
                if self.holo.isVisible():
                    self.holo.set_telemetry(readings)
            except (OSError, RuntimeError, ValueError):
                pass
            self.sensor_future = None
        now = time.monotonic()
        interval = min(self.settings.refresh_seconds, self.sensors.interval())
        if self.cpu_controller.mode == "auto":
            interval = min(interval, 1)
        if self.sensor_future is None and now - self.last_sensor_request >= interval:
            self.last_sensor_request = now
            self.sensor_future = self.sensor_worker.submit(self.sample_sensors)

    def quit_app(self):
        # Return the original desktop to XFCE when NovaBar exits normally.
        if getattr(self, "_xfce_skin_was_active", False):
            from .xfce_panel_skin import remove_skin
            ok, message = remove_skin()
            self.xfce_skin_status = message
            self._xfce_skin_was_active = not ok
        self.close()
        QApplication.instance().quit()

    def _reserve_workarea_clear(self):
        if getattr(self,"full_rect",QRect()).isValid():
            reserve_edge(self,self.settings.position,0,False)

    def closeEvent(self, event):
        self._reserve_workarea_clear()
        if getattr(self,"bottom_dock",None) is not None:
            self.bottom_dock.close()
        self.tray.hide()
        for dock in getattr(self, "sidebars", {}).values():
            dock.close()
        if getattr(self, "xfce_skin_fx", None) is not None:
            self.xfce_skin_fx.close()
        self.holo.close_panel()
        for panel in self.module_holos.values(): panel.close_panel()
        self.sensor_timer.stop()
        self.workspace_timer.stop()
        self.hotkeys.stop()
        self.sensor_worker.shutdown(wait=False, cancel_futures=True)
        super().closeEvent(event)

    def open_module_holo(self, slot):
        # The host supplies the CPU hologram; ZIP modules only declare capabilities.
        if not self.settings.holo_enabled: return
        if not self.sensors.prefs.get(slot, {}).get('holo_enabled', True): return
        for kind, other in self.module_holos.items():
            if kind != slot: other.close_panel()
        if slot != "cpu": self.holo.close_panel()
        if slot != "cpu":
            panel = self.module_holos.get(slot)
            if panel and any(item["enabled"] and item["slot"] == slot for item in self.registry.installed()):
                if panel.isVisible(): panel.close_panel()
                else:
                    screen = QApplication.screens()[min(self.settings.screen, len(QApplication.screens())-1)]
                    panel.set_telemetry(self.canvas.readings or {})
                    panel.show_at(self.canvas.module_global_rect(slot), screen.availableGeometry(), self.settings.position)
            return
        enabled = any(item["enabled"] and item["id"] == "cpu-manager-viewer" and
                      item.get("holo_view") == "cpu-core-matrix"
                      for item in self.registry.installed())
        if not enabled:
            # The core slot remains a read-only monitor until its Holo ZIP is installed.
            return
        if self.holo.isVisible():
            self.holo.close_panel()
            return
        app = QApplication.instance()
        screens = app.screens()
        screen = screens[min(self.settings.screen, len(screens)-1)]
        anchor = self.canvas.module_global_rect("cpu")
        self.holo.set_telemetry(self.canvas.readings or {})
        self.holo.show_at(anchor, screen.availableGeometry(), self.settings.position)

    def save_layout(self, order):
        self.settings.slot_order = order
        try:
            self.settings.save()
            folder = data_dir() / "App" / "Repports" / "NovaBar"
            folder.mkdir(parents=True, exist_ok=True)
            with (folder / "layout.log").open("a", encoding="utf-8") as log:
                log.write(f"{datetime.now().isoformat()} | {', '.join(order)}\n")
        except OSError as error:
            QMessageBox.warning(self, "Enregistrement", str(error))

    def make_button(self, kind, tooltip, callback):
        button = NeonButton()
        button.setObjectName("nav")
        button.setProperty("icon_kind", kind)
        button.setIcon(button_icon(kind))
        from PySide6.QtCore import QSize
        button.setIconSize(QSize(34, 34))
        button.setFixedSize(56, 58)
        button.setToolTip(tooltip)
        button.setAccessibleName(tooltip)
        button.clicked.connect(callback)
        self.button_layout.addWidget(button)
        return button

    def apply_settings(self):
        from .ui_kit import set_theme
        set_theme(self.settings.theme)
        from .ui_kit import stylesheet
        from .redblack_shell import active as redblack_active, control_stylesheet
        self.setStyleSheet(control_stylesheet() if redblack_active() else stylesheet(STYLE))
        if hasattr(self,"holo"):
            for panel in [self.holo,*getattr(self,"module_holos",{}).values()]:
                panel.apply_visual_theme()
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, self.settings.always_on_top)
        self.animation.stop()
        self.retracted = False
        self._edge_armed = False
        self.quit_button.setVisible(self.settings.position != "top")
        self.actions.show()
        self.root.setSpacing(8)
        screens = QApplication.screens()
        screen = screens[min(self.settings.screen, len(screens)-1)]
        g = screen.geometry()
        vertical = self.settings.position in ("right", "left")
        self.setMaximumWidth(150 if vertical else 16777215)
        self.setMaximumHeight(16777215 if vertical else 150)
        thickness = min(150, self.settings.thickness * (2 if self.expanded else 1),
                        g.width() if vertical else g.height())
        thickness = int(thickness)
        self.canvas.vertical = vertical
        self.canvas.module_opacity = self.settings.opacity
        self.canvas.hidden_modules = list(self.settings.hidden_modules)
        self.canvas.slot_order = (self.settings.slot_order or self.canvas.ORIGINAL).copy()
        self.canvas.update()
        for child in self.buttons.findChildren(NeonButton):
            kind = child.property("icon_kind")
            if kind and child is not self.turbo: child.setIcon(button_icon(kind))
            child.panel_opacity = self.settings.opacity
            child.update()
        self.expand_button.setIcon(button_icon("expand"))
        self.chip_logo.update()
        self.expand_button.panel_opacity = self.settings.opacity
        self.expand_button.update()
        alpha = round(255*self.settings.opacity/100)
        self.actions.setStyleSheet("background:transparent;border:0;" if redblack_active()
            else f"""QPushButton#nav {{ background: rgba(2,15,34,{alpha}); }}
            QPushButton#nav:hover {{ background: rgba(11,52,90,{alpha}); }}""")
        self.root.setDirection(QHBoxLayout.Direction.TopToBottom if vertical else QHBoxLayout.Direction.LeftToRight)
        self.actions.setFixedWidth(thickness-12 if vertical else min(400, max(290, g.width()//5)))
        if vertical:
            self.button_layout.setDirection(QHBoxLayout.Direction.TopToBottom)
            length = max(360, round(g.height()*self.settings.length_percent/100))
            button_height = min(40,max(28,(length-120)//10))
            total = self.button_layout.count()*button_height + (self.button_layout.count()-1)*5
            self.actions.setFixedHeight(total+8)
            self.buttons.setFixedHeight(total)
            for index in range(self.button_layout.count()):
                button=self.button_layout.itemAt(index).widget()
                button.setFixedSize(max(28,min(56,thickness-22)),button_height)
            self.turbo.setText("")
            shift = {"left": 0, "center": (g.height()-length)//2,
                     "right": g.height()-length}[self.settings.alignment]
            self.full_rect = QRect(g.left() if self.settings.position == "left" else g.right()-thickness+1, g.top()+shift, thickness, length)
        else:
            self.button_layout.setDirection(QHBoxLayout.Direction.LeftToRight)
            self.actions.setMinimumHeight(0)
            self.actions.setMaximumHeight(16777215)
            button_height = max(28,min(48,thickness-12))
            self.buttons.setFixedHeight(button_height)
            width = self.actions.width()
            turbo_width = 148 if width >= 350 else 90
            utility_width = 28
            count = self.button_layout.count() - 3  # turbo, expand, optional quit
            size = max(20,min(55,(width-10-30-turbo_width-2*utility_width)//count))
            self.turbo.setFixedSize(turbo_width,button_height)
            self.turbo.setText("NORMAL MODE")
            self._set_turbo_indicator(False,force=True)
            for index in range(1, 1+count):
                self.button_layout.itemAt(index).widget().setFixedSize(min(size,button_height),min(size,button_height))
            self.expand_button.setFixedSize(utility_width,utility_width)
            self.quit_button.setFixedSize(utility_width,utility_width)
            y = g.top() if self.settings.position == "top" else g.bottom()-thickness+1
            length = max(290, round(g.width()*self.settings.length_percent/100))
            shift = {"left": 0, "center": (g.width()-length)//2,
                     "right": g.width()-length}[self.settings.alignment]
            self.full_rect = QRect(g.left()+shift, y, length, thickness)
        self.action_layout.invalidate()
        self.action_layout.activate()
        self.root.invalidate()
        self.root.activate()
        self.setGeometry(self.full_rect)
        self._reserve_workarea()
        self.update()
        if hasattr(self, "sidebars"):
            self.sync_sidebars()
        if hasattr(self, "xfce_skin_fx"):
            self.sync_xfce_skin()
        if hasattr(self, "tray_menu"):
            self.build_tray_menu()
        self.arm_hide()

    def _reserve_workarea(self):
        if not getattr(self,"full_rect",QRect()).isValid():
            return
        if self.settings.position in ("top","bottom") and self.settings.hud_enabled:
            reserve_edge(self,self.settings.position,self.geometry().height(),self.settings.top_reserved)
        else:
            reserve_edge(self,self.settings.position,0,False)

    def showEvent(self, event):
        super().showEvent(event)
        QTimer.singleShot(0,self._reserve_workarea)
        from .overlay import apply_priority
        self.overlay_status = apply_priority(self, self.settings.always_on_top)
        from .overlay import schedule_all_workspaces
        schedule_all_workspaces(self)
        self.expand_button.setToolTip("Minimiser manuellement · " + self.overlay_status)

    def paintEvent(self, event):
        p = QPainter(self)
        # Clear every pixel outside the modules; no shared panel or outer rectangle.
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
        p.fillRect(self.rect(), Qt.GlobalColor.transparent)
        from .ui_kit import pcb
        from .redblack_shell import active as redblack_active
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
        if not redblack_active():
            pcb(p, self.rect())
        p.end()

    def arm_hide(self):
        self.hide_timer.stop()
        if (self.settings.retract_mode or ("auto" if self.settings.auto_hide else "manual")) == "auto" and not self.busy and not self.retracted:
            self.hide_timer.start(self.settings.hide_seconds*1000)

    def enterEvent(self, event):
        self.hide_timer.stop()
        # Never expand on enter: the 10-pixel continuous hover gate is sole trigger.
        if not self.retracted:
            self.arm_hide()
        super().enterEvent(event)

    def leaveEvent(self, event):
        if self.retracted:
            # Rearm only once the pointer really leaves the collapsed window.
            if not self.geometry().contains(QCursor.pos()):
                self._edge_armed = True
        else:
            self.arm_hide()
        super().leaveEvent(event)

    def retract(self, manual=False):
        if self.busy or (not manual and self.geometry().contains(QCursor.pos())) or QApplication.activePopupWidget():
            self.arm_hide()
            return
        if not manual and (self.settings.retract_mode or ("auto" if self.settings.auto_hide else "manual")) != "auto":
            return
        rect = QRect(self.full_rect)
        if self.settings.position in ("top", "bottom"):
            edge = min(32, max(26, round(rect.height() * .40)))
            if self.settings.position == "bottom":
                rect.setTop(rect.bottom()-edge+1)
            else:
                rect.setHeight(edge)
        else:
            # Narrow vertical stripe; never grow past the configured full width.
            edge = max(22, min(76, rect.width()-6))
            if self.settings.position == "right":
                rect.setLeft(rect.right()-edge+1)
            else:
                rect.setWidth(edge)
        for panel in (self.holo, *self.module_holos.values()):
            if panel.isVisible() and not panel.pinned:
                panel.close_panel()
        self.retracted = True
        self._edge_armed = False
        self._top_edge_entered_at = None
        self.actions.hide()
        self.root.setSpacing(0)
        self.canvas.update()
        self.animate(rect)

    def animate(self, rect):
        self.animation.stop()
        self.animation.setStartValue(self.geometry())
        self.animation.setEndValue(rect)
        self.animation.start()

    def _finish_transition(self):
        # Recompute the X11 workarea after each completed open/collapse animation.
        self._reserve_workarea()
        if not self.retracted:
            self.root.setSpacing(8)
            self.actions.show()
            self.canvas.update()

    def reveal(self):
        from .overlay import schedule_all_workspaces
        schedule_all_workspaces(self)
        if self.retracted:
            self.retracted = False
            self.canvas.update()
            self.animate(self.full_rect)
        self.show()
        self.arm_hide()

    def check_edge(self):
        if not self.retracted:
            self._top_edge_entered_at = None
            return
        bounds = self.full_rect
        pointer = QCursor.pos()
        if self.settings.position == 'top':
            edge = QRect(bounds.left(), bounds.top(), bounds.width(), self.settings.top_trigger_px)
        elif self.settings.position == 'bottom':
            edge = QRect(bounds.left(), bounds.bottom()-self.settings.top_trigger_px+1, bounds.width(), self.settings.top_trigger_px)
        else:
            edge = self.geometry()
        if not edge.contains(pointer):
            self._top_edge_entered_at = None
            self._edge_armed = True
        elif self._edge_armed:
            now = time.monotonic()
            if getattr(self, '_top_edge_entered_at', None) is None:
                self._top_edge_entered_at = now
            elif (now - self._top_edge_entered_at)*1000 >= self.settings.top_hover_ms:
                self._top_edge_entered_at = None
                self.reveal()

    def toggle_expand(self):
        self.expanded = not self.expanded
        self.apply_settings()

    def run_dialog(self, dialog):
        self.busy = True
        self.hide_timer.stop()
        try:
            return dialog.exec()
        finally:
            self.busy = False
            self.arm_hide()

    def preferences(self):
        if self.holo.isVisible() and not self.holo.pinned:
            self.holo.close_panel()
        if self.run_dialog(SettingsDialog(self.settings, QApplication.screens(),
                                          parent=self if self.isVisible() else None)) == QDialog.DialogCode.Accepted:
            self.sensors.reload_preferences()
            for slot, panel in self.module_holos.items():
                panel.detail_fields = set(self.sensors.prefs[slot]["details"])
                if panel.isVisible():
                    panel.set_telemetry(self.canvas.readings or {})
            self.last_sensor_request = 0.0
            self.apply_settings()
            self.setVisible(self.settings.hud_enabled)
            from .ui_kit import stylesheet
            for panel in [self.holo, *self.module_holos.values()]:
                panel.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint,self.settings.always_on_top)
                panel.apply_visual_theme()
                panel.update()
            self.hotkeys.configure(self.settings.shortcuts)
            self.tray.setIcon(novabar_icon(self.settings.theme))
            self.build_tray_menu()

    def plugins(self):
        self.run_dialog(PluginsDialog(self.registry, self))
        self.canvas.refresh_plugins()
        if self.holo.isVisible() and not any(item["enabled"] and
                item.get("holo_view") == "cpu-core-matrix"
                for item in self.registry.installed()):
            self.holo.close_panel()

    def open_wiki(self):
        if not QDesktopServices.openUrl(QUrl(WIKI_URL)):
            QMessageBox.warning(self, "Wiki NovaBar",
                "Impossible d\u0027ouvrir le navigateur.\nAccès direct :\n" + WIKI_URL)

    def open_folder(self):
        data_dir().mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(data_dir())))

    def open_terminal(self):
        """Open the user's terminal emulator, never a themed stub."""
        commands=(
            ["exo-open","--launch","TerminalEmulator"],
            ["xfce4-terminal"], ["x-terminal-emulator"], ["konsole"],
            ["gnome-terminal"], ["xterm"])
        cmd=next((c for c in commands if shutil.which(c[0])),None)
        if cmd is None:
            QMessageBox.warning(self,"NovaBar / Terminal",
                                "Aucun émulateur de terminal disponible sur le système.")
            return
        try:
            subprocess.Popen(cmd,env=native_env(),stdin=subprocess.DEVNULL,
                             stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
                             start_new_session=True)
        except OSError as exc:
            QMessageBox.warning(self,"NovaBar / Terminal",str(exc))

    def run_script(self, path):
        root = Path(self.settings.shell_dir).expanduser() if self.settings.shell_dir else (
            Path.home() / "Scripts" / "HardwareHealth")
        path = Path(path).resolve()
        if root.resolve() != path.parent or not path.is_file():
            QMessageBox.warning(self, "Script refusé", "Le script doit être directement dans le dossier autorisé.")
            return
        confirm = QMessageBox.question(self, "Exécuter le script local ?", 
            f"Fichier : {path.name}\n\nCe script s'exécutera avec les droits de votre compte.\nContinuer ?")
        if confirm != QMessageBox.StandardButton.Yes:
            return
        if path.suffix.lower() == ".py":
            args = [sys.executable, str(path)]
        elif os.name == "nt":
            if path.suffix.lower() == ".ps1":
                args = ["powershell", "-NoProfile", "-File", str(path)]
            else:
                args = ["cmd", "/c", str(path)]
        else:
            args = ["/bin/sh", str(path)]
        folder = data_dir() / "App" / "Repports" / "NovaBar"
        folder.mkdir(parents=True, exist_ok=True)
        log = folder / ("shell-" + datetime.now().strftime("%Y%m%d-%H%M%S") + ".log")
        try:
            with log.open("wb") as output:
                subprocess.Popen(args, cwd=path.parent, stdin=subprocess.DEVNULL,
                                 stdout=output, stderr=subprocess.STDOUT,
                                 start_new_session=(os.name != "nt"), env=native_env())
        except (OSError, ValueError) as error:
            QMessageBox.warning(self, "Exécution impossible", str(error))

    def _set_turbo_indicator(self,enabled,force=False):
        if not force and getattr(self,"_shown_turbo",None)==enabled:
            return
        self._shown_turbo=bool(enabled)
        accent="#FF5972" if enabled else "#36DFFF"
        self.turbo.setText("TURBO ON" if enabled else "NORMAL MODE")
        self.turbo.setStyleSheet(
            "QPushButton#cpuModeButton {color:"+accent+
            ";background:rgba(3,23,45,220);font-weight:800;"
            "border:1px solid "+accent+";border-radius:7px;}"
            "QPushButton#cpuModeButton:hover {background:rgba(25,64,86,235);}"
        )

    def turbo_menu(self):
        self.busy=True
        self.hide_timer.stop()
        menu=QMenu(self)
        menu.setTitle("CPU / privilèges administrateur")
        if not self.settings.turbo_auth_enabled:
            disabled=menu.addAction("Turbo désactivé dans les Paramètres")
            disabled.setEnabled(False)
        else:
            menu.addAction("◈ NORMAL MODE",lambda:self.select_cpu_mode("off"))
            menu.addAction("⚡ TURBO ON",lambda:self.select_cpu_mode("on"))
        menu.addSeparator()
        status=menu.addAction(self.cpu_controller.status)
        status.setEnabled(False)
        try:
            menu.exec(self.turbo.mapToGlobal(self.turbo.rect().bottomLeft()))
        finally:
            self.busy=False
            self.arm_hide()

    def select_cpu_mode(self,mode):
        if mode not in ("on","off"):
            QMessageBox.warning(self,"CPU Turbo","Choisir NORMAL MODE ou TURBO ON")
            return
        if not self.settings.turbo_auth_enabled:
            QMessageBox.information(self,"CPU Turbo","Autoriser le Turbo dans Paramètres → Général")
            return
        from .turbo_polkit import request_turbo
        self.turbo.setEnabled(False)
        self.turbo.setToolTip("Authentification administrateur demandée via polkit")
        def finished(success,message):
            self.turbo.setEnabled(True)
            self.cpu_controller.mode=None  # Never poll/write privileged sysfs in background.
            self.last_sensor_request=0
            if not success:
                QMessageBox.warning(self,"Autorisation Turbo",message)
            else:
                self._set_turbo_indicator(mode=="on")
                self.turbo.setToolTip(message)
        self._turbo_worker=request_turbo(mode=="on",finished)

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        menu.addAction("Préférences", self.preferences)
        menu.addAction("Extensions", self.plugins)
        menu.addAction("📖 Wiki NovaBar", self.open_wiki)
        menu.addAction("Quitter", QApplication.instance().quit)
        self.busy = True
        try:
            menu.exec(event.globalPos())
        finally:
            self.busy = False
            self.arm_hide()


def main():
    parser = argparse.ArgumentParser()
    from . import __version__
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument("--restore-xfce-after-pid", type=int)
    parser.add_argument("--expect-version")
    parser.add_argument("--wait-for-pid", type=int)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--setup", action="store_true", help="Reopen installation preferences")
    parser.add_argument("--preview", metavar="PNG", help="Render static HUD offscreen without changing user settings")
    args = parser.parse_args()
    if args.restore_xfce_after_pid:
        from .desktop_backend import restore_after_exit
        restore_after_exit(args.restore_xfce_after_pid)
        return 0
    if args.wait_for_pid:
        import psutil
        deadline = time.monotonic() + 40
        while psutil.pid_exists(args.wait_for_pid) and time.monotonic() < deadline:
            time.sleep(.2)
        if psutil.pid_exists(args.wait_for_pid):
            return 3
    if args.preview or args.self_test:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    if not (args.preview or args.self_test) and sys.platform.startswith("linux") and os.getenv("DISPLAY"):
        from .platforms import detected_target
        if detected_target() == "bazzite":
            os.environ.setdefault("QT_QPA_PLATFORM", "xcb")
    app = QApplication(sys.argv[:1])
    app.setApplicationName("HealthPerfsBar")
    app.setOrganizationName("HealthPerfs")
    app.setWindowIcon(novabar_icon("blue-neon"))
    app.setQuitOnLastWindowClosed(False)
    if args.self_test:
        if args.expect_version and args.expect_version != __version__:
            return 4
        widget = HudCanvas(PluginRegistry())
        widget.resize(1400, 190)
        widget.show()
        app.processEvents()
        if widget.grab().isNull():
            return 2
        widget.close()
        return 0
    if args.preview:
        settings = Settings(configured=True, auto_hide=False)
    else:
        data_dir().mkdir(parents=True, exist_ok=True)
        lock = QLockFile(str(data_dir() / "session.lock"))
        if not lock.tryLock(100):
            QMessageBox.information(None, "Health & Perfs", "Une instance est déjà ouverte dans cette session.")
            return 0
        settings = Settings.load()
        packaged = os.getenv("NOVABAR_PACKAGED") in ("deb", "flatpak") or (getattr(sys,"frozen",False) and Path(sys.executable).with_name("native-install.json").is_file())
        if (args.setup or not settings.configured) and packaged:
            # A .deb/.flatpak already contains NovaBar: configure without
            # launching the separate runtime installer or duplicating binaries.
            from .dialogs import SettingsDialog
            first_run = not settings.configured
            dialog = SettingsDialog(settings, app.screens(), first_run=first_run)
            if dialog.exec() != QDialog.DialogCode.Accepted or args.setup:
                return 0
        elif args.setup or not settings.configured:
            from .installer import InstallerWizard
            payload = None
            if getattr(sys, "frozen", False):
                payload = Path(sys.executable).parents[3] if sys.platform == "darwin" else Path(sys.executable).parent.parent
            dialog = InstallerWizard(settings, source_root=os.getenv("HEALTHBAR_SOURCE_ROOT"), payload=payload)
            dialog.exec()
            return 0
    if not args.preview:
        from .install_engine import refresh_active_shortcuts
        refresh_active_shortcuts()
    bar = Bar(settings)
    app.aboutToQuit.connect(bar.close)
    if settings.hud_enabled or args.preview:
        bar.show()
    if not args.preview:
        QTimer.singleShot(900, bar.offer_xfce_cyber)
    if args.preview:
        bar.setGeometry(0, 0, 2048, 72)
        bar.actions.setFixedWidth(400)
        bar.turbo.setFixedSize(96,48)
        for index in range(1,5):
            bar.button_layout.itemAt(index).widget().setFixedSize(49,48)
        app.processEvents()
        if not bar.grab().save(args.preview):
            raise OSError("Impossible d’enregistrer l’aperçu")
        return 0
    return app.exec()
