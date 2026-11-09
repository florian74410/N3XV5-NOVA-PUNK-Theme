"""Safe, user-editable GitHub plugin sources and ZIP catalogue (no git checkout, no shell)."""
import hashlib
import json
import os
import re
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from .profiles import workspace_dir
from .plugins import MAX_PACKAGE, version_tuple

REPO_URL = re.compile(r"^https://github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+?)(?:\.git)?/?$")
ID_PATTERN = re.compile(r"^[a-z][a-z0-9-]{2,63}$")
VERSIONED_ZIP = re.compile(r"^([a-z][a-z0-9-]{2,63})-v(\d{1,6}\.\d{1,6}\.\d{1,6})\.zip$")
ALLOWED_HOSTS = {"api.github.com", "raw.githubusercontent.com"}
MAX_SOURCE_COUNT = 16
MAX_LIST_BYTES = 3 * 1024 * 1024

class StrictGitHubRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        target = urllib.parse.urlparse(newurl)
        if target.scheme != "https" or target.hostname not in ALLOWED_HOSTS:
            raise ValueError("Redirection vers une destination non autorisée")
        return super().redirect_request(req, fp, code, msg, headers, newurl)

_OPENER = urllib.request.build_opener(StrictGitHubRedirects())

def request_bytes(url, size_limit, progress=None):
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in ALLOWED_HOSTS:
        raise ValueError("Seuls les hôtes GitHub officiels sont autorisés")
    request = urllib.request.Request(url, headers={
        "User-Agent": "NovaBar-Plugin-Manager/0.3",
        "Accept": "application/vnd.github+json" if parsed.hostname == "api.github.com"
                  else "application/octet-stream"
    })
    with _OPENER.open(request, timeout=15) as response:
        total = 0
        chunks = []
        while True:
            data = response.read(min(65536, size_limit + 1 - total))
            if not data:
                break
            total += len(data)
            if total > size_limit:
                raise ValueError("Fichier distant trop volumineux")
            chunks.append(data)
            if progress:
                progress(total)
        return b"".join(chunks)

def normalized_source(name, url, branch="main", folder="Plugins", enabled=True):
    """Reject protocols other than HTTPS and references that can escape the chosen folder."""
    match = REPO_URL.fullmatch(str(url).strip())
    if not match:
        raise ValueError("URL attendue : https://github.com/proprietaire/depot")
    owner, repo = match.groups()
    if not isinstance(name, str) or not 1 <= len(name.strip()) <= 60:
        raise ValueError("Nom de source invalide")
    if not isinstance(branch, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._/-]{0,120}", branch) or ".." in branch or "//" in branch:
        raise ValueError("Branche invalide")
    folder = str(folder).strip("/")
    if not folder or len(folder) > 180 or "\\" in folder or any(
        not re.fullmatch(r"[A-Za-z0-9_.-]+", segment) or segment in (".", "..")
        for segment in folder.split("/")):
        raise ValueError("Dossier du dépôt invalide")
    if type(enabled) is not bool:
        raise ValueError("État de la source invalide")
    return {"name": name.strip(), "url": f"https://github.com/{owner}/{repo}",
            "branch": branch, "folder": folder, "enabled": enabled}

DEFAULT_SOURCE = normalized_source(
    "NovaBar Official", "https://github.com/florian74410/Health-and-Perfs---Navigation-Controler-Bar",
    "main", "Plugins")

class SourceStore:
    def __init__(self, path=None):
        self.path = Path(path) if path else workspace_dir() / "App" / "Settings" / "plugin_sources.json"

    def load(self):
        if not self.path.exists():
            return [DEFAULT_SOURCE.copy()]
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        if not isinstance(raw, list) or len(raw) > MAX_SOURCE_COUNT:
            raise ValueError("Configuration des sources corrompue")
        return [normalized_source(**source) for source in raw]

    def save(self, sources):
        if not isinstance(sources, list) or len(sources) > MAX_SOURCE_COUNT:
            raise ValueError("Nombre de sources invalide")
        verified = [normalized_source(**item) for item in sources]
        keys = [(i["url"].lower(), i["branch"], i["folder"]) for i in verified]
        if len(set(keys)) != len(keys):
            raise ValueError("Source en double")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(prefix=".sources-", suffix=".json", dir=self.path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as out:
                json.dump(verified, out, ensure_ascii=False, indent=2)
            os.replace(tmp, self.path)
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)

def fetch_catalog(sources):
    """List one latest ZIP per plugin ID across user-selected GitHub sources."""
    latest = {}
    failures = []
    for source in sources:
        if not source["enabled"]:
            continue
        try:
            checked = normalized_source(**source)
            owner, repo = REPO_URL.fullmatch(checked["url"]).groups()
            path = urllib.parse.quote(checked["branch"], safe="")
            api = f"https://api.github.com/repos/{owner}/{repo}/git/trees/{path}?recursive=1"
            tree = json.loads(request_bytes(api, MAX_LIST_BYTES))
            if tree.get("truncated") is True:
                raise ValueError("Arbre Git incomplet, dépôt trop volumineux")
            if not isinstance(tree.get("tree"), list):
                raise ValueError("Catalogue GitHub illisible")
            prefix = checked["folder"] + "/"
            for record in tree["tree"]:
                path = record.get("path", "")
                if record.get("type") != "blob" or not path.startswith(prefix):
                    continue
                filename = path[len(prefix):]
                if "/" in filename:
                    continue
                match = VERSIONED_ZIP.fullmatch(filename)
                if not match:
                    continue
                ident, version = match.groups()
                if record.get("size", MAX_PACKAGE+1) > MAX_PACKAGE:
                    continue
                blobsha = record.get("sha")
                if not isinstance(blobsha,str) or not re.fullmatch(r"[0-9a-f]{40}",blobsha):
                    continue
                encoded_branch = urllib.parse.quote(checked["branch"], safe="")
                encoded_folder = "/".join(urllib.parse.quote(x, safe="") for x in checked["folder"].split("/"))
                url = f"https://raw.githubusercontent.com/{owner}/{repo}/{encoded_branch}/{encoded_folder}/{filename}"
                candidate = {"id": ident, "version": version, "source": checked["name"],
                             "repo": checked["url"], "filename": filename, "url": url,
                             "blob_sha": blobsha}
                existing = latest.get(ident)
                if existing is None or version_tuple(version) > version_tuple(existing["version"]):
                    latest[ident] = candidate
        except (ValueError, OSError, urllib.error.URLError, json.JSONDecodeError, KeyError) as error:
            failures.append(f"{source.get('name', 'Source')} : {error}")
    return latest, failures

def download_package(entry, destination, progress=None):
    """Compare downloaded ZIP with immutable Git object hash from the catalogue."""
    data = request_bytes(entry["url"], MAX_PACKAGE, progress)
    git_hash = hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\x00" + data).hexdigest()
    if git_hash != entry["blob_sha"]:
        raise ValueError("Le ZIP a changé depuis la consultation du dépôt : actualisez les sources")
    target = Path(destination)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    return target, hashlib.sha256(data).hexdigest()
