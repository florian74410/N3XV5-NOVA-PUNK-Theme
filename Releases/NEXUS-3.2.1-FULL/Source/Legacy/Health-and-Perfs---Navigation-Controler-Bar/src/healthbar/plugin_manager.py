"""NovaBar 2-in-1 plugin manager: installed versions + configurable remote GitHub sources."""
import re
import sys
import tempfile
import zipfile
from pathlib import Path

from PySide6.QtCore import Qt, QThread, Signal, QTimer
from PySide6.QtGui import QColor
from .redblack_shell import active as redblack_active, control_stylesheet
from PySide6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QTabWidget,
    QTableWidget, QTableWidgetItem, QHeaderView, QPushButton, QLabel, QLineEdit,
    QCheckBox, QMessageBox, QDialogButtonBox, QFileDialog, QProgressBar,
    QAbstractItemView,
)

from . import __version__
from .plugins import version_tuple
from .plugin_sources import SourceStore, normalized_source, fetch_catalog, download_package

STYLE = """
QDialog {background:#031022;color:#D6EEFF;}
QWidget {color:#D6EEFF;}
QLabel {color:#C5E6FF;background:transparent;border:0;}
QLabel#title {color:#5AE5FF;font-size:17px;font-weight:800;}
QLabel#hint {color:#78A9D2;font-size:11px;}
QTabWidget::pane {background:#06172B;border:1px solid #137FBE;border-radius:8px;}
QTabBar::tab {background:#071B35;color:#81C8ED;border:1px solid #124C87;padding:7px 16px;}
QTabBar::tab:selected {color:#D5FAFF;background:#0B3561;border-bottom:2px solid #46E8FF;}
QTableWidget {background:#04142A;color:#DBF4FF;border:1px solid #1268A1;gridline-color:#123459;
    alternate-background-color:#081E38;selection-background-color:#164D8D;}
QHeaderView::section {background:#0B2850;color:#63D9FF;font-weight:600;
    padding:5px;border:0;border-bottom:1px solid #17659C;}
QPushButton {background:rgba(8,32,62,210);color:#D9F8FF;border:1px solid #128DE9;
    border-radius:6px;padding:6px 11px;min-height:22px;}
QPushButton:hover {background:#124A85;border-color:#83F7FF;}
QPushButton:disabled {color:#527B96;border-color:#143954;background:#061527;}
QLineEdit {background:#06182D;color:#E7F9FF;border:1px solid #188FC4;padding:6px;}
QProgressBar {background:#04132A;border:1px solid #1379B0;border-radius:4px;text-align:center;height:8px;}
QProgressBar::chunk {background:#35DEFF;border-radius:4px;}
QCheckBox {color:#BDE6FF;}
"""

class CatalogThread(QThread):
    result = Signal(object, object)
    def __init__(self, sources):
        super().__init__()
        self.sources = [dict(x) for x in sources]

    def run(self):
        try:
            found, errors = fetch_catalog(self.sources)
        except Exception as error:
            found, errors = {}, [str(error)]
        self.result.emit(found, errors)

class DownloadThread(QThread):
    progress = Signal(int)
    result = Signal(object, object)
    def __init__(self, entry, directory):
        super().__init__()
        self.entry = dict(entry)
        self.directory = Path(directory)

    def run(self):
        try:
            dest = self.directory / self.entry["filename"]
            path, digest = download_package(self.entry, dest, self.progress.emit)
            self.result.emit((str(path), digest), None)
        except Exception as error:
            self.result.emit(None, str(error))

