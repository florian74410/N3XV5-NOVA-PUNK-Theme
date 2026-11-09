from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QFormLayout, QComboBox,
    QSpinBox, QSlider, QCheckBox, QDialogButtonBox, QPushButton, QFileDialog,
    QMessageBox, QListWidget, QHBoxLayout, QTabWidget, QWidget, QLineEdit, QScrollArea, QColorDialog)
from . import __version__
from .autostart import set_enabled
from .plugins import PluginRegistry
from .module_preferences import load as load_module_prefs, save as save_module_prefs, FIELDS, MODULES
from .theme_overrides import load as load_theme_overrides, save as save_theme_overrides
from .settings_visual import PCBSettingsDialog, BarPreview

STYLE = """
QDialog { background: #061224; color: #dfedff; }
QTabWidget::pane { border: 1px solid #17639b; border-radius: 8px; padding: 15px; }
QTabBar::tab { color: #c6eaff; padding: 10px 13px; background: #091b32; border: 1px solid #17639b; }
QTabBar::tab:selected { background: #104377; color: #31dcff; border-bottom: 2px solid #21ceff; }
QLineEdit { color: #e4f2ff; background: #0b2440; border: 1px solid #17639b; padding: 8px; }
QLabel, QCheckBox { color: #c4d9f7; font-size: 13px; }
QLabel#title { color: #31dcff; font-size: 25px; font-weight: 700; }
QPushButton, QComboBox, QSpinBox { color: #dcecff; background: #0b2440;
 border: 1px solid #17639b; border-radius: 6px; padding: 9px; }
QPushButton:hover { border-color: #00ddff; background: #123960; }
QPushButton:disabled { color: #65798c; border-color: #19314a; }
QListWidget { background: #040d1b; color: #dcecff; border: 1px solid #17639b; padding: 8px; }
QSlider::groove:horizontal { height: 4px; background: #17476c; }
QSlider::handle:horizontal { width: 16px; margin: -6px 0; background: #14d8ff; border-radius: 8px; }
QCheckBox { spacing: 12px; }
"""



_catalog_workers = set()  # Keep nonblocking workers alive if settings closes.

class CatalogReader(QThread):
    finished_catalog = Signal(object, object)
    def run(self):
        from .plugin_sources import SourceStore, fetch_catalog
        try:
            rows, errors = fetch_catalog(SourceStore().load())
            self.finished_catalog.emit(rows, errors)
        except (OSError, ValueError, TypeError) as exc:
            self.finished_catalog.emit({}, [str(exc)])



