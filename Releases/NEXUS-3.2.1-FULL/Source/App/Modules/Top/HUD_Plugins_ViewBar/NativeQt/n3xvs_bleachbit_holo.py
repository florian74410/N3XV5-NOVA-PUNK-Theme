"""N3XV5 Holo SSD Cleaner v2.4.2 — conservative BleachBit CLI frontend.

No shell, no automatic deletion, no global sudo/root HUD. All deletions are
previewed and explicitly confirmed. Admin privileges only via pkexec for apt.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
import os
import re
import shutil

from PySide6.QtCore import Qt, QProcess, QTimer
from PySide6.QtWidgets import (
    QCheckBox, QDialog, QHBoxLayout, QLabel, QPushButton, QTextEdit,
    QVBoxLayout, QWidget,
)

# Intentional allowlist — no browser session/cookie/password clearing,
# no package removal, no APT package lists, no trash, no free-space wiping.
USER_OPTIONS = ("system.cache", "thumbnails.cache")
ROOT_OPTIONS = ("apt.clean", "apt.autoclean")


def choose_options(available, root):
    approved = ROOT_OPTIONS if root else USER_OPTIONS
    return tuple(x for x in approved if x in available)


def free_bytes():
    try:
        return shutil.disk_usage(Path.home()).free
    except OSError:
        return None


def preview_is_empty(output):
    """Recognize explicit zero-file/zero-byte BleachBit previews, not guesses."""
    items = re.search(r"(?im)^(?:files potentially removable|fichiers potentiellement supprimables)\s*:\s*0\b", output)
    size = re.search(r"(?im)^(?:space potentially recoverable|espace disque potentiellement récupérable)\s*:\s*0\s*(?:B|octets?)\b", output)
    return bool(items and size)


def display_bytes(value):
    if value is None:
        return "indisponible"
    return f"{value / (1024 ** 2):.1f} Mio"


class CleanerController:
    def __init__(self, panel):
        self.panel = panel
        self.proc = None
        self.phase = "idle"
        self.busy = False
        self.root_mode = False
        self.selected = ()
        self.preview_output = ""
        self.step = ""
        self.spinner_index = 0
        self.free_before = None
        self.output = []
        self._max_output = 100_000
        self.available_options = None

        top = panel.layout().itemAt(0).layout()
        pin = panel.pin_button
        index = top.indexOf(pin)
        if index < 0:
            raise RuntimeError("Bouton Épingler non identifié")
        top.removeWidget(pin)
        column = QVBoxLayout()
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(2)
        column.addWidget(pin)
        self.status = QLabel("", panel)
        self.status.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.status.setFixedHeight(18)
        column.addWidget(self.status)
        top.insertLayout(index, column)

        root_layout = panel.layout()
        control = QWidget(panel)
        row = QHBoxLayout(control)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(5)
        self.button = QPushButton("NETTOYER", control)
        self.button.setToolTip("Analyse des caches puis confirmation du nettoyage")
        self.admin = QCheckBox("ROOT · APT", control)
        self.admin.setToolTip("Caches APT uniquement ; Polkit demande une autorisation")
        row.addWidget(self.button, 1)
        row.addWidget(self.admin)
        # The button is in the same content/footer area as the SSD test action.
        root_layout.insertWidget(max(1, root_layout.count() - 1), control)
        self.message = QLabel("Nettoyage utilisateur : caches uniquement · prévisualisation obligatoire", panel)
        self.message.setObjectName("n3xvsCleanerMessage")
        self.message.setWordWrap(True)
        self.message.setStyleSheet("color:#8ecde3;font-size:10px;")
        root_layout.insertWidget(max(1, root_layout.count() - 1), self.message)
        self.button.clicked.connect(self.start)
        self.admin.toggled.connect(self.set_mode)
        self.spinner = QTimer(panel)
        self.spinner.setInterval(115)
        self.spinner.timeout.connect(self.animate)

    def set_mode(self, active):
        if self.busy:
            self.admin.blockSignals(True)
            self.admin.setChecked(self.root_mode)
            self.admin.blockSignals(False)
            return
        self.root_mode = bool(active)
        self.set_state("idle", "Mode ROOT : caches APT seulement · authentification Polkit"
                       if active else "Mode utilisateur : caches temporaires, sans données personnelles")

    def set_state(self, phase, text):
        self.phase = phase
        self.status.setToolTip(text)
        self.message.setText(text)
        if phase == "loading":
            self.status.setStyleSheet("color:#27dcff;font-size:16px;font-weight:900;")
            self.spinner.start()
            self.animate()
        else:
            self.spinner.stop()
            icon, color = {"success": ("✓", "#45e69b"), "error": ("✕", "#ff5271"),
                           "idle": ("", "#8ecde3")}.get(phase, ("", "#8ecde3"))
            self.status.setText(icon)
            self.status.setStyleSheet(f"color:{color};font-size:17px;font-weight:900;")

    def animate(self):
        frames = ("◴", "◷", "◶", "◵")
        self.status.setText(frames[self.spinner_index % len(frames)])
        self.spinner_index += 1

    def lock_controls(self, locked):
        self.busy = locked
        self.button.setEnabled(not locked)
        self.admin.setEnabled(not locked)

    def available(self):
        if shutil.which("bleachbit") is None:
            self.set_state("error", "BleachBit absent : sudo apt install bleachbit")
            return False
        if self.root_mode and shutil.which("pkexec") is None:
            self.set_state("error", "Polkit introuvable ; impossible de demander les droits ROOT")
            return False
        return True

    def start(self):
        if self.busy or not self.available():
            return
        self.lock_controls(True)
        self.set_state("loading", "Détection des catégories disponibles…")
        self.run("list", "bleachbit", ["--list-cleaners"])

    def run(self, step, program, args):
        self.step = step
        self.output = []
        proc = QProcess(self.panel)
        self.proc = proc
        proc.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        proc.readyReadStandardOutput.connect(lambda p=proc: self.collect(p))
        proc.finished.connect(lambda code, status, p=proc: self.finished(p, code, status))
        proc.errorOccurred.connect(lambda error, p=proc: self.failed(p, error))
        proc.start(program, args)

    def collect(self, proc):
        data = bytes(proc.readAllStandardOutput()).decode("utf-8", "replace")
        if proc is self.proc and sum(map(len, self.output)) < self._max_output:
            self.output.append(data)

    def failed(self, proc, error):
        if proc is not self.proc:
            return
        if error == QProcess.ProcessError.FailedToStart:
            self.proc = None
            self.lock_controls(False)
            self.set_state("error", "BleachBit / pkexec impossible à démarrer")
            proc.deleteLater()

    def finished(self, proc, code, status):
        if proc is not self.proc:
            proc.deleteLater()
            return
        self.collect(proc)
        output = "".join(self.output).strip()
        step = self.step
        self.proc = None
        proc.deleteLater()
        if code != 0 or status != QProcess.ExitStatus.NormalExit:
            self.lock_controls(False)
            self.set_state("error", f"Échec {step} (code {code}) : {(output[-260:] or 'pas de résultat')}")
            return

        if step == "list":
            available = {line.strip() for line in output.splitlines() if '.' in line}
            self.selected = choose_options(available, self.root_mode)
            if not self.selected:
                self.lock_controls(False)
                self.set_state("error", "Aucune catégorie sécurisée disponible pour ce mode : vérifier bleachbit --list-cleaners")
                return
            self.set_state("loading", "Prévisualisation " + ", ".join(self.selected))
            if self.root_mode:
                # Preview under exactly the same permission scope as actual cleaning.
                self.run("preview", "pkexec", ["/usr/bin/bleachbit", "--preview", *self.selected])
            else:
                self.run("preview", "bleachbit", ["--preview", *self.selected])
            return

        if step == "preview":
            self.preview_output = output
            self.lock_controls(False)
            if preview_is_empty(output):
                self.set_state("success", "Rien à nettoyer dans ce profil (0 fichier · 0 octet). "
                               + ("Essaie le mode Utilisateur pour les caches personnels." if self.root_mode
                                  else "Les caches sélectionnés sont déjà vides."))
                return
            self.set_state("idle", "Analyse terminée · vérifier la liste avant suppression")
            self.confirm()
            return

        if step == "clean":
            self.lock_controls(False)
            after = free_bytes()
            delta = after - self.free_before if after is not None and self.free_before is not None else None
            note = (f" · variation d'espace libre : {display_bytes(delta)}" if delta is not None
                    else " · espace libre indisponible")
            self.set_state("success", "BleachBit terminé · " + datetime.now().strftime('%H:%M') + note)

    def confirm(self):
        label = "ROOT · caches APT" if self.root_mode else "Utilisateur · caches temporaires"
        dialog = QDialog(self.panel)
        dialog.setWindowTitle("N3XV5 — Prévisualisation BleachBit")
        bounds = dialog.screen().availableGeometry() if dialog.screen() is not None else None
        if bounds is not None:
            dialog.resize(min(570, bounds.width() - 50), min(420, bounds.height() - 80))
        else:
            dialog.resize(540, 390)
        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel("Mode : " + label + "\nPrévisualisation uniquement, aucune suppression effectuée.", dialog))
        view = QTextEdit(dialog)
        view.setReadOnly(True)
        view.setPlainText(self.preview_output or "Aucun élément à nettoyer trouvé.")
        layout.addWidget(view, 1)
        if self.root_mode:
            layout.addWidget(QLabel("Si APT indique 0 B, teste le mode Utilisateur : ce sont des caches distincts.", dialog))
        choices = QHBoxLayout()
        cancel = QPushButton("Annuler", dialog)
        go = QPushButton("Confirmer le nettoyage", dialog)
        choices.addWidget(cancel)
        choices.addWidget(go)
        layout.addLayout(choices)
        cancel.clicked.connect(dialog.reject)
        go.clicked.connect(dialog.accept)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            self.set_state("idle", "Nettoyage annulé — aucune suppression")
            return
        self.free_before = free_bytes()
        self.lock_controls(True)
        self.set_state("loading", "Nettoyage BleachBit en cours…")
        if self.root_mode:
            self.run("clean", "pkexec", ["/usr/bin/bleachbit", "--clean", *self.selected])
        else:
            self.run("clean", "bleachbit", ["--clean", *self.selected])


def attach_storage_cleaner(bar):
    panel = getattr(bar, "module_holos", {}).get("storage")
    if panel is None:
        return None
    if getattr(panel, "_n3xvs_cleaner", None) is None:
        panel._n3xvs_cleaner = CleanerController(panel)
    return panel._n3xvs_cleaner
