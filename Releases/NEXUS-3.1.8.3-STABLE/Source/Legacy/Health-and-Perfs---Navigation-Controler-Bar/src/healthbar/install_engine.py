"""Versioned per-user installs. Test staged binary before changing the active installation."""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import asdict
from pathlib import Path
from . import __version__
from .config import data_dir
from .profiles import ensure_workspace, save_profile, write_json
from .platforms import validate_host
from .autostart import desktop_quote


def install_root():
    if os.getenv("HEALTHBAR_INSTALL_ROOT"):
        return Path(os.environ["HEALTHBAR_INSTALL_ROOT"])
    if os.getenv("HEALTHBAR_DATA_DIR"):
        return data_dir() / "runtime"
    if sys.platform == "win32":
        return Path(os.getenv("LOCALAPPDATA", str(Path.home()))) / "NovaBar"
    if sys.platform == "darwin":
        return Path.home() / "Library/Application Support/NovaBar/runtime"
    return Path.home() / ".local/share/novabar"


def read_installed_state(root=None):
    """Read the existing installation without touching its settings or executables."""
    root = Path(root) if root is not None else install_root()
    path = root / "installation.json"
    if not path.exists():
        return None
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise ValueError("Métadonnées d'installation existantes illisibles : aucune suppression autorisée") from error
    if not isinstance(state, dict) or not isinstance(state.get("version"), str):
        raise ValueError("Métadonnées d'installation existantes invalides : aucune suppression autorisée")
    return state


def version_tuple(value):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+(?:\.[0-9]+)?", value):
        return None
    return tuple(map(int, value.split(".")))


def cleanup_obsolete_runtimes(root, active_version, notify=None):
    """Remove ONLY old app-owned version folders after the new version is activated.

    Never scan Documents/NovaBar, plugins, profiles, shortcuts or arbitrary legacy paths.
    A busy executable (e.g. on Windows) is kept and reported for manual retry.
    """
    root = Path(root)
    state = read_installed_state(root)
    if not state or state.get("version") != active_version:
        return []
    active = version_tuple(active_version)
    versions = root / "versions"
    if active is None or not versions.is_dir() or versions.is_symlink():
        return []
    removed = []
    for entry in versions.iterdir():
        old = version_tuple(entry.name)
        if old is None or old >= active or entry.is_symlink() or not entry.is_dir():
            continue
        if entry.resolve().parent != versions.resolve():
            continue
        try:
            shutil.rmtree(entry)
            removed.append(entry.name)
        except OSError:
            if notify:
                notify(f"Ancienne version {entry.name} encore utilisée : suppression différée")
    return removed


def payload_executable(root):
    root = Path(root)
    candidates = [root / "HealthPerfsBar.app/Contents/MacOS/HealthPerfsBar",
                  root / "HealthPerfsBar/HealthPerfsBar.exe",
                  root / "HealthPerfsBar/HealthPerfsBar"]
    return next((p for p in candidates if p.is_file()), None)


def run_logged(command, report, env=None, timeout=900):
    with Path(report).open("ab") as output:
        result = subprocess.run([str(v) for v in command], stdout=output, stderr=subprocess.STDOUT,
                                stdin=subprocess.DEVNULL, env=env, timeout=timeout,
                                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0)
    if result.returncode:
        raise RuntimeError(f"Une étape a échoué (code {result.returncode}). Rapport : {report}")


def self_test(executable, report, expected_version=__version__):
    # Real process, isolated data. No autostart, sensors, tray or startup UI in self-test.
    with tempfile.TemporaryDirectory(prefix="novabar-test-") as temp:
        from .system_env import native_env
        env=dict(native_env(), QT_QPA_PLATFORM="offscreen", HEALTHBAR_DATA_DIR=temp,PYINSTALLER_RESET_ENVIRONMENT="1")
        run_logged([executable, "--self-test", "--expect-version", expected_version], report, env=env, timeout=35)