class SettingsDialog(PCBSettingsDialog):
    def __init__(self, settings, screens, first_run=False, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.module_prefs = load_module_prefs()
        self.pending_theme_colors = load_theme_overrides()
        self.module_controls = {}
        self.setWindowTitle("Installation • Health & Perfs" if first_run else "Préférences • Health & Perfs")
        self.use_pcb_theme(settings.theme)
        # Enough room for columns and glass controls, but fit smaller screens.
        bounds = screens[min(settings.screen, len(screens)-1)].availableGeometry() if screens else None
        width = min(1180, max(700, (bounds.width()-60) if bounds else 1180))
        height = min(820, max(570, (bounds.height()-70) if bounds else 820))
        self.setMinimumSize(min(900,width),min(570,height))
        self.resize(width,height)
        box = QVBoxLayout(self)
        box.setContentsMargins(36, 35, 36, 30)
        box.setSpacing(13)
        title = QLabel(("◈ NOVA / REDBLACK 0.8.2.2 — CONTROL CENTER"
                        if settings.theme=="redblack-0822" else
                        "◈ NOVA NEXUS HD • v"+__version__+"   /   PARAMÈTRES"))
        title.setObjectName("title")
        box.addWidget(title)
        intro = QLabel(("CYBERPUNK ELECTRONIC SYSTEM / PARAMÈTRES & MODULES ACTIFS"
                        if settings.theme=="redblack-0822" else
                        "NovaBar / Health & Perfs  —  Linux XFCE  /  Contrôleur des barres, modules et effets PCB"))
        intro.setWordWrap(True)
        box.addWidget(intro)
        form = QFormLayout()
        form.setVerticalSpacing(16)
        self.position = QComboBox()
        self.position.addItems(["Haut", "Bas", "Droite • verticale", "Gauche • verticale"])
        self.position.setCurrentIndex(("top", "bottom", "right", "left").index(settings.position))
        form.addRow("Placement", self.position)
        self.screen = QComboBox()
        self.screen.addItems([f"Écran {i+1} • {s.name()}" for i, s in enumerate(screens)])
        self.screen.setCurrentIndex(min(settings.screen, len(screens)-1))
        form.addRow("Écran", self.screen)
        self.thickness = QSpinBox()
        self.thickness.setRange(50, 150)
        self.thickness.setValue(settings.thickness)
        self.thickness.setSuffix(" px")
        form.addRow("Épaisseur", self.thickness)
        self.opacity = QSlider(Qt.Orientation.Horizontal)
        self.opacity.setRange(0, 100)
        self.opacity.setValue(settings.opacity)
        self.opacity_label = QLabel(f"{settings.opacity} %")
        self.opacity.valueChanged.connect(lambda v: self.opacity_label.setText(f"{v} %"))
        row = QHBoxLayout()
        row.addWidget(self.opacity)
        row.addWidget(self.opacity_label)
        form.addRow("Opacité des modules", row)
        self.auto_hide = QCheckBox("Rétracter après 15 s sans survol")
        self.auto_hide.setChecked(settings.auto_hide)
        self.retract_mode = QComboBox()
        for label, key in (("Always visible", "always"), ("Auto retract", "auto"), ("Manual retract only", "manual")):
            self.retract_mode.addItem(label, key)
        self.retract_mode.setCurrentIndex(max(0, self.retract_mode.findData(settings.retract_mode or ("auto" if settings.auto_hide else "manual"))))
        form.addRow("Rétractation", self.retract_mode)
        self.always_on_top = QCheckBox("Always-on-top (selon le compositeur)")
        self.always_on_top.setChecked(settings.always_on_top)
        form.addRow("Priorité", self.always_on_top)
        self.autostart = QCheckBox("Lancer à l’ouverture de ma session")
        self.autostart.setChecked(settings.autostart)
        if __import__("os").environ.get("NOVABAR_PACKAGED") == "flatpak":
            self.autostart.setEnabled(False)
            self.autostart.setToolTip("Démarrage automatique non géré dans cette édition Flatpak.")
        
        self.hide_seconds = QSpinBox()
        self.hide_seconds.setRange(3, 120)
        self.hide_seconds.setValue(settings.hide_seconds)
        self.hide_seconds.setSuffix(" secondes")
        form.addRow("Délai avant veille", self.hide_seconds)
        self.length_percent = QSpinBox()
        self.length_percent.setRange(25, 100)
        self.length_percent.setValue(settings.length_percent)
        self.length_percent.setSuffix(" % écran")
        form.addRow("Longueur", self.length_percent)
        self.alignment = QComboBox()
        self.alignment.addItems(["Left", "Middle", "Right"])
        self.alignment.setCurrentIndex(("left", "center", "right").index(settings.alignment))
        form.addRow("Alignement", self.alignment)
        tabs = QTabWidget()
        tabs.setObjectName("settingsTabs")
        general = QWidget()
        general_form = QFormLayout(general)
        general_form.addRow("Démarrage", self.autostart)
        self.refresh_seconds = QSpinBox()
        self.refresh_seconds.setRange(1, 30)
        self.refresh_seconds.setSuffix(" s")
        self.refresh_seconds.setValue(settings.refresh_seconds)
        general_form.addRow("Actualisation", self.refresh_seconds)
        self.shell_dir = QLineEdit(settings.shell_dir)
        self.shell_dir.setPlaceholderText("~/Scripts/HardwareHealth")
        folder_row = QHBoxLayout()
        folder_row.addWidget(self.shell_dir)
        browse = QPushButton("Parcourir")
        browse.clicked.connect(self.choose_script_folder)
        folder_row.addWidget(browse)
        general_form.addRow("Dossier Shell", folder_row)
        from .ui_kit import THEMES
        self.theme = QComboBox()
        for key, label in THEMES.items(): self.theme.addItem(label, key)
        self.theme.setCurrentIndex(max(0, self.theme.findData(settings.theme)))
        general_form.addRow("Thème actif", self.theme)
        self.holo_enabled=QCheckBox("Ouvrir les panneaux par clic sur le logo du plugin")
        self.holo_enabled.setChecked(settings.holo_enabled)
        general_form.addRow("Holo",self.holo_enabled)
        update_button = QPushButton("Upgrade • mise à jour automatique")
        update_button.clicked.connect(self.open_updates)
        general_form.addRow("CYBER NEXUS HUD", update_button)
        from .help_links import WIKI_URL
        from PySide6.QtGui import QDesktopServices
        from PySide6.QtCore import QUrl
        wiki_button = QPushButton("📖 Ouvrir le Wiki NovaBar")
        wiki_button.setToolTip("Guide : installation, interface, capteurs, plugins, dépannage")
        wiki_button.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(WIKI_URL)))
        general_form.addRow("Documentation", wiki_button)
        installer_button = QPushButton("Profil, confidentialité et raccourcis…")
        installer_button.clicked.connect(self.open_installer)
        if __import__("os").environ.get("NOVABAR_PACKAGED") in ("deb", "flatpak"):
            installer_button.setEnabled(False)
            installer_button.setToolTip("Le paquet Linux gère les fichiers du programme ; utiliser les préférences et le gestionnaire de plugins.")
        general_form.addRow("NovaBar", installer_button)
        # All three independent panels live in the same NovaBar executable.
        docks = QWidget()
        docks_layout = QVBoxLayout(docks)
        docks_layout.addWidget(QLabel("NOVABAR • QUATRE PANNEAUX INDÉPENDANTS"))
        docks_layout.addWidget(QLabel("Chaque panneau peut être activé séparément. Les colonnes se cachent après 3 secondes. Elles s’ouvrent dans les 10 px du bord, sans trait visible."))
        self.hud_enabled = QCheckBox("Barre principale • télémétrie CPU/GPU/RAM/SSD")
        self.hud_enabled.setChecked(settings.hud_enabled)
        docks_layout.addWidget(self.hud_enabled)
        self.dock_left_enabled = QCheckBox("Dock gauche actif")
        self.dock_left_enabled.setChecked(settings.dock_left_enabled)
        docks_layout.addWidget(self.dock_left_enabled)
        self.dock_right_enabled = QCheckBox("Dock droit actif")
        self.dock_right_enabled.setChecked(settings.dock_right_enabled)
        docks_layout.addWidget(self.dock_right_enabled)
        self.bottom_dock_enabled = QCheckBox("Barre inférieure CYBER NEXUS • applications, fenêtres et système")
        self.bottom_dock_enabled.setChecked(settings.bottom_dock_enabled)
        self.bottom_dock_enabled.setEnabled(__import__("sys").platform.startswith("linux"))
        docks_layout.addWidget(self.bottom_dock_enabled)
        self.dock_left_kind = QComboBox()
        self.dock_left_kind.addItem("Dossiers personnels", "folders")
        self.dock_left_kind.addItem("Applications du Bureau", "apps")
        self.dock_left_kind.setCurrentIndex(max(0, self.dock_left_kind.findData(settings.dock_left_kind)))
        docks_layout.addWidget(QLabel("Contenu du dock gauche (l'autre dock reçoit automatiquement l'autre contenu) :"))
        docks_layout.addWidget(self.dock_left_kind)
        docks_layout.addWidget(QLabel("⠿ Glissez la poignée d'un dock vers le bord opposé ou cliquez ↔ pour échanger les deux."))
        docks_layout.addWidget(QLabel("Glissez des dossiers depuis Thunar ou des lanceurs .desktop du Bureau pour les ajouter ou les réorganiser."))
        docks_layout.addWidget(QLabel("Les raccourcis sont conservés dans votre profil NovaBar ; aucun fichier n'est déplacé ou effacé."))
        docks_layout.addStretch()
        display = QWidget()
        display.setLayout(form)
        edit = QWidget()
        editor = QVBoxLayout(edit)
        editor.addWidget(QLabel("ÉDITION DU HUD • réglages rapides"))
        tip = QLabel("La présentation se compacte automatiquement lorsque la longueur diminue.")
        tip.setWordWrap(True)
        editor.addWidget(tip)
        reset = QPushButton("Rétablir l'affichage d'origine")
        reset.clicked.connect(self.reset_display)
        editor.addWidget(reset)
        editor.addStretch()
        extensions = QWidget()
        ext_layout = QVBoxLayout(extensions)
        ext_layout.addWidget(QLabel("Importer des ZIP v2, activer les plugins et restaurer une version."))
        open_ext = QPushButton("OUVRIR LE PLUGIN MANAGER")
        open_ext.clicked.connect(lambda: PluginsDialog(PluginRegistry(), self).exec())
        ext_layout.addWidget(open_ext)
        ext_layout.addStretch()
        help_tab = QWidget()
        help_layout = QVBoxLayout(help_tab)
        howto = QLabel("Bord de l'écran : révéler la barre\nFlèche haute : minimiser\nLogo en haut à droite : ouvrir/fermer le Holo\nCPU Mode : selon noyau et permissions\nZIP : code jamais exécuté automatiquement")
        howto.setWordWrap(True)
        help_layout.addWidget(howto)
        help_layout.addStretch()
        wiki = QWidget()
        wiki_layout = QVBoxLayout(wiki)
        description = QLabel("Documentation NovaBar : installation, configuration, capteurs et extensions. Ces liens s’ouvrent dans le navigateur ; cette base accueillera un viewer intégré.")
        description.setWordWrap(True); wiki_layout.addWidget(description)
        from .help_links import DOC_LINKS
        for label, url in DOC_LINKS.items():
            button = QPushButton(label)
            button.clicked.connect(lambda checked=False, url=url: QDesktopServices.openUrl(QUrl(url)))
            wiki_layout.addWidget(button)
        wiki_layout.addStretch()
        tabs.addTab(wiki, "Wiki")
        tabs.addTab(docks, "Docks")
        modules_tab = QWidget()
        modules_layout = QVBoxLayout(modules_tab)
        title_modules = QLabel("MODULES DE LA BARRE PRINCIPALE")
        modules_layout.addWidget(title_modules)
        modules_description = QLabel(
            "Décochez les plugins à masquer sur cette machine. "
            "Les modules restent installés, leurs mesures ne sont pas supprimées. "
            "Le module Power affiche uniquement les données réellement disponibles.")
        modules_description.setWordWrap(True)
        modules_layout.addWidget(modules_description)
        from .hud import HudCanvas
        labels = {
            "cpu": "CPU — Fréquence et température",
            "gpu": "GPU — Fréquence et utilisation",
            "ram": "RAM — Utilisation et capacité",
            "storage": "Stockage — SSD / HDD",
            "fans": "Ventilateurs — RPM",
            "network": "Réseau — Débits et ping",
            "power": "Power ⚡ — Consommation et tensions",
        }
        self.module_checks = {}
        for slot, name in labels.items():
            control = QCheckBox(name)
            control.setChecked(slot not in settings.hidden_modules)
            self.module_checks[slot] = control
            modules_layout.addWidget(control)
        modules_layout.addStretch()
        tabs.addTab(modules_tab, "Modules")
        xfce_tab = QWidget()
        xfce_layout = QVBoxLayout(xfce_tab)
        info = QLabel("XFCE CYBER SKIN • Habillage du panneau natif")
        xfce_layout.addWidget(info)
        explanation = QLabel("Conserve les icônes et les fenêtres du panneau XFCE original. "
                             "Ajoute un habillage PCB avec impulsions animées, modifie au choix son épaisseur "
                             "(sans jamais dépasser 2 fois l'originale) et le masque automatiquement "
                             "après le délai choisi. Le bord natif de 1 px assure le rappel au survol.")
        explanation.setWordWrap(True)
        xfce_layout.addWidget(explanation)
        self.xfce_skin_enabled = QCheckBox("Activer l'habillage CYBER NEXUS du panneau XFCE inférieur")
        self.xfce_skin_enabled.setChecked(settings.xfce_skin_enabled)
        xfce_layout.addWidget(self.xfce_skin_enabled)
        delay_info = QLabel("La temporisation commence après avoir quitté le panneau. "
                            "Les paramètres de rétraction et d'épaisseur d'origine sont sauvegardés.")
        delay_info.setWordWrap(True)
        xfce_layout.addWidget(delay_info)
        self.xfce_skin_delay_seconds = QSpinBox()
        self.xfce_skin_delay_seconds.setRange(1, 120)
        self.xfce_skin_delay_seconds.setSuffix(" secondes")
        self.xfce_skin_delay_seconds.setValue(settings.xfce_skin_delay_seconds)
        xfce_layout.addWidget(QLabel("Délai avant rétractation complète"))
        xfce_layout.addWidget(self.xfce_skin_delay_seconds)
        self.xfce_skin_scale_percent = QSlider(Qt.Orientation.Horizontal)
        self.xfce_skin_scale_percent.setRange(100, 200)
        self.xfce_skin_scale_percent.setValue(settings.xfce_skin_scale_percent)
        self.xfce_skin_scale_label = QLabel(
            f"Épaisseur : {settings.xfce_skin_scale_percent} % de l'originale (max. 200 %)")
        self.xfce_skin_scale_percent.valueChanged.connect(
            lambda number: self.xfce_skin_scale_label.setText(
                f"Épaisseur : {number} % de l'originale (max. 200 %)"))
        xfce_layout.addWidget(self.xfce_skin_scale_label)
        xfce_layout.addWidget(self.xfce_skin_scale_percent)
        self.xfce_skin_fx_intensity = QSlider(Qt.Orientation.Horizontal)
        self.xfce_skin_fx_intensity.setRange(0, 100)
        self.xfce_skin_fx_intensity.setValue(settings.xfce_skin_fx_intensity)
        self.xfce_skin_fx_label = QLabel(f"Effets lumineux : {settings.xfce_skin_fx_intensity} %")
        self.xfce_skin_fx_intensity.valueChanged.connect(
            lambda amount: self.xfce_skin_fx_label.setText(f"Effets lumineux : {amount} %"))
        xfce_layout.addWidget(self.xfce_skin_fx_label)
        xfce_layout.addWidget(self.xfce_skin_fx_intensity)
        xfce_note = QLabel("L'ajout d'icônes reste géré par le panneau XFCE : clic droit sur le panneau "
                           "→ Panneau → Ajouter de nouveaux éléments. Désactiver l'habillage restaure "
                           "l'apparence et le comportement de repli précédents.")
        xfce_note.setWordWrap(True)
        xfce_layout.addWidget(xfce_note)
        xfce_layout.addStretch()
        tabs.addTab(xfce_tab, "XFCE Cyber")
        # One logical General page; no separate legacy Édition/Docks tabs.
        # Reparent the existing form widgets rather than recreating their controls.
        while tabs.count():
            tabs.removeTab(0)
        general_all = QWidget()
        general_all.setObjectName("generalContent")
        general_all_box = QVBoxLayout(general_all)
        general_all_box.setContentsMargins(21,16,21,18)
        general_all_box.setSpacing(13)
        section_header = QLabel("◈  GÉNÉRAL  /  COMPORTEMENT")
        section_header.setObjectName("sectionHeader")
        general_all_box.addWidget(section_header)
        controls = QWidget()
        grid = QFormLayout(controls)
        grid.setVerticalSpacing(13)
        self.top_hover_ms = QSpinBox()
        self.top_hover_ms.setRange(500,4000)
        self.top_hover_ms.setSingleStep(100)
        self.top_hover_ms.setSuffix(" ms")
        self.top_hover_ms.setValue(settings.top_hover_ms)
        grid.addRow("Survol continu avant déploiement", self.top_hover_ms)
        self.top_trigger_px = QSpinBox()
        self.top_trigger_px.setRange(5,20)
        self.top_trigger_px.setSuffix(" px")
        self.top_trigger_px.setValue(settings.top_trigger_px)
        grid.addRow("Zone sensible du haut",self.top_trigger_px)
        self.top_reserved = QCheckBox("Réserver la place du HUD dans XFCE / X11")
        self.top_reserved.setChecked(settings.top_reserved)
        grid.addRow("Espace réservé",self.top_reserved)
        self.bottom_dock_height = QSpinBox()
        self.bottom_dock_height.setRange(62,130)
        self.bottom_dock_height.setSuffix(" px")
        self.bottom_dock_height.setValue(settings.bottom_dock_height)
        grid.addRow("Hauteur du dock inférieur",self.bottom_dock_height)
        self.bottom_tabs_max = QSpinBox()
        self.bottom_tabs_max.setRange(1,3)
        self.bottom_tabs_max.setValue(settings.bottom_tabs_max)
        grid.addRow("Onglets visibles (surplus : +N)",self.bottom_tabs_max)
        self.bottom_nav_opacity=QSlider(Qt.Orientation.Horizontal)
        self.bottom_nav_opacity.setRange(10,100)
        self.bottom_nav_opacity.setValue(settings.bottom_nav_opacity)
        opacity_status=QLabel(str(settings.bottom_nav_opacity)+" %")
        self.bottom_nav_opacity.valueChanged.connect(
            lambda value:opacity_status.setText(str(value)+" %"))
        opacity_row=QHBoxLayout()
        opacity_row.addWidget(self.bottom_nav_opacity)
        opacity_row.addWidget(opacity_status)
        grid.addRow("Transparence de navigation basse",opacity_row)
        no_reserve=QLabel("Le dock inférieur se superpose maintenant aux fenêtres sans réserver de hauteur.")
        no_reserve.setWordWrap(True)
        grid.addRow("",no_reserve)
        self.turbo_auth_enabled = QCheckBox("Exiger le mot de passe administrateur (polkit)")
        self.turbo_auth_enabled.setChecked(settings.turbo_auth_enabled)
        grid.addRow("CPU Turbo",self.turbo_auth_enabled)
        general_all_box.addWidget(controls)
        self.live_bar_preview=BarPreview(settings.theme)
        self.theme.currentIndexChanged.connect(lambda:self.live_bar_preview.change_theme(self.theme.currentData()))
        general_all_box.addWidget(self.live_bar_preview)
        for heading, section in (
            ("Démarrage et actualisation", general),
            ("Position, dimensions et affichage", display),
            ("Édition de l'affichage", edit),
            ("Barres, docks et rétraction", docks),
            ("Habillage du panneau XFCE", xfce_tab)):
            group_heading = QLabel("◈  " + heading.upper())
            group_heading.setObjectName("sectionHeader")
            general_all_box.addWidget(group_heading)
            general_all_box.addWidget(section)
        general_all_box.addStretch()
        general_scroll = QScrollArea()
        general_scroll.setObjectName("settingsScroll")
        general_scroll.setWidgetResizable(True)
        general_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        general_scroll.setWidget(general_all)
        # Plugin manager remains the existing secure GitHub ZIP catalogue.
        # Existing ext_layout already owns the window; append a clear source action.
        sources_button = QPushButton("⌁ Sources GitHub / Plugins")
        sources_button.clicked.connect(lambda: PluginsDialog(PluginRegistry(), self).exec())
        ext_layout.addWidget(sources_button)
        # CPU gets its own controls without duplicating telemetry collectors.
        cpu_page = QWidget()
        cpu_box = QVBoxLayout(cpu_page)
        cpu_box.addWidget(QLabel("CPU  /  HOLOGRAMME ET COLLECTE"))
        cpu_box.addWidget(QLabel("La fréquence est partagée par les capteurs; pas de timer CPU supplémentaire."))
        cpu_box.addWidget(QLabel("Taux de rafraîchissement CPU (secondes)"))
        self.cpu_refresh_control = QSpinBox()
        self.cpu_refresh_control.setRange(1, 30)
        self.cpu_refresh_control.setSuffix(" s")
        self.cpu_refresh_control.setValue(settings.refresh_seconds)
        self.cpu_refresh_control.valueChanged.connect(self.refresh_seconds.setValue)
        self.refresh_seconds.valueChanged.connect(self.cpu_refresh_control.setValue)
        cpu_box.addWidget(self.cpu_refresh_control)
        self.cpu_holo_control = QCheckBox("Activer le Holo Mode des modules")
        self.cpu_holo_control.setChecked(settings.holo_enabled)
        self.cpu_holo_control.toggled.connect(self.holo_enabled.setChecked)
        self.holo_enabled.toggled.connect(self.cpu_holo_control.setChecked)
        cpu_box.addWidget(self.cpu_holo_control)
        cpu_box.addWidget(QLabel("Un clic sur toute la surface du module ouvre son Holo Mode."))
        cpu_box.addStretch()
        updates_page = QWidget()
        updates_box = QVBoxLayout(updates_page)
        updates_box.addWidget(QLabel("MISE À JOUR  /  NOVABAR"))
        update_action = QPushButton("↻ Vérifier et installer une mise à jour")
        update_action.clicked.connect(self.open_updates)
        updates_box.addWidget(update_action)
        updates_box.addStretch()
        # Preserve the existing functional module enable/disable controls.
        ext_layout.addWidget(QLabel("MODULES INSTALLÉS  /  VISIBILITÉ"))
        for slot, control in self.module_checks.items():
            control.setParent(extensions)
            ext_layout.addWidget(control)
        ext_layout.addWidget(QLabel("Les plugins ZIP peuvent être activés ou désactivés dans le gestionnaire."))
        ext_layout.addWidget(QLabel("EXTENSIONS DISPONIBLES / GITHUB"))
        self.catalog_list = QListWidget()
        self.catalog_list.setMinimumHeight(130)
        ext_layout.addWidget(self.catalog_list)
        refresh_catalog_button = QPushButton("↻ Actualiser le catalogue GitHub")
        refresh_catalog_button.clicked.connect(self.reload_catalog)
        ext_layout.addWidget(refresh_catalog_button)
        self.catalog_worker = None

        about = QWidget()
        about_layout = QVBoxLayout(about)
        about_layout.addWidget(QLabel("NOVA NEXUS HD  /  WIKI ET AIDE"))
        about_layout.addWidget(wiki)
        about_layout.addWidget(help_tab)
        about_layout.addStretch()
        # Visual settings: reuse native theme presets, preview colours without
        # altering the active desktop until the user explicitly applies a preset.
        colors_page = QWidget()
        colors_box = QVBoxLayout(colors_page)
        colors_box.addWidget(QLabel("THÈMES & COULEURS / PRÉVISUALISATION"))
        colors_box.addWidget(QLabel("Sélectionnez la palette dans Générale. Aperçu de son rendu et de ses accents."))
        colors_box.addWidget(QLabel("NOVA REDBLACK 0.8.2.2 : cadres, HUD, Holo et panneaux reconstruits."))
        wallpaper_row=QHBoxLayout()
        apply_wallpaper_button=QPushButton("◈  Appliquer le fond REDBLACK")
        restore_wallpaper_button=QPushButton("↶  Restaurer le fond précédent")
        def set_wallpaper():
            try:
                from .redblack_wallpaper import apply_wallpaper
                output=apply_wallpaper()
                QMessageBox.information(self,"REDBLACK • Fond d'écran",
                    "Fond REDBLACK appliqué sur XFCE. Sauvegarde du fond précédent conservée.\n"+output)
            except (OSError,ValueError) as error:
                QMessageBox.warning(self,"REDBLACK • Fond d'écran",str(error))
        def undo_wallpaper():
            try:
                from .redblack_wallpaper import restore_wallpaper
                total=restore_wallpaper()
                QMessageBox.information(self,"REDBLACK • Fond d'écran",
                    f"Fond d'écran XFCE restauré pour {total} espace(s) de travail.")
            except (OSError,ValueError) as error:
                QMessageBox.warning(self,"REDBLACK • Restauration",str(error))
        apply_wallpaper_button.clicked.connect(set_wallpaper)
        restore_wallpaper_button.clicked.connect(undo_wallpaper)
        apply_wallpaper_button.setEnabled(settings.theme=="redblack-0822")
        self.theme.currentIndexChanged.connect(
            lambda:apply_wallpaper_button.setEnabled(self.theme.currentData()=="redblack-0822"))
        wallpaper_row.addWidget(apply_wallpaper_button)
        wallpaper_row.addWidget(restore_wallpaper_button)
        colors_box.addLayout(wallpaper_row)
        colors_box.addWidget(QLabel("Fond XFCE facultatif : sauvegarde puis restauration explicite, aucune suppression de panneau."))
        from .cockpit_style import PALETTES
        self.palette_preview = QLabel()
        self.palette_preview.setMinimumHeight(68)
        colors_box.addWidget(self.palette_preview)
        def update_palette_preview():
            name=self.theme.currentData()
            colors=PALETTES.get(name, PALETTES.get('blue-neon', ('#00d9ff','#1860ff','#061020')))
            custom=self.pending_theme_colors.get(name,{})
            primary=custom.get('primary',colors[0])
            secondary=custom.get('secondary',colors[1])
            background=custom.get('background','#061224')
            self.palette_preview.setText("   PCB   /   " + name.upper() + "   ·   " + primary + "  " + secondary)
            self.palette_preview.setStyleSheet(
                "color:"+primary+"; background:"+background+
                ";border:2px solid "+secondary+";font-weight:700;")
        self.theme.currentIndexChanged.connect(update_palette_preview)
        palette_select = QComboBox()
        for index in range(self.theme.count()):
            palette_select.addItem(self.theme.itemText(index), self.theme.itemData(index))
        palette_select.setCurrentIndex(self.theme.currentIndex())
        palette_select.currentIndexChanged.connect(self.theme.setCurrentIndex)
        self.theme.currentIndexChanged.connect(palette_select.setCurrentIndex)
        colors_box.insertWidget(2, palette_select)
        for key,label in (("primary","Néon principal"),
                          ("secondary","Néon secondaire"),
                          ("background","Verre / fond")):
            picker=QPushButton("◈  Choisir : "+label)
            def choose_color(checked=False, part=key):
                theme_name=self.theme.currentData()
                preset=PALETTES.get(theme_name,PALETTES["blue-neon"])
                fallbacks={"primary":preset[0],"secondary":preset[1],"background":"#061224"}
                initial=self.pending_theme_colors.get(theme_name,{}).get(part,fallbacks[part])
                chosen=QColorDialog.getColor(QColor(initial),self,"NOVA / "+part)
                if chosen.isValid():
                    self.pending_theme_colors.setdefault(theme_name,{})[part]=chosen.name().upper()
                    update_palette_preview()
            picker.clicked.connect(choose_color)
            colors_box.addWidget(picker)
        reset_palette=QPushButton("↺  Restaurer les couleurs d'origine de cette palette")
        def reset_palette_colors():
            self.pending_theme_colors.pop(self.theme.currentData(),None)
            update_palette_preview()
        reset_palette.clicked.connect(reset_palette_colors)
        colors_box.addWidget(reset_palette)
        update_palette_preview()
        colors_box.addWidget(QLabel("Palettes existantes conservées : bleu, Matrix, rouge, cyber-futuriste."))
        colors_box.addStretch()
        # Per-plugin configuration. The shared collector provides cached
        # values; this page does not create any additional acquisition timers.
        for module in MODULES:
            page = QWidget()
            form_plugin = QVBoxLayout(page)
            form_plugin.addWidget(QLabel(module.upper() + " / HOLOGRAMME"))
            rate = QSpinBox()
            rate.setRange(1,60)
            rate.setSuffix(" s")
            rate.setValue(self.module_prefs[module]["refresh_seconds"])
            form_plugin.addWidget(QLabel("Fraîcheur souhaitée des données"))
            form_plugin.addWidget(rate)
            holo = QCheckBox("Autoriser le mode Holo")
            holo.setChecked(self.module_prefs[module]["holo_enabled"])
            form_plugin.addWidget(holo)
            details={}
            form_plugin.addWidget(QLabel("Détails à afficher dans l'Holo :"))
            for field_name in FIELDS[module]:
                check = QCheckBox(field_name.replace("_"," ").capitalize())
                check.setChecked(field_name in self.module_prefs[module]["details"])
                details[field_name]=check
                form_plugin.addWidget(check)
            form_plugin.addStretch()
            self.module_controls[module]=(rate,holo,details)
            self.plugin_pages = getattr(self, 'plugin_pages', {})
            self.plugin_pages[module] = page
        tabs.addTab(general_scroll, "Générale")
        tabs.addTab(colors_page, "Thèmes & Couleurs")
        tabs.addTab(extensions, "Extensions")
        tabs.addTab(cpu_page, "CPU")
        tabs.addTab(updates_page, "Mise à jour")
        tabs.addTab(about, "À propos")
        for module in MODULES:
            tabs.addTab(self.plugin_pages[module], module.upper())
        tabs.tabBar().hide()
        nav = QListWidget()
        nav.setObjectName("settingsNavigation")
        nav.setFixedWidth(258 if settings.theme=="redblack-0822" else 230)
        entries=(("⌂  GÉNÉRAL","◈  APPARENCE","▣  PLUGINS","◉  CPU","⟲  MISE À JOUR","ⓘ  À PROPOS")
                 if settings.theme=="redblack-0822" else
                 ("GÉNÉRALE","THÈMES & COULEURS","EXTENSIONS","CPU","MISE À JOUR","À PROPOS"))
        for name in entries:nav.addItem(name)
        for name in MODULES:
            nav.addItem("↳ " + name.upper())
        nav.currentRowChanged.connect(tabs.setCurrentIndex)
        nav.setCurrentRow(0)
        split = QHBoxLayout()
        split.addWidget(nav)
        split.addWidget(tabs, 1)
        box.addLayout(split, 1)
        note = QLabel("Mesures locales : — indique un capteur indisponible.\nPriorité d’affichage limitée par le système et son compositeur.")
        note.setWordWrap(True)
        box.addWidget(note)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        reset_button=buttons.addButton("↺ Rétablir",QDialogButtonBox.ButtonRole.ResetRole)
        reset_button.clicked.connect(self.reset_display)
        buttons.button(QDialogButtonBox.StandardButton.Save).setText("Installer et ouvrir" if first_run else "✓ Appliquer")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Annuler")
        buttons.accepted.connect(self.save)
        buttons.rejected.connect(self.reject)
        box.addWidget(buttons)

    def reload_catalog(self):
        if self.catalog_worker is not None and self.catalog_worker.isRunning():
            return
        self.catalog_list.clear()
        self.catalog_list.addItem("Connexion aux sources GitHub…")
        worker = CatalogReader()
        _catalog_workers.add(worker)
        self.catalog_worker = worker
        worker.finished_catalog.connect(self.show_catalog)
        def release_worker():
            _catalog_workers.discard(worker)
            if self.catalog_worker is worker:
                self.catalog_worker = None
            worker.deleteLater()
        worker.finished.connect(release_worker)
        worker.start()

    def show_catalog(self, entries, errors):
        self.catalog_list.clear()
        for item in sorted(entries.values(), key=lambda obj:obj["id"]):
            self.catalog_list.addItem(item["id"]+"  ·  v"+item["version"]+"  ·  "+item["source"])
        for message in errors:
            self.catalog_list.addItem("⚠ "+str(message))
        if not entries and not errors:
            self.catalog_list.addItem("Aucune extension disponible")

    def open_updates(self):
        from .updates import UpdateDialog
        UpdateDialog(self, auto_upgrade=True).exec()

    def open_installer(self):
        from .installer import InstallerWizard
        from .profiles import workspace_dir, current_profile
        import json
        wizard = InstallerWizard(self.settings, parent=self)
        path = workspace_dir() / "App/Profiles" / (current_profile() + ".json")
        if path.is_file():
            record = json.loads(path.read_text(encoding="utf-8"))
            identity = record.get("identity", {})
            wizard.email.setText(identity.get("email", ""))
            wizard.username.setText(identity.get("username", ""))
            wizard.share.setChecked(identity.get("share_experience", False))
        # Editing the profile uses the first page and preserves installed runtime files.
        def save_profile_settings():
            from .profiles import save_profile
            from dataclasses import asdict, replace
            if wizard.stack.currentIndex() == 0:
                wizard.advance()
                if wizard.stack.currentIndex() == 1:
                    wizard.next.setText("ENREGISTRER")
            elif wizard.stack.currentIndex() == 1:
                try:
                    changed = replace(self.settings, position=wizard.position.currentData(),
                        thickness=wizard.thickness.value(), length_percent=wizard.length.value(),
                        opacity=wizard.opacity.value(), auto_hide=wizard.retract_mode.currentData()=="auto", retract_mode=wizard.retract_mode.currentData(),
                        theme=wizard.theme.currentData(),always_on_top=wizard.always_on_top.isChecked(),holo_enabled=wizard.holo_enabled.isChecked(),
                        autostart=wizard.autostart.isChecked(), shortcuts=wizard.bindings()).validate()
                    set_enabled(changed.autostart)
                    changed.save()
                    previous = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
                    save_profile(wizard.identity, asdict(changed), previous.get("installation"))
                    self.settings.__dict__.update(changed.__dict__)
                    wizard.accept()
                except (ValueError, OSError) as error:
                    QMessageBox.warning(wizard, "Profil", str(error))
        wizard.next.clicked.disconnect()
        wizard.next.clicked.connect(save_profile_settings)
        wizard.autostart.setChecked(self.settings.autostart)
        wizard.next.setText("VALIDER")
        if wizard.exec() == QDialog.DialogCode.Accepted:
            self.accept()

    def choose_script_folder(self):
        chosen = QFileDialog.getExistingDirectory(self, "Dossier de scripts Shell", self.shell_dir.text())
        if chosen:
            self.shell_dir.setText(chosen)

    def reset_display(self):
        self.top_hover_ms.setValue(1000)
        self.top_trigger_px.setValue(10)
        self.top_reserved.setChecked(True)
        self.bottom_dock_height.setValue(84)
        self.bottom_tabs_max.setValue(3)
        self.bottom_nav_opacity.setValue(55)
        self.turbo_auth_enabled.setChecked(True)
        self.length_percent.setValue(100)
        self.thickness.setValue(72)
        self.opacity.setValue(88)
        self.hide_seconds.setValue(15)

    def save(self):
        from dataclasses import replace
        updated = replace(self.settings, position=("top", "bottom", "right", "left")[self.position.currentIndex()],
            screen=self.screen.currentIndex(), thickness=self.thickness.value(), opacity=self.opacity.value(),
            auto_hide=self.retract_mode.currentData() == "auto", retract_mode=self.retract_mode.currentData(),
            always_on_top=self.always_on_top.isChecked(), theme=self.theme.currentData(), holo_enabled=self.holo_enabled.isChecked(), hide_seconds=self.hide_seconds.value(),
            autostart=self.autostart.isChecked(), configured=True,
            length_percent=self.length_percent.value(),
            alignment=("left", "center", "right")[self.alignment.currentIndex()],
            refresh_seconds=self.refresh_seconds.value(), shell_dir=self.shell_dir.text().strip(),
            hud_enabled=self.hud_enabled.isChecked(),
            dock_left_enabled=self.dock_left_enabled.isChecked(),
            dock_right_enabled=self.dock_right_enabled.isChecked(),
            bottom_dock_enabled=self.bottom_dock_enabled.isChecked(),
            bottom_dock_height=self.bottom_dock_height.value(),bottom_tabs_max=self.bottom_tabs_max.value(),
            bottom_nav_opacity=self.bottom_nav_opacity.value(),
            top_hover_ms=self.top_hover_ms.value(), top_trigger_px=self.top_trigger_px.value(),
            top_reserved=self.top_reserved.isChecked(), turbo_auth_enabled=self.turbo_auth_enabled.isChecked(),
            dock_left_kind=self.dock_left_kind.currentData(),
            dock_right_kind="apps" if self.dock_left_kind.currentData() == "folders" else "folders",
            hidden_modules=[slot for slot, checkbox in self.module_checks.items()
                            if not checkbox.isChecked()],
            xfce_skin_enabled=self.xfce_skin_enabled.isChecked(),
            xfce_skin_delay_seconds=self.xfce_skin_delay_seconds.value(),
            xfce_skin_scale_percent=self.xfce_skin_scale_percent.value(),
            xfce_skin_fx_intensity=self.xfce_skin_fx_intensity.value())
        try:
            set_enabled(updated.autostart)
            updated.save()
        except (OSError, ValueError) as error:
            QMessageBox.warning(self, "Enregistrement impossible", str(error))
            return
        for module,(rate,holo,fields) in self.module_controls.items():
            self.module_prefs[module] = {
                "refresh_seconds":rate.value(),
                "holo_enabled":holo.isChecked(),
                "details":[key for key,control in fields.items() if control.isChecked()]
            }
        try:
            save_module_prefs(self.module_prefs)
            save_theme_overrides(self.pending_theme_colors)
        except OSError as error:
            QMessageBox.warning(self, "Préférences des modules", str(error))
            return
        self.settings.__dict__.update(updated.__dict__)
        self.accept()


# Plugin Manager v0.3.3 uses one compact two-tab dialog, independent of the installer.
# Import here keeps the existing app/settings interface stable.
from .plugin_manager import PluginsDialog
