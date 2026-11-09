"""Neon two-page installation wizard with asynchronous compilation and staged self-test."""
import getpass
import os
import re
import subprocess
import sys
from dataclasses import asdict, replace
from datetime import datetime, timezone
from pathlib import Path
from PySide6.QtCore import Qt, QThread, Signal, QUrl, QRectF
from PySide6.QtGui import QColor, QDesktopServices, QPainter, QPixmap, QKeySequence
from PySide6.QtWidgets import (QApplication, QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QWidget, QStackedWidget, QScrollArea, QTextBrowser, QLineEdit, QComboBox,
    QCheckBox, QPushButton, QFormLayout, QSpinBox, QSlider, QProgressBar, QMessageBox,
    QTableWidget, QKeySequenceEdit, QHeaderView, QFileDialog)
from . import __version__
from .branding import BrandHeader
from .config import Settings
from .platforms import TARGETS, detected_target, target_by_key, validate_host
from .profiles import save_profile, workspace_dir, current_profile
from .install_engine import install

REPOSITORY = "https://github.com/florian74410/Health-and-Perfs---Navigation-Controler-Bar"
TERMS_VERSION = "2026-10-31"
TERMS = """<h3>Votre PC. Votre cockpit.</h3>
<p>NovaBar est une barre de suivi et de gestion des performances du PC. Elle rassemble
les informations disponibles sur le processeur, la carte graphique, la mémoire, le stockage,
les ventilateurs et le réseau. Son interface transparente accueille des modules et des thèmes
évolutifs ; les fonctionnalités dépendent du système, du matériel et des plugins activés.
Le contrôle Turbo Linux dépend du noyau et des permissions ; les autres systèmes affichent une indisponibilité explicite.</p>
<h3>Conditions d’utilisation · édition de développement</h3>
<p>Installez uniquement sur un compte que vous êtes autorisé à utiliser. Les mesures sont
indicatives : certaines sondes peuvent être absentes ou indisponibles. Les modifications
matérielles privilégiées ne sont pas activées par cet installateur. Les dépendances tierces
conservent leurs licences respectives. Le code et son historique sont consultables sur le dépôt.</p>
<h3>Partager votre expérience · facultatif</h3>
<p>Souhaitez-vous partager votre expérience avec le créateur et la communauté ? Vos avis,
réclamations et propositions peuvent enrichir le projet et aider à l’adapter aux besoins des
utilisateurs. Vous pourrez consulter l’espace communautaire lorsqu’il sera mis à disposition.</p>
<p>Cette option n’autorise aucune collecte automatique, aucune télémétrie et aucun envoi en
arrière-plan. Seuls les réponses, commentaires et coordonnées que vous choisirez explicitement
de transmettre pourront être envoyés, après présentation du message et de son destinataire.
Votre choix peut être modifié à tout moment dans les préférences.</p>
<h3>Données et contact</h3>
<p>L’adresse e-mail est facultative et reste dans votre profil local. Aucun compte distant
n’est créé. Les profils sont enregistrés dans Documents/NovaBar ; vous pouvez les consulter
et retirer vos coordonnées. Les rapports d’installation restent également locaux.</p>
<p>Le service SMTP et le forum ne sont pas encore configurés : le bouton Contacter prépare
uniquement un brouillon local. Les coordonnées de l’éditeur et du responsable d’un futur service,
la durée de conservation distante et les modalités de suppression devront être publiées
avant l’ouverture de ce service. Ce texte ne remplace pas ces informations.</p>
<p>Merci pour votre compréhension et votre participation.<br>Conditions datées du 31 octobre 2026.</p>"""