def write_shortcuts(executable, desktop=False, root=None):
    root = Path(root) if root else install_root()
    command = [str(executable)]
    if sys.platform == "darwin":
        app = executable.parents[2]
        applications = Path.home() / "Applications"
        applications.mkdir(parents=True, exist_ok=True)
        link = applications / "NovaBar.app"
        if link.is_symlink():
            link.unlink()
        elif link.exists():
            raise OSError("Une application ~/Applications/NovaBar.app existe déjà et n’a pas été remplacée.")
        link.symlink_to(app, target_is_directory=True)
        if desktop:
            from PySide6.QtCore import QStandardPaths
            folder=Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DesktopLocation))
            folder.mkdir(parents=True,exist_ok=True)
            link=folder/"NovaBar.app"
            if link.is_symlink(): link.unlink()
            if not link.exists(): link.symlink_to(app,target_is_directory=True)
    elif sys.platform == "win32":
        programs=Path(os.getenv("APPDATA",str(Path.home()))) / "Microsoft/Windows/Start Menu/Programs"
        paths=[programs/"NovaBar.lnk"]
        if desktop:
            from PySide6.QtCore import QStandardPaths
            paths.append(Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DesktopLocation))/"NovaBar.lnk")
        for link in paths:
            link.parent.mkdir(parents=True,exist_ok=True)
            env=dict(os.environ,NOVABAR_LINK=str(link),NOVABAR_EXE=str(executable))
            subprocess.run(["powershell.exe","-NoProfile","-Command",
                "$w=New-Object -ComObject WScript.Shell; $s=$w.CreateShortcut($env:NOVABAR_LINK); "
                "$s.TargetPath=$env:NOVABAR_EXE; $s.Save()"],env=env,check=True,timeout=30,
                creationflags=subprocess.CREATE_NO_WINDOW)
    else:
        applications=Path(os.getenv("XDG_DATA_HOME",str(Path.home()/".local/share")))/"applications"
        paths=[applications/"io.github.florian74410.NovaBar.desktop"]
        if desktop:
            from PySide6.QtCore import QStandardPaths
            paths.append(Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DesktopLocation))/"NovaBar.desktop")
        for link in paths:
            link.parent.mkdir(parents=True,exist_ok=True)
            link.write_text("[Desktop Entry]\nType=Application\nName=NovaBar\nExec="+desktop_quote(command[0])+
                            "\nTerminal=false\nCategories=System;Monitor;\n",encoding="utf-8")
            link.chmod(0o755)
    if sys.platform.startswith("linux"):
        # Preserve pinned legacy launchers, but show only the official desktop ID.
        legacy=applications/"novabar.desktop"
        legacy.write_text("[Desktop Entry]\nType=Application\nName=NovaBar\nNoDisplay=true\nExec="+
                          desktop_quote(command[0])+"\nTerminal=false\n",encoding="utf-8")
    return command


def refresh_active_shortcuts():
    """Migrate shortcuts made by older updaters after their first successful launch."""
    if not sys.platform.startswith("linux") or not getattr(sys,"frozen",False):return
    state=read_installed_state()
    if state and Path(state.get("executable","")).resolve()==Path(sys.executable).resolve():
        write_shortcuts(Path(sys.executable),state.get("desktop_shortcut",False))


def activate(executable, settings, identity, desktop, root=None, release_version=None):
    from .autostart import set_enabled
    root = Path(root) if root else install_root()
    root.mkdir(parents=True,exist_ok=True)
    state_path=root/"installation.json"
    old_state=read_installed_state(root)
    previous=({key:old_state.get(key) for key in ("version","executable","desktop_shortcut")}
              if old_state else None)
    # Initialize the official plugin source only once; never overwrite user-added repositories.
    from .plugin_sources import SourceStore, DEFAULT_SOURCE
    sources = SourceStore()
    if not sources.path.exists():
        sources.save([DEFAULT_SOURCE.copy()])
    state={"version":release_version or __version__,"executable":str(executable),"desktop_shortcut":desktop,
           "previous":previous}
    from .profiles import workspace_dir, profile_id
    old_settings=__import__("healthbar.config",fromlist=["Settings"]).Settings.load()
    key=profile_id()+".json"
    paths=[data_dir()/"settings.json", data_dir()/"active-profile",
           workspace_dir()/"App/Profiles"/key, workspace_dir()/"Profiles"/key]
    snapshots={path:path.read_bytes() if path.is_file() else None for path in paths}
    try:
        command=write_shortcuts(executable,desktop,root)
        settings.configured=True
        settings.save()
        save_profile(identity,asdict(settings),state)
        set_enabled(settings.autostart, command=command)
        write_json(state_path,state)
    except Exception:
        for path,content in snapshots.items():
            if content is None:path.unlink(missing_ok=True)
            else:
                path.parent.mkdir(parents=True,exist_ok=True)
                path.write_bytes(content)
        if previous and Path(previous["executable"]).is_file():
            write_shortcuts(Path(previous["executable"]),previous.get("desktop_shortcut",False),root)
            set_enabled(old_settings.autostart,command=[previous["executable"]])
        else:
            set_enabled(False)
        raise
    return state