class SourceEditDialog(QDialog):
    def __init__(self, source=None, parent=None):
        super().__init__(parent)
        self.setStyleSheet(
            (control_stylesheet() + "QDialog {background:#080609;border:2px solid #FF2945;}")
            if redblack_active() else STYLE)
        self.setWindowTitle("NovaBar • Source GitHub")
        self.resize(490, 265)
        root = QVBoxLayout(self)
        form = QFormLayout()
        self.fields = {}
        for key, title, placeholder in (
            ("name", "Nom", "Ex. NovaBar Official"),
            ("url", "Dépôt GitHub", "https://github.com/organisation/depot"),
            ("branch", "Branche", "main"),
            ("folder", "Dossier des ZIP", "Plugins"),
        ):
            field = QLineEdit((source or {}).get(key, {"branch": "main", "folder": "Plugins"}.get(key, "")))
            field.setPlaceholderText(placeholder)
            self.fields[key] = field
            form.addRow(title, field)
        root.addLayout(form)
        self.enabled = QCheckBox("Source activée")
        self.enabled.setChecked((source or {}).get("enabled", True))
        root.addWidget(self.enabled)
        foot = QDialogButtonBox(QDialogButtonBox.StandardButton.Save |
                                 QDialogButtonBox.StandardButton.Cancel)
        foot.accepted.connect(self.validate)
        foot.rejected.connect(self.reject)
        root.addWidget(foot)
        self.source = None

    def validate(self):
        try:
            self.source = normalized_source(
                **{key: input_.text() for key, input_ in self.fields.items()},
                enabled=self.enabled.isChecked())
        except ValueError as error:
            QMessageBox.warning(self, "Source invalide", str(error))
            return
        self.accept()