WIZARD_STYLE = """
QDialog { color: #e1f3ff; }
QWidget#card { background: rgba(2,12,27,205); border: 1px solid #075e84; border-radius: 10px; }
QLabel { color: #d8efff; font-size: 13px; background: transparent; }
QLabel#step { color: #8eff75; font-size: 17px; font-weight: bold; }
QLabel#caption { color: #73e7bc; font-size: 10px; font-style: italic; }
QLabel#status { color: #a3ff78; font-size: 18px; }
QLineEdit, QComboBox, QSpinBox, QKeySequenceEdit { background: #06182a; color: #e2f5ff;
 border: 1px solid #0878ae; border-radius: 5px; padding: 7px; min-height: 21px; }
QTextBrowser { background: rgba(1,9,24,215); color: #d4eaff; border: 1px solid #087198;
 border-radius: 7px; padding: 10px; font-size: 12px; }
QScrollArea { background: transparent; border: none; }
QScrollArea > QWidget > QWidget { background: transparent; }
QPushButton { background: #08263b; color: #dff7ff; border: 1px solid #0cb8e5;
 border-radius: 6px; padding: 10px 17px; font-weight: bold; }
QPushButton:hover { border-color: #9eff65; color: #baff89; background: #103b48; }
QPushButton:disabled { color: #567283; border-color: #1c4054; }
QPushButton#primary { background: #174b47; color: #b4ff89; border: 1px solid #98ff68; }
QPushButton#help { background: #064ee8; border-radius: 16px; padding: 2px; color: white; }
QCheckBox { color: #ceebf5; spacing: 9px; padding: 3px; background: transparent; }
QCheckBox::indicator { width: 16px; height: 16px; background: #06182a; border: 1px solid #1cb4ac; border-radius: 3px; }
QCheckBox::indicator:checked { background: #65d877; border: 1px solid #b4ff9c; }
QTableWidget { background: #041322; color: #dcf3ff; border: 1px solid #137e94; }
QHeaderView::section { background: #0b2c42; color: #a7f9ec; padding: 6px; }
QSlider::groove:horizontal { height: 4px; background: #0c5277; }
QSlider::handle:horizontal { width: 15px; margin: -5px 0; background: #83fba1; border-radius: 6px; }
QProgressBar { background: #031020; border: 1px solid #118faa; color: #dffff0; border-radius: 8px; text-align: center; min-height: 25px; }
QProgressBar::chunk { background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #007dff,stop:1 #81ff9b); border-radius: 7px; }
QScrollBar:vertical { background: #061729; width: 8px; }
QScrollBar::handle:vertical { background: #126c81; min-height: 24px; border-radius: 4px; }
"""


class InstallWorker(QThread):
    progress = Signal(int, str)
    completed = Signal(dict)
    failed = Signal(str)

    def __init__(self, settings, identity, desktop, source, payload, parent=None):
        super().__init__(parent)
        self.settings=settings;self.identity=identity;self.desktop=desktop
        self.source=source;self.payload=payload

    def run(self):
        try:
            self.completed.emit(install(self.settings,self.identity,self.desktop,self.progress.emit,
                                        source_root=self.source,payload=self.payload))
        except Exception as error:
            self.failed.emit(str(error))


