"""User-visible Documents workspace, independent from versioned executables."""
import getpass
import json
import os
import re
from pathlib import Path
from .config import data_dir


def workspace_dir():
    override = os.getenv("HEALTHBAR_DOCUMENTS_DIR")
    if override:
        return Path(override) / "NovaBar"
    if os.getenv("HEALTHBAR_DATA_DIR"):
        return data_dir() / "Documents/NovaBar"
    from PySide6.QtCore import QStandardPaths
    documents = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DocumentsLocation)
    return Path(documents or str(Path.home() / "Documents")) / "NovaBar"


def ensure_workspace():
    root = workspace_dir()
    for name in ("App/Profiles", "App/Settings", "Profiles", "Themes", "Plugins", "Reports", "Updates"):
        (root / name).mkdir(parents=True, exist_ok=True)
    return root


def profile_id(username=None):
    return re.sub(r"[^A-Za-z0-9_-]+", "_", username or getpass.getuser())[:48] or "Default"


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")
    try:
        temp.chmod(0o600)
    except OSError:
        pass
    temp.replace(path)


def current_profile():
    try:
        key = (data_dir() / "active-profile").read_text(encoding="utf-8").strip()
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,48}", key):
            raise ValueError("Identifiant de profil invalide")
    except (OSError, ValueError):
        key = profile_id()
    return key


def save_profile(identity, preferences, installation=None):
    root = ensure_workspace()
    key = profile_id()  # OS account identity, not user-entered paths or email.
    path = root / "App/Profiles" / (key + ".json")
    if installation is None and path.is_file():
        try:
            installation = json.loads(path.read_text(encoding="utf-8")).get("installation", {})
        except (ValueError, OSError, AttributeError):
            installation = {}
    record = {"schema_version": 1, "identity": identity, "preferences": preferences,
              "installation": installation or {}}
    write_json(path, record)
    write_json(root / "Profiles" / path.name, record)
    data_dir().mkdir(parents=True, exist_ok=True)
    (data_dir() / "active-profile").write_text(key, encoding="utf-8")
    return path


def mirror_preferences(preferences):
    root = workspace_dir()
    path = root / "App/Profiles" / (current_profile() + ".json")
    if not path.is_file():
        return
    record = json.loads(path.read_text(encoding="utf-8"))
    record["preferences"] = preferences
    write_json(path, record)
    write_json(root / "Profiles" / path.name, record)