class PluginsDialog(QDialog):
    """Small single-window manager: modules table / GitHub sources table."""
    def __init__(self, registry, parent=None, source_store=None):
        super().__init__(parent)
        self.registry = registry
        self.sources_store = source_store or SourceStore()
        self.remote = {}
        self.errors = []
        self._catalog_thread = None
        self._download_thread = None
        self._tempdir = None
        self._queued_refresh = False
        self.items = []
        try:
            self.sources = self.sources_store.load()
        except (OSError, ValueError, TypeError) as error:
            self.sources = []
            self.errors = [f"Configuration des sources invalide : {error}"]
        self.setWindowTitle("NovaBar   •   PLUGIN CONTROL CENTER")
        self.resize(745, 485)
        self.setMinimumSize(590, 355)
        self.setStyleSheet(
            (control_stylesheet() + "QDialog {background:#080609;border:2px solid #FF2945;}")
            if redblack_active() else STYLE)
        root = QVBoxLayout(self)
        root.setContentsMargins(13, 12, 13, 10)
        root.setSpacing(6)
        title_row = QHBoxLayout()
        title = QLabel("◈ PLUGINS CONTROL CENTER")
        title.setObjectName("title")
        title_row.addWidget(title)
        title_row.addStretch()
        self.refresh_button = QPushButton("⟳ Synchroniser")
        self.refresh_button.clicked.connect(self.refresh_catalog)
        title_row.addWidget(self.refresh_button)
        root.addLayout(title_row)
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        root.addWidget(self.tabs, 1)
        plugins = QWidget()
        pbox = QVBoxLayout(plugins)
        pbox.setContentsMargins(8, 8, 8, 8)
        pbox.setSpacing(5)
        self.table = self.make_table(["Plugin", "Installée", "Dernière", "Source", "Statut"])
        self.table.itemSelectionChanged.connect(self.selected_changed)
        pbox.addWidget(self.table, 1)
        row = QHBoxLayout()
        self.selection_info = QLabel("Sélectionne un plugin pour consulter ses versions.")
        self.selection_info.setObjectName("hint")
        row.addWidget(self.selection_info, 1)
        self.install_button = QPushButton("Installer")
        self.install_button.clicked.connect(self.install_selected)
        self.install_button.hide()
        row.addWidget(self.install_button)
        self.enable_button = QPushButton("Activer")
        self.enable_button.clicked.connect(self.toggle)
        self.enable_button.hide()
        row.addWidget(self.enable_button)
        pbox.addLayout(row)
        bar = QHBoxLayout()
        self.import_button = QPushButton("+ Importer ZIP local")
        self.import_button.clicked.connect(self.import_package)
        bar.addWidget(self.import_button)
        self.rollback_button = QPushButton("↶ Restaurer")
        self.rollback_button.clicked.connect(self.rollback)
        bar.addWidget(self.rollback_button)
        bar.addStretch()
        pbox.addLayout(bar)
        self.tabs.addTab(plugins, "◈  Plugins")
        source_panel = QWidget()
        sbox = QVBoxLayout(source_panel)
        sbox.setContentsMargins(8, 8, 8, 8)
        sbox.setSpacing(5)
        self.sources_table = self.make_table(["Source", "Dépôt", "Branche", "Dossier", "État"])
        sbox.addWidget(self.sources_table, 1)
        actions = QHBoxLayout()
        for name, method in (("+ Ajouter", self.add_source),
                             ("✎ Modifier", self.edit_source),
                             ("− Supprimer", self.remove_source),
                             ("↻ Recharger", self.refresh_catalog)):
            action = QPushButton(name)
            action.clicked.connect(method)
            actions.addWidget(action)
        sbox.addLayout(actions)
        note = QLabel("Dépôts GitHub HTTPS • dossier contenant des ZIP versionnés • par utilisateur")
        note.setObjectName("hint")
        sbox.addWidget(note)
        self.tabs.addTab(source_panel, "⌁  Sources")
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.hide()
        root.addWidget(self.progress)
        status = QHBoxLayout()
        self.status = QLabel("Mode sécurisé : jamais de lancement automatique d'install.sh.")
        self.status.setObjectName("hint")
        self.status.setWordWrap(True)
        status.addWidget(self.status, 1)
        close = QPushButton("Fermer")
        close.clicked.connect(self.accept)
        status.addWidget(close)
        root.addLayout(status)
        self.refresh_sources()
        self.refresh()
        self._opened = False

    def showEvent(self, event):
        super().showEvent(event)
        if not self._opened:
            self._opened = True
            QTimer.singleShot(0, self.refresh_catalog)

    def make_table(self, headers):
        table = QTableWidget(0, len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.setAlternatingRowColors(True)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        table.verticalHeader().hide()
        table.verticalHeader().setDefaultSectionSize(30)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        table.horizontalHeader().setStretchLastSection(True)
        table.setShowGrid(False)
        return table

    def busy(self):
        return ((self._catalog_thread is not None and self._catalog_thread.isRunning()) or
                (self._download_thread is not None and self._download_thread.isRunning()))

    def refresh(self):
        chosen = self.selected_id()
        installed = {p["id"]: p for p in self.registry.installed()}
        self.items = []
        self.table.setRowCount(0)
        self.table.blockSignals(True)
        for ident in sorted(set(installed) | set(self.remote)):
            current, available = installed.get(ident), self.remote.get(ident)
            if available and (not current or version_tuple(available["version"]) > version_tuple(current["version"])):
                state = "MISE À JOUR" if current else "NOUVEAU"
            elif current and available:
                state = "À JOUR" if version_tuple(current["version"]) == version_tuple(available["version"]) else "LOCAL + RÉCENT"
            else:
                state = "LOCAL"
            self.items.append((ident, current, available))
            row = self.table.rowCount()
            self.table.insertRow(row)
            values = [current["name"] if current else ident,
                      current["version"] if current else "—",
                      available["version"] if available else "—",
                      available["source"] if available else "Local",
                      state]
            for col, value in enumerate(values):
                cell = QTableWidgetItem(str(value))
                cell.setData(Qt.ItemDataRole.UserRole, ident)
                if col == 4 and state in ("MISE À JOUR", "NOUVEAU"):
                    cell.setForeground(QColor("#6DFFCA"))
                self.table.setItem(row, col, cell)
            if ident == chosen:
                self.table.selectRow(row)
        self.table.blockSignals(False)
        self.table.setColumnWidth(0, 190)
        self.table.setColumnWidth(1, 92)
        self.table.setColumnWidth(2, 92)
        self.table.setColumnWidth(3, 145)
        self.selected_changed()

    def selected_id(self):
        row = self.table.currentRow()
        return self.table.item(row,0).data(Qt.ItemDataRole.UserRole) if row >= 0 and self.table.item(row,0) else None

    def selected(self):
        ident = self.selected_id()
        for id_, current, available in self.items:
            if id_ == ident:
                return id_, current, available
        return None

    def selected_changed(self):
        selected = self.selected()
        self.install_button.hide()
        self.enable_button.hide()
        if not selected:
            self.selection_info.setText("Sélectionne une ligne pour gérer ce plugin.")
            self.rollback_button.setEnabled(False)
            return
        ident, current, available = selected
        update = available and (not current or version_tuple(available["version"]) > version_tuple(current["version"]))
        if update:
            self.install_button.setText("Mettre à jour" if current else "Installer")
            self.install_button.show()
        if current:
            self.enable_button.setText("Désactiver" if current["enabled"] else "Activer")
            self.enable_button.show()
        self.rollback_button.setEnabled(bool(current))
        self.selection_info.setText(f"{ident} • {current['version'] if current else 'non installé'} → "
                                    f"{available['version'] if available else 'non disponible'}")

    def refresh_sources(self):
        self.sources_table.setRowCount(0)
        for i, source in enumerate(self.sources):
            self.sources_table.insertRow(i)
            for c, value in enumerate((source["name"], source["url"].replace("https://github.com/",""),
                                       source["branch"], source["folder"], "●" if source["enabled"] else "○")):
                self.sources_table.setItem(i,c,QTableWidgetItem(value))
        for i, width in enumerate((145,210,100,100)):
            self.sources_table.setColumnWidth(i,width)

    def persist_sources(self, updated):
        self.sources_store.save(updated)
        self.sources = self.sources_store.load()
        self.refresh_sources()
        self.refresh_catalog()

    def add_source(self):
        editor = SourceEditDialog(parent=self)
        if editor.exec() == QDialog.DialogCode.Accepted:
            try:
                self.persist_sources(self.sources + [editor.source])
            except ValueError as error:
                QMessageBox.warning(self, "Sources", str(error))

    def edit_source(self):
        index = self.sources_table.currentRow()
        if index < 0:
            return
        editor = SourceEditDialog(self.sources[index], self)
        if editor.exec() == QDialog.DialogCode.Accepted:
            changed = self.sources.copy()
            changed[index] = editor.source
            try:
                self.persist_sources(changed)
            except ValueError as error:
                QMessageBox.warning(self, "Sources", str(error))

    def remove_source(self):
        index = self.sources_table.currentRow()
        if index < 0:
            return
        if QMessageBox.question(self, "Supprimer la source ?",
                                f"Retirer « {self.sources[index]['name']} » du catalogue ?\n"
                                "Les plugins déjà installés seront conservés.") == QMessageBox.StandardButton.Yes:
            self.persist_sources([s for i,s in enumerate(self.sources) if i != index])

    def refresh_catalog(self):
        if self.busy():
            self._queued_refresh = True
            return
        self.status.setText("Synchronisation du catalogue GitHub…")
        self.refresh_button.setEnabled(False)
        self._catalog_thread = CatalogThread(self.sources)
        self._catalog_thread.result.connect(self.on_catalog)
        self._catalog_thread.finished.connect(self._idle)
        self._catalog_thread.start()

    def _idle(self):
        if not self.busy():
            self.refresh_button.setEnabled(True)
            if self._queued_refresh:
                self._queued_refresh = False
                QTimer.singleShot(0, self.refresh_catalog)

    def on_catalog(self, catalog, errors):
        self.remote = catalog
        self.errors = errors
        self.refresh()
        if errors:
            self.status.setText("⚠ " + " | ".join(str(x) for x in errors)[:280])
        else:
            self.status.setText(f"Catalogue synchronisé • {len(catalog)} plugin(s) • aucun lanceur à recompiler pour une mise à jour compatible")
        self.refresh_button.setEnabled(True)

    def install_selected(self):
        selected = self.selected()
        if not selected or self.busy():
            return
        ident, current, available = selected
        if available and (not current or version_tuple(available["version"]) > version_tuple(current["version"])):
            self._tempdir = tempfile.TemporaryDirectory(prefix="novabar-plugin-")
            self._download_thread = DownloadThread(available, self._tempdir.name)
            self._download_thread.progress.connect(self.on_progress)
            self._download_thread.result.connect(lambda result, error: self.download_complete(available, result, error))
            self._download_thread.finished.connect(self._idle)
            self.install_button.setEnabled(False)
            self.status.setText(f"Téléchargement sécurisé : {available['filename']}")
            self.progress.setRange(0, 0)
            self.progress.show()
            self._download_thread.start()

    def on_progress(self, count):
        self.status.setText(f"Téléchargement du ZIP : {count / 1024:.0f} Kio")

    def download_complete(self, entry, result, error):
        self.progress.hide()
        self.install_button.setEnabled(True)
        try:
            if error:
                raise ValueError(error)
            path, expected = result
            manifest, digest = self.registry.inspect(path)
            if (digest != expected or manifest["id"] != entry["id"] or
                    manifest["version"] != entry["version"]):
                raise ValueError("Identité ou version du manifeste différente du catalogue")
            self.confirm_install(path, manifest, digest)
        except Exception as problem:
            self.status.setText(f"Échec : {problem}")
            QMessageBox.warning(self, "Téléchargement refusé", str(problem))
        finally:
            if self._tempdir:
                self._tempdir.cleanup()
                self._tempdir = None

    def compatible(self, manifest):
        requirements = manifest.get("requires", [])
        for item in requirements:
            match = re.match(r"^healthbar>=(\d+\.\d+\.\d+)$", item, re.IGNORECASE)
            if match and version_tuple(__version__) < version_tuple(match.group(1)):
                return f"Ce plugin requiert NovaBar {match.group(1)} ou supérieur (actuel : {__version__})."
            match = re.match(r"^Python>=(\d+)\.(\d+)$", item, re.IGNORECASE)
            if match and sys.version_info[:2] < (int(match.group(1)),int(match.group(2))):
                return "Version de Python incompatible."
        return None

    def confirm_install(self, path, manifest, digest):
        problem = self.compatible(manifest)
        if problem:
            QMessageBox.warning(self,"Runtime incompatible",problem + "\nMettez à jour NovaBar une fois pour acquérir cette nouvelle API.")
            self.status.setText("Plugin incompatible avec le moteur actuel")
            return
        dependency_details = ""
        try:
            with zipfile.ZipFile(path) as archive:
                if "DEPENDENCY.md" in archive.namelist() and archive.getinfo("DEPENDENCY.md").file_size <= 32768:
                    dependency_details = archive.read("DEPENDENCY.md").decode("utf-8", errors="replace").strip()
        except (OSError, ValueError, zipfile.BadZipFile):
            dependency_details = ""
        if dependency_details:
            dependency_details = "\nDépendances du paquet :\n" + dependency_details[:1100] + "\n"
        answer = QMessageBox.question(self, "NovaBar • Installation du plugin",
            f"{manifest['name']}  ·  {manifest['version']}\n"
            f"Slot : {manifest['slot']}\n"
            f"Dépendances déclarées : {', '.join(manifest.get('requires', [])) or 'aucune'}\n"
            f"Permissions : {', '.join(manifest.get('permissions', [])) or 'aucune'}\n"
            f"RAM minimale déclarée : {manifest.get('min_ram_mb', 0)} Mio\n"
            f"Empreinte SHA-256 : {digest[:20]}…\n"
            f"{dependency_details}\n"
            "Installer cette archive dans votre profil ?\n"
            "Aucun install.sh ni installation système ne sera exécuté.")
        if answer == QMessageBox.StandardButton.Yes:
            self.registry.install(path, digest)
            self.status.setText(f"✓ {manifest['name']} {manifest['version']} installé • rapport enregistré")
            self.refresh()

    def import_package(self):
        if self.busy():
            return
        path, _ = QFileDialog.getOpenFileName(self, "Importer ZIP local", "", "NovaBar plugins (*.zip *.hbp)")
        if path:
            try:
                manifest, digest = self.registry.inspect(path)
                self.confirm_install(path, manifest, digest)
            except (ValueError, OSError, zipfile.BadZipFile, RuntimeError) as error:
                QMessageBox.warning(self, "Archive refusée", str(error))

    def toggle(self):
        selected = self.selected()
        if selected and selected[1]:
            ident, current, _ = selected
            self.registry.set_enabled(ident, not current["enabled"])
            self.refresh()

    def rollback(self):
        selected = self.selected()
        if selected and selected[1]:
            try:
                self.registry.rollback(selected[0])
                self.refresh()
                self.status.setText("Version précédente restaurée")
            except (ValueError, OSError) as error:
                QMessageBox.warning(self, "Restauration impossible", str(error))

    def closeEvent(self, event):
        if self.busy():
            self.status.setText("Synchronisation ou téléchargement en cours…")
            event.ignore()
        else:
            super().closeEvent(event)

    def reject(self):
        if self.busy():
            self.status.setText("Terminez la synchronisation ou le téléchargement avant de fermer.")
            return
        super().reject()

    def accept(self):
        if self.busy():
            self.status.setText("Opération réseau en cours : fermeture temporairement indisponible.")
            return
        super().accept()