class InstallerWizard(QDialog):
    def __init__(self, settings=None, source_root=None, payload=None, parent=None):
        super().__init__(parent)
        self.settings=settings or Settings.load()
        self.source_root=source_root;self.payload=payload
        self.state=None;self.worker=None;self.identity=None
        self.setWindowTitle("CYBER NEXUS HUD · Installation de NovaBar")
        self.setStyleSheet(WIZARD_STYLE)
        self.scene=QPixmap(str(Path(__file__).parent/"assets/installer-scene.png"))
        screen=QApplication.primaryScreen().availableGeometry()
        self.resize(min(900,screen.width()-32),min(790,screen.height()-40))
        self.setMinimumSize(min(690,screen.width()-32),min(560,screen.height()-40))
        root=QVBoxLayout(self);root.setContentsMargins(24,12,24,12);root.setSpacing(10)
        self.header=BrandHeader();root.addWidget(self.header)
        self.step=QLabel("01 / IDENTITÉ & CONDITIONS");self.step.setObjectName("step");root.addWidget(self.step)
        self.stack=QStackedWidget();root.addWidget(self.stack,1)
        self.build_identity_page();self.build_preferences_page();self.build_progress_page()
        footer=QHBoxLayout();footer.setSpacing(12)
        self.next=QPushButton("VALIDER");self.next.setObjectName("primary");self.next.clicked.connect(self.advance)
        self.cancel=QPushButton("ANNULER");self.cancel.clicked.connect(self.cancel_or_back)
        self.contact=QPushButton("CONTACTER");self.contact.clicked.connect(self.feedback)
        self.help=QPushButton("?");self.help.setObjectName("help");self.help.setFixedSize(33,33)
        self.help.setToolTip("Ouvrir le Wiki du projet");self.help.clicked.connect(lambda:QDesktopServices.openUrl(QUrl(REPOSITORY+"/wiki")))
        for widget in (self.next,self.cancel,self.contact,self.help):footer.addWidget(widget)
        footer.addStretch();root.addLayout(footer)
        caption=QLabel("31 octobre 2026 · France · Créé par une A.I. et un humain… devinez qui est qui 😉")
        caption.setObjectName("caption");caption.setAlignment(Qt.AlignmentFlag.AlignCenter);caption.setWordWrap(True)
        root.addWidget(caption)
        self.accept_terms.toggled.connect(self.update_validation)
        self.update_validation()

    def paintEvent(self,event):
        p=QPainter(self)
        if not self.scene.isNull():
            # Use only the lake/mountain portion of the reference, without duplicating the HUD.
            source=self.scene.copy(0,205,self.scene.width(),self.scene.height()-205)
            scaled=source.scaled(self.size(),Qt.AspectRatioMode.KeepAspectRatioByExpanding,Qt.TransformationMode.SmoothTransformation)
            p.drawPixmap((self.width()-scaled.width())//2,(self.height()-scaled.height())//2,scaled)
        p.fillRect(self.rect(),QColor(1,8,21,215))
        p.setPen(QColor("#087cc1"));p.drawRoundedRect(self.rect().adjusted(1,1,-2,-2),14,14)
        p.end()

    def scroll_page(self):
        scroll=QScrollArea();scroll.setWidgetResizable(True)
        card=QWidget();card.setObjectName("card")
        box=QVBoxLayout(card);box.setContentsMargins(18,16,18,16);box.setSpacing(12)
        scroll.setWidget(card);self.stack.addWidget(scroll)
        return box

    def build_identity_page(self):
        box=self.scroll_page()
        self.rules=QTextBrowser();self.rules.setHtml(TERMS);self.rules.setMinimumHeight(140);self.rules.setMaximumHeight(205)
        box.addWidget(self.rules)
        self.accept_terms=QCheckBox("J’accepte les conditions d’utilisation")
        self.share=QCheckBox("Je souhaite pouvoir partager mon expérience · aucun envoi automatique")
        self.share.setChecked(True)
        box.addWidget(self.accept_terms);box.addWidget(self.share)
        form=QFormLayout();form.setSpacing(10)
        self.email=QLineEdit();self.email.setMaxLength(254);self.email.setPlaceholderText("Facultatif · conservé uniquement dans le profil local")
        self.username=QLineEdit(getpass.getuser())
        self.os_choice=QComboBox()
        for target in TARGETS:self.os_choice.addItem(target.label,target.key)
        self.os_choice.setCurrentIndex(next(i for i,t in enumerate(TARGETS) if t.key==detected_target()))
        form.addRow("E-mail",self.email);form.addRow("Utilisateur / Nom",self.username);form.addRow("Système d’exploitation",self.os_choice)
        box.addLayout(form)
        try:
            import json
            path=workspace_dir()/"App/Profiles"/(current_profile()+".json")
            identity=json.loads(path.read_text(encoding="utf-8")).get("identity",{})
            self.email.setText(identity.get("email",""))
            self.username.setText(identity.get("username",getpass.getuser()))
            self.share.setChecked(identity.get("share_experience",True))
        except (OSError,ValueError,AttributeError,TypeError):
            pass
        self.capabilities=QLabel();self.capabilities.setWordWrap(True);box.addWidget(self.capabilities)
        self.os_choice.currentIndexChanged.connect(self.show_capabilities);self.show_capabilities()
        box.addStretch()

    def show_capabilities(self):
        target=target_by_key(self.os_choice.currentData())
        self.capabilities.setText(target.details)
        if hasattr(self,"next"):self.update_validation()

    def update_validation(self):
        if self.stack.currentIndex()==0:
            self.next.setEnabled(self.accept_terms.isChecked() and target_by_key(self.os_choice.currentData()).available)

    def build_preferences_page(self):
        box=self.scroll_page();form=QFormLayout();form.setSpacing(12)
        self.autostart=QCheckBox("Afficher NovaBar à chaque ouverture de session");self.autostart.setChecked(self.settings.autostart if self.settings.configured else True)
        self.desktop=QCheckBox("Créer un raccourci sur le bureau");self.desktop.setChecked(True)
        self.opacity=QSlider(Qt.Orientation.Horizontal);self.opacity.setRange(0,100);self.opacity.setValue(self.settings.opacity)
        self.opacity_value=QLabel(f"{self.settings.opacity} %")
        self.opacity.valueChanged.connect(lambda value:self.opacity_value.setText(f"{value} %"))
        row=QHBoxLayout();row.addWidget(self.opacity);row.addWidget(self.opacity_value)
        form.addRow("Démarrage automatique",self.autostart);form.addRow("Bureau",self.desktop)
        form.addRow("Opacité des modules",row)
        self.position=QComboBox()
        for label,key in (("Horizontale · Haut","top"),("Horizontale · Bas","bottom"),("Verticale · Droite","right"),("Verticale · Gauche","left")):
            self.position.addItem(label,key)
        self.position.setCurrentIndex(max(0,self.position.findData(self.settings.position)))
        form.addRow("Positionnement",self.position)
        self.thickness=QSpinBox();self.thickness.setRange(50,150);self.thickness.setValue(self.settings.thickness);self.thickness.setSuffix(" px")
        self.length=QSpinBox();self.length.setRange(25,100);self.length.setValue(self.settings.length_percent);self.length.setSuffix(" %")
        form.addRow("Épaisseur",self.thickness);form.addRow("Longueur",self.length)
        self.auto_hide=QCheckBox("Rétracter après 15 secondes sans survol");self.auto_hide.setChecked(self.settings.auto_hide)
        from .ui_kit import THEMES
        self.theme=QComboBox()
        for key,label in THEMES.items():self.theme.addItem(label,key)
        self.theme.setCurrentIndex(max(0,self.theme.findData(self.settings.theme)))
        form.addRow("Thème",self.theme)
        self.retract_mode=QComboBox()
        for label,key in (("Always visible","always"),("Auto retract","auto"),("Manual retract only","manual")):self.retract_mode.addItem(label,key)
        self.retract_mode.setCurrentIndex(max(0,self.retract_mode.findData(self.settings.retract_mode or ("auto" if self.settings.auto_hide else "manual"))))
        form.addRow("Rétractation",self.retract_mode)
        self.always_on_top=QCheckBox("Always-on-top");self.always_on_top.setChecked(self.settings.always_on_top);form.addRow(self.always_on_top)
        self.holo_enabled=QCheckBox("Activer les Holo des plugins");self.holo_enabled.setChecked(self.settings.holo_enabled);form.addRow(self.holo_enabled)
        box.addLayout(form)
        explanation=QLabel("Le fond général reste transparent. Les plugins compatibles peuvent ensuite être installés ou mis à jour sans réinstaller NovaBar, depuis Extensions → Plugin Manager → Sources. La source officielle GitHub est ajoutée au premier lancement ; vous pourrez en configurer d’autres.")
        explanation.setWordWrap(True);box.addWidget(explanation)
        box.addWidget(QLabel("RACCOURCIS · globaux selon le système et ses permissions"))
        self.keys=QTableWidget(0,2);self.keys.setHorizontalHeaderLabels(["Action","Combinaison"])
        self.keys.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.keys.verticalHeader().hide()
        self.keys.setMinimumHeight(130);box.addWidget(self.keys)
        for binding in self.settings.shortcuts:self.add_binding(binding["action"],binding["sequence"])
        row=QHBoxLayout()
        for label,callback in (("+ Ajouter",lambda:self.add_binding()),("Supprimer",self.remove_binding),("Sauvegarder",self.save_binding_draft),("Annuler les modifications",self.reset_bindings)):
            button=QPushButton(label);button.clicked.connect(callback);row.addWidget(button)
        box.addLayout(row)
        self.binding_draft=[dict(binding) for binding in self.settings.shortcuts]
        path=QLabel("Profil et données : "+str(workspace_dir())+"\nL’installation et les mises à jour conservent ce dossier.")
        path.setWordWrap(True);box.addWidget(path);box.addStretch()

    def add_binding(self,action="toggle",sequence=""):
        row=self.keys.rowCount();self.keys.insertRow(row)
        action_box=QComboBox()
        for label,key in (("Afficher / Masquer la barre","toggle"),("Agrandir / Réduire","expand"),("Ouvrir les préférences","preferences")):
            action_box.addItem(label,key)
        action_box.setCurrentIndex(max(0,action_box.findData(action)))
        editor=QKeySequenceEdit(QKeySequence(sequence));editor.setMaximumSequenceLength(1)
        self.keys.setCellWidget(row,0,action_box);self.keys.setCellWidget(row,1,editor)

    def remove_binding(self):
        if self.keys.currentRow()>=0:self.keys.removeRow(self.keys.currentRow())

    def bindings(self):
        values=[];seen=set()
        for row in range(self.keys.rowCount()):
            sequence=self.keys.cellWidget(row,1).keySequence().toString(QKeySequence.SequenceFormat.PortableText)
            if not sequence:raise ValueError("Chaque raccourci doit avoir une combinaison, ou être supprimé.")
            if sequence.casefold() in seen:raise ValueError("Deux actions ne peuvent pas utiliser le même raccourci.")
            seen.add(sequence.casefold());values.append({"action":self.keys.cellWidget(row,0).currentData(),"sequence":sequence})
        return values

    def save_binding_draft(self):
        try:self.binding_draft=self.bindings()
        except ValueError as error:QMessageBox.warning(self,"Raccourcis",str(error))

    def reset_bindings(self):
        self.keys.setRowCount(0)
        for item in self.binding_draft:self.add_binding(item["action"],item["sequence"])

    def build_progress_page(self):
        box=self.scroll_page();box.addStretch()
        self.status=QLabel("PRÉPARATION DE VOTRE COCKPIT");self.status.setObjectName("status");self.status.setWordWrap(True)
        self.progress=QProgressBar();self.progress.setRange(0,100)
        self.events=QTextBrowser();self.events.setMinimumHeight(160)
        box.addWidget(self.status);box.addWidget(self.progress);box.addWidget(self.events);box.addStretch()

    def advance(self):
        if self.stack.currentIndex()==0:
            try:
                validate_host(self.os_choice.currentData())
                email=self.email.text().strip()
                if email and not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+",email):raise ValueError("L’adresse e-mail renseignée est invalide.")
                if not self.username.text().strip():raise ValueError("Renseignez votre nom ou votre utilisateur.")
                self.identity={"username":self.username.text().strip()[:120],"email":email[:254],
                    "os":self.os_choice.currentData(),"share_experience":self.share.isChecked(),
                    "terms_version":TERMS_VERSION,"accepted_at":datetime.now(timezone.utc).isoformat()}
                save_profile(self.identity,asdict(self.settings))
            except (ValueError,OSError) as error:
                QMessageBox.warning(self,"Vérification",str(error));return
            self.stack.setCurrentIndex(1);self.step.setText("02 / VOTRE CONFIGURATION")
            self.next.setText("INSTALLER");self.next.setEnabled(True);self.cancel.setText("RETOUR")
        elif self.stack.currentIndex()==1:
            try:
                settings=replace(self.settings,position=self.position.currentData(),thickness=self.thickness.value(),
                    length_percent=self.length.value(),opacity=self.opacity.value(),auto_hide=self.retract_mode.currentData()=="auto",
                    retract_mode=self.retract_mode.currentData(),theme=self.theme.currentData(),
                    always_on_top=self.always_on_top.isChecked(),holo_enabled=self.holo_enabled.isChecked(),
                    autostart=self.autostart.isChecked(),shortcuts=self.bindings()).validate()
            except ValueError as error:QMessageBox.warning(self,"Configuration",str(error));return
            self.stack.setCurrentIndex(2);self.step.setText("03 / INSTALLATION & VÉRIFICATION")
            self.next.setEnabled(False);self.cancel.setEnabled(False)
            self.worker=InstallWorker(settings,self.identity,self.desktop.isChecked(),self.source_root,self.payload,self)
            self.worker.progress.connect(self.report_progress);self.worker.failed.connect(self.failed)
            self.worker.completed.connect(self.completed);self.worker.start()
        elif self.state:
            if os.getenv("NOVABAR_BOOTSTRAP"):
                self.accept();return
            subprocess.Popen([self.state["executable"],"--wait-for-pid",str(os.getpid())],stdin=subprocess.DEVNULL)
            self.accept()

    def report_progress(self,value,message):
        self.progress.setValue(value);self.status.setText(message);self.events.append(message)

    def completed(self,state):
        self.state=state;self.status.setText("✓ INSTALLATION RÉUSSIE")
        self.next.setText("OUVRIR NOVABAR");self.next.setEnabled(True)
        self.cancel.setText("FERMER");self.cancel.setEnabled(True)
        QMessageBox.information(self,"✓ Installation réussie","Le programme a passé son test de lancement.\nNovaBar va maintenant s’ouvrir.")
        # The worker has returned before closing its owning dialog.
        self.worker.wait();self.advance()

    def failed(self,message):
        self.status.setText("INSTALLATION INTERROMPUE");self.events.append(message)
        self.worker.wait();self.cancel.setText("FERMER");self.cancel.setEnabled(True)
        QMessageBox.warning(self,"Installation non terminée",message)

    def cancel_or_back(self):
        if self.stack.currentIndex()==1:
            self.stack.setCurrentIndex(0);self.step.setText("01 / IDENTITÉ & CONDITIONS")
            self.next.setText("VALIDER");self.cancel.setText("ANNULER");self.update_validation()
        else:self.reject()

    def reject(self):
        if self.worker and self.worker.isRunning():
            return
        super().reject()

    def closeEvent(self,event):
        if self.worker and self.worker.isRunning():event.ignore()
        else:super().closeEvent(event)

    def feedback(self):
        dialog=QDialog(self);dialog.setWindowTitle("Contacter · brouillon local")
        dialog.setStyleSheet(WIZARD_STYLE);box=QVBoxLayout(dialog)
        label=QLabel("Le service SMTP sera configuré plus tard.\nCe message n’est pas envoyé automatiquement.")
        box.addWidget(label)
        from PySide6.QtWidgets import QPlainTextEdit
        message=QPlainTextEdit();message.setPlaceholderText("Votre avis ou votre recommandation…");box.addWidget(message)
        button=QPushButton("Enregistrer le brouillon .eml")
        def save():
            from email.message import EmailMessage
            path,_=QFileDialog.getSaveFileName(dialog,"Brouillon d’avis","avis-novabar.eml","Message (*.eml)")
            if path:
                mail=EmailMessage();mail["Subject"]="Avis NovaBar";mail.set_content(message.toPlainText())
                Path(path).write_bytes(mail.as_bytes());dialog.accept()
        button.clicked.connect(save);box.addWidget(button);dialog.resize(500,320);dialog.exec()


def main():
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument("--preview");parser.add_argument("--verify-payload",action="store_true");args=parser.parse_args()
    if args.preview or args.verify_payload:os.environ.setdefault("QT_QPA_PLATFORM","offscreen")
    app=QApplication(sys.argv[:1]);app.setApplicationName("CYBER NEXUS HUD")
    payload=Path(getattr(sys,"_MEIPASS",Path(__file__).parent))/"payload"
    if args.verify_payload:
        import tempfile
        from .updates import extract_runtime
        from .install_engine import payload_executable, self_test
        archives=list(payload.glob("NovaBar-runtime-*.zip"))
        if len(archives)!=1:
            raise ValueError("Le lanceur doit contenir un runtime unique")
        with tempfile.TemporaryDirectory(prefix="nexus-verify-") as temporary:
            extract_runtime(archives[0],temporary)
            executable=payload_executable(temporary)
            if not executable:
                raise ValueError("Exécutable absent du lanceur")
            self_test(executable,Path(temporary)/"verify.log")
        return 0
    source=os.getenv("HEALTHBAR_SOURCE_ROOT") or str(Path(__file__).resolve().parents[2])
    initial=None
    if os.getenv("NOVABAR_BOOTSTRAP_SETTINGS"):
        import json
        initial=Settings(**json.loads(os.environ["NOVABAR_BOOTSTRAP_SETTINGS"])).validate()
    wizard=InstallerWizard(settings=initial,source_root=source,payload=payload if payload_executable_available(payload) else None)
    wizard.show()
    if args.preview:
        app.processEvents();wizard.grab().save(args.preview);wizard.header.timer.stop();return 0
    result=app.exec()
    return (0 if wizard.state else 1) if os.getenv("NOVABAR_BOOTSTRAP") else result


def payload_executable_available(path):
    from .install_engine import payload_executable
    return any(path.glob("NovaBar-runtime-*.zip")) or payload_executable(path) is not None