def install(settings, identity, desktop, progress, source_root=None, payload=None):
    validate_host(identity["os"])
    workspace=ensure_workspace()
    report=workspace/"Reports/installation.log"
    root=install_root();root.mkdir(parents=True,exist_ok=True)
    existing = read_installed_state(root)
    old_version = existing.get("version") if existing else None
    if old_version and version_tuple(old_version) and version_tuple(old_version) > version_tuple(__version__):
        raise ValueError("Un runtime NovaBar plus récent est installé : rétrogradation refusée")
    if old_version and old_version != __version__:
        progress(5, f"Ancienne version NovaBar {old_version} détectée · données préservées")
    target=root/"versions"/__version__
    if target.exists():
        # Reconfiguration does not reinstall a healthy version.
        executable=payload_executable(target)
        if executable:
            progress(35,"Version déjà installée · vérification")
            self_test(executable,report)
            progress(85,"Enregistrement du profil et des raccourcis")
            state=activate(executable,settings,identity,desktop,root)
            removed=cleanup_obsolete_runtimes(root,__version__,lambda m:progress(94,m))
            if removed:
                progress(96,"Ancien runtime supprimé : "+", ".join(removed))
            progress(100,"Installation vérifiée")
            return state
        raise OSError("Cette version existe mais est incomplète. Consultez le dossier runtime avant de réessayer.")
    with tempfile.TemporaryDirectory(prefix=".install-",dir=root) as temporary:
        temporary=Path(temporary);stage=temporary/"stage";stage.mkdir()
        if payload:
            progress(15,"Préparation du paquet natif pour ce système")
            archives=list(Path(payload).glob("NovaBar-runtime-*.zip"))
            if archives:
                if len(archives) != 1:
                    raise ValueError("Le lanceur contient plusieurs runtimes ambigus")
                from .updates import extract_runtime
                extract_runtime(archives[0],stage)
            else:
                original=payload_executable(payload)
                if not original:
                    raise ValueError("Exécutable natif manquant dans le lanceur")
                component=original.relative_to(payload).parts[0]
                shutil.copytree(Path(payload)/component,stage/component,symlinks=True)
        else:
            source_root=Path(source_root or "")
            if not (source_root/"pyproject.toml").is_file():
                raise ValueError("Sources de compilation introuvables. Utilisez le lanceur natif ou lancez scripts/install.py depuis le dépôt.")
            if getattr(sys,"frozen",False):
                raise ValueError("Ce lanceur autonome ne contient pas de paquet natif valide.")
            progress(10,"Création de l’environnement de compilation privé")
            venv_root=temporary/"compiler"
            run_logged([sys.executable,"-m","venv",venv_root],report)
            python=venv_root/("Scripts/python.exe" if sys.platform=="win32" else "bin/python")
            progress(25,"Installation des dépendances dans l’environnement privé")
            run_logged([python,"-m","pip","install",source_root,"pyinstaller==6.16.0"],report)
            progress(45,"Compilation de l’application pour votre système")
            run_logged([python,"-m","PyInstaller","--noconfirm","--windowed","--name","HealthPerfsBar",
                        "--paths",source_root/"src","--distpath",stage,"--workpath",temporary/"build",
                        "--specpath",temporary,"--add-data",str(source_root/"src/healthbar/assets")+os.pathsep+"healthbar/assets","--osx-bundle-identifier","com.healthperfs.bar",
                        source_root/"scripts/entrypoint.py"],report)
        executable=payload_executable(stage)
        if not executable:
            raise ValueError("Le paquet ne contient pas l’exécutable attendu")
        progress(70,"Test de lancement du programme compilé")
        self_test(executable,report)
        relative=executable.relative_to(stage)
        progress(82,"Installation permanente de la version vérifiée")
        target.parent.mkdir(parents=True,exist_ok=True)
        stage.rename(target)
        try:
            state=activate(target/relative,settings,identity,desktop,root)
            # Delete the old runtime ONLY after staging, self-test and successful switch.
            removed=cleanup_obsolete_runtimes(root,__version__,lambda m:progress(94,m))
            if removed:
                progress(96,"Ancien runtime supprimé : "+", ".join(removed))
        except Exception:
            # Keep the tested payload for diagnostics/reconfiguration, never delete user data.
            raise
    progress(100,"Installation réussie · profil et lancement prêts")
    return state
