"""Declared installation targets and capability descriptions, never cross-install silently."""
import platform
import sys
from dataclasses import dataclass


@dataclass(frozen=True)
class Target:
    key: str
    label: str
    family: str
    available: bool
    details: str


TARGETS = (
    Target("windows10", "Windows 10 · 64 bits (1809+)", "win32", True, "Installation utilisateur • registre HKCU pour le démarrage • binaire x64."),
    Target("windows11", "Windows 11 · 64 bits", "win32", True, "Installation utilisateur • registre HKCU pour le démarrage • binaire x64."),
    Target("mint", "Linux Mint · XFCE", "linux", True, "Applications utilisateur • raccourcis XDG • Qt/XCB • compositeur pour la transparence."),
    Target("ubuntu", "Ubuntu Desktop", "linux", True, "Applications utilisateur • démarrage XDG • sous Wayland, ancrage de la barre à vérifier."),
    Target("bazzite", "Bazzite · Desktop (expérimental)", "linux", True, "Installation dans le dossier personnel, sans modifier le système immuable. XWayland si disponible ; overlay et raccourcis Wayland à vérifier ; pas de prise en charge du mode Gaming."),
    Target("macos", "macOS récent · 12 ou supérieur", "darwin", True, "Application native Intel ou Apple Silicon selon le paquet • LaunchAgent utilisateur • permissions d’accessibilité pour les raccourcis."),
    Target("high-sierra", "macOS High Sierra · 10.13 (port legacy requis)", "darwin", False, "Non installable avec Qt 6.8. Cette cible nécessite un port legacy et un paquet dédiés ; choisir une autre entrée ne rend pas ce Mac compatible."),
)


def detected_target():
    if sys.platform == "win32":
        return "windows11" if int(platform.version().split(".")[-1]) >= 22000 else "windows10"
    if sys.platform == "darwin":
        major = int((platform.mac_ver()[0] or "0").split(".")[0])
        return "macos" if major >= 12 else "high-sierra"
    try:
        info = platform.freedesktop_os_release()
    except OSError:
        info = {}
    identity = (info.get("ID", "") + info.get("NAME", "")).lower()
    return "bazzite" if "bazzite" in identity else "mint" if "mint" in identity else "ubuntu"


def target_by_key(key):
    return next(t for t in TARGETS if t.key == key)


def validate_host(key):
    target = target_by_key(key)
    family = sys.platform if sys.platform in ("win32", "darwin") else "linux"
    if not target.available:
        raise ValueError(target.details)
    if target.family != family:
        raise ValueError("Ce lanceur installe uniquement pour le système qui l’exécute. Utilisez le paquet du système choisi.")
    if family == "darwin" and int((platform.mac_ver()[0] or "0").split(".")[0]) < 12:
        raise ValueError("Ce Mac nécessite un paquet legacy : macOS 12 minimum pour cette édition.")
    machine = platform.machine().lower()
    if machine not in ("x86_64", "amd64", "arm64", "aarch64"):
        raise ValueError("Architecture non prise en charge par cette édition.")
    return target
