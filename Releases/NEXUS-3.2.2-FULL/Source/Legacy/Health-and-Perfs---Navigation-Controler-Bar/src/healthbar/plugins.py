"""API v1: declarative packages only. No downloaded Python/JS is executed."""
import hashlib
import json
import re
import shutil
import tempfile
import zipfile
import stat
from datetime import datetime
from pathlib import Path, PurePosixPath
from .config import data_dir

API_VERSION = 2
MAX_PACKAGE = 16 * 1024 * 1024
MAX_UNPACKED = 32 * 1024 * 1024
SLOTS = ("cpu", "gpu", "ram", "storage", "fans", "network", "power")


def validate_manifest(raw):
    if not isinstance(raw, dict):
        raise ValueError("Le manifeste doit être un objet JSON")
    if type(raw.get("api_version")) is not int or raw["api_version"] not in (1, 2):
        raise ValueError("API de plugin incompatible")
    if not re.fullmatch(r"[a-z][a-z0-9-]{2,63}", str(raw.get("id", ""))):
        raise ValueError("Identifiant de plugin invalide")
    if not re.fullmatch(r"\d{1,6}\.\d{1,6}\.\d{1,6}", str(raw.get("version", ""))):
        raise ValueError("Version attendue : majeur.mineur.correctif")
    if raw.get("slot") not in SLOTS:
        raise ValueError("Emplacement inconnu")
    if not isinstance(raw.get("name"), str) or not 1 <= len(raw["name"]) <= 60:
        raise ValueError("Nom du plugin invalide")
    if raw.get("kind") != ("declarative" if raw["api_version"] == 1 else "builtin-sensor"):
        raise ValueError("Type d’extension non autorisé")
    v1 = {"id", "version", "name", "api_version", "slot", "kind", "description"}
    v2 = v1 | {"sensor_keys", "min_ram_mb", "requires", "permissions", "optional_permissions", "holo_view"}
    if set(raw) - (v1 if raw["api_version"] == 1 else v2):
        raise ValueError("Champs de manifeste non pris en charge")
    if raw["api_version"] == 2:
        if "holo_view" in raw and (raw.get("id") != "cpu-manager-viewer" or
                                   raw["slot"] != "cpu" or raw["holo_view"] != "cpu-core-matrix"):
            raise ValueError("Hologramme non reconnu par ce runtime")
        for key in ("sensor_keys", "requires", "permissions", "optional_permissions"):
            vals = raw.get(key, [])
            if not isinstance(vals, list) or len(vals) > 32 or any(
                not isinstance(v, str) or len(v) > 96 for v in vals
            ):
                raise ValueError("Liste de dépendances/capteurs invalide")
        mem = raw.get("min_ram_mb", 0)
        if type(mem) is not int or not 0 <= mem <= 65536:
            raise ValueError("Mémoire minimale invalide")
    if not isinstance(raw.get("description", ""), str) or len(raw.get("description", "")) > 400:
        raise ValueError("Description invalide")
    return raw


def version_tuple(value):
    return tuple(map(int, value.split(".")))


class PluginRegistry:
    def __init__(self, root=None):
        if root:
            self.root = Path(root)
        else:
            from .profiles import workspace_dir
            modern = workspace_dir() / "Plugins"
            legacy = data_dir() / "App/Plugins"
            if not legacy.exists():
                legacy = data_dir() / "plugins"
            if legacy.exists() and (not modern.exists() or not any(modern.iterdir())):
                modern.parent.mkdir(parents=True, exist_ok=True)
                with tempfile.TemporaryDirectory(dir=modern.parent, prefix=".migrate-") as temp:
                    stage = Path(temp) / "Plugins"
                    shutil.copytree(legacy, stage)
                    if modern.exists():
                        modern.rmdir()  # Only remove an empty destination created by the installer.
                    stage.rename(modern)
            self.root = modern

    def installed(self):
        if not self.root.exists():
            return []
        items = []
        for directory in sorted(self.root.iterdir()):
            if not directory.is_dir() or directory.name.startswith("."):
                continue
            try:
                manifest = validate_manifest(json.loads((directory / "manifest.json").read_text(encoding="utf-8")))
                state = json.loads((directory / "state.json").read_text(encoding="utf-8"))
                if manifest["id"] != directory.name:
                    continue
                items.append({**manifest, "enabled": state.get("enabled") is True})
            except (OSError, ValueError, TypeError, AttributeError):
                continue
        return items

    def inspect(self, archive):
        archive = Path(archive)
        if archive.stat().st_size > MAX_PACKAGE:
            raise ValueError("Paquet trop volumineux (2 Mio maximum)")
        with zipfile.ZipFile(archive) as package:
            members = package.infolist()
            names = [item.filename for item in members]
            if not members or len(members) > 150:
                raise ValueError("Nombre de fichiers invalide")
            seen = set()
            unpacked = 0
            for item in members:
                path = PurePosixPath(item.filename)
                if (path.is_absolute() or ".." in path.parts or "\\" in item.filename
                    or ":" in path.parts[0] or item.filename in seen
                    or stat.S_ISLNK(item.external_attr >> 16)):
                    raise ValueError("Chemin ou type de fichier interdit")
                seen.add(item.filename)
                unpacked += item.file_size
                if unpacked > MAX_UNPACKED or (item.file_size > 4096 and
                    item.file_size / max(1, item.compress_size) > 250):
                    raise ValueError("Archive décompressée excessive")
            if "manifest.json" not in seen or package.getinfo("manifest.json").file_size > 16384:
                raise ValueError("manifest.json absent ou trop grand")
            manifest = validate_manifest(json.loads(package.read("manifest.json")))
            if manifest["api_version"] == 1 and names != ["manifest.json"]:
                raise ValueError("Le paquet v1 doit contenir uniquement manifest.json")
            if manifest["api_version"] == 2 and not {
                "README.md", "DEPENDENCY.md", "VERSION.md", "install.sh"
            }.issubset(seen):
                raise ValueError("Documentation de l’extension incomplète")
        return manifest, hashlib.sha256(archive.read_bytes()).hexdigest()

    def install(self, archive, expected_digest):
        manifest, digest = self.inspect(archive)
        if digest != expected_digest:
            raise ValueError("Le paquet a changé depuis sa vérification")
        current = next((p for p in self.installed() if p["id"] == manifest["id"]), None)
        if current and version_tuple(manifest["version"]) <= version_tuple(current["version"]):
            raise ValueError("La mise à jour doit avoir une version supérieure")
        self.root.mkdir(parents=True, exist_ok=True)
        target = self.root / manifest["id"]
        backup = self.root / ("." + manifest["id"] + ".previous")
        if backup.exists():
            shutil.rmtree(backup)
        with tempfile.TemporaryDirectory(dir=self.root, prefix=".stage-") as staging:
            stage = Path(staging) / manifest["id"]
            stage.mkdir()
            if manifest["api_version"] == 2:
                with zipfile.ZipFile(archive) as package:
                    for member in package.infolist():
                        dest = stage.joinpath(*PurePosixPath(member.filename).parts)
                        if member.is_dir():
                            dest.mkdir(parents=True, exist_ok=True)
                        else:
                            dest.parent.mkdir(parents=True, exist_ok=True)
                            with package.open(member) as source, dest.open("wb") as output:
                                shutil.copyfileobj(source, output)
                            dest.chmod(0o600)  # Never execute untrusted install.sh.
            else:
                (stage / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
            # Updating preserves the user's activation choice. New packages start disabled.
            (stage / "state.json").write_text(json.dumps({"enabled": bool(current and current["enabled"]),
                                                          "sha256": digest}), encoding="utf-8")
            if target.exists():
                target.rename(backup)
            try:
                stage.rename(target)
            except OSError:
                if backup.exists():
                    backup.rename(target)
                raise
        self._report(manifest, digest)
        return manifest

    def _report(self, manifest, digest):
        folder = data_dir() / "App" / "Repports" / "Plugins"
        folder.mkdir(parents=True, exist_ok=True)
        indexes = [int(m.group(1)) for f in folder.glob("REPORT-*.md")
                   if (m := re.match(r"REPORT-(\d+)-", f.name))]
        index = max(indexes, default=0) + 1
        stamp = datetime.now().strftime("%Y.%m.%d")
        (folder / f"REPORT-{index:04d}-{stamp}.md").write_text(
            f"# Rapport plugin {index}\n\n"
            f"- Plugin : {manifest['name']}\n- Version : {manifest['version']}\n"
            f"- Statut : VALIDÉ\n- SHA256 : {digest}\n"
            "- Dépendances installées : aucune (inspection manuelle requise)\n"
            "- Code externe exécuté : non\n", encoding="utf-8")

    def set_enabled(self, plugin_id, enabled):
        item = next((p for p in self.installed() if p["id"] == plugin_id), None)
        if item is None:
            raise ValueError("Plugin introuvable")
        target = self.root / plugin_id / "state.json"
        state = json.loads(target.read_text(encoding="utf-8"))
        state["enabled"] = bool(enabled)
        temp = target.with_suffix(".tmp")
        temp.write_text(json.dumps(state), encoding="utf-8")
        temp.replace(target)

    def rollback(self, plugin_id):
        if not re.fullmatch(r"[a-z][a-z0-9-]{2,63}", plugin_id):
            raise ValueError("Identifiant invalide")
        target = self.root / plugin_id
        previous = self.root / ("." + plugin_id + ".previous")
        if not previous.is_dir():
            raise ValueError("Aucune version précédente")
        with tempfile.TemporaryDirectory(dir=self.root, prefix=".rollback-") as tmp:
            displaced = Path(tmp) / plugin_id
            target.rename(displaced)
            try:
                previous.rename(target)
            except OSError:
                displaced.rename(target)
                raise
