"""Per-user preferences, atomically persisted outside the installation."""
import json
import os
import getpass
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path


def data_dir():
    override = os.getenv("HEALTHBAR_DATA_DIR")
    if override:
        return Path(override)
    if sys.platform == "win32":
        return Path(os.getenv("APPDATA", str(Path.home()))) / "HealthPerfsBar"
    if sys.platform == "darwin":
        return Path.home() / "Library/Application Support/HealthPerfsBar"
    return Path(os.getenv("XDG_CONFIG_HOME", str(Path.home() / ".config"))) / "health-perfs-bar"


@dataclass
class Settings:
    position: str = "top"
    thickness: int = 72
    layout_revision: int = 1
    opacity: int = 88
    auto_hide: bool = True
    retract_mode: str = ""
    always_on_top: bool = True
    holo_enabled: bool = True
    # Any combination of the three panels may be enabled.
    hud_enabled: bool = True
    dock_left_enabled: bool = True
    dock_right_enabled: bool = True
    bottom_dock_enabled: bool = sys.platform.startswith("linux")
    bottom_dock_height: int = 84
    bottom_tabs_max: int = 3
    bottom_nav_opacity: int = 55
    bottom_pinned_apps: list | None = None
    dock_aliases: dict = field(default_factory=dict)
    top_reserved: bool = True
    top_hover_ms: int = 1000
    top_trigger_px: int = 10
    turbo_auth_enabled: bool = True
    dock_left_kind: str = "folders"
    dock_right_kind: str = "apps"
    # None = auto-discover defaults, [] = intentionally empty dock.
    dock_folder_paths: list | None = None
    dock_app_paths: list | None = None
    hide_seconds: int = 15
    autostart: bool = False
    configured: bool = False
    screen: int = 0
    length_percent: int = 100
    alignment: str = "center"
    refresh_seconds: int = 2
    shell_dir: str = ""
    theme: str = "redblack-0822"
    slot_order: list = None
    hidden_modules: list = field(default_factory=lambda: ["power"])
    xfce_skin_enabled: bool = False
    xfce_skin_offer_done: bool = False  # single opt-in offer for upgraded XFCE setups
    xfce_skin_delay_seconds: int = 10
    xfce_skin_scale_percent: int = 175
    xfce_skin_fx_intensity: int = 72
    shortcuts: list = field(default_factory=lambda: [{"action": "toggle", "sequence": "Ctrl+B"}])

    def validate(self):
        if self.position not in ("top", "bottom", "right", "left") or self.alignment not in ("left", "center", "right"):
            raise ValueError("Position invalide")
        for name, lo, hi in (("thickness", 50, 150), ("opacity", 0, 100), ("layout_revision", 1, 1),
                             ("hide_seconds", 3, 120), ("screen", 0, 64),
                             ("length_percent", 25, 100), ("refresh_seconds", 1, 30),
                             ("bottom_dock_height", 62, 130), ("bottom_tabs_max", 1, 3),
                             ("bottom_nav_opacity", 10, 100),
                             ("top_hover_ms", 500, 4000), ("top_trigger_px", 5, 20)):
            value = getattr(self, name)
            if type(value) is not int or not lo <= value <= hi:
                raise ValueError(f"Préférence invalide : {name}")
        for name in ("autostart", "configured", "auto_hide", "top_reserved", "turbo_auth_enabled"):
            if type(getattr(self, name)) is not bool:
                raise ValueError(f"Préférence invalide : {name}")
        if not isinstance(self.shell_dir, str) or len(self.shell_dir) > 1024 or "\x00" in self.shell_dir:
            raise ValueError("Dossier des scripts invalide")
        if not self.retract_mode:
            self.retract_mode = "auto" if self.auto_hide else "manual"
        if self.retract_mode not in ("always", "auto", "manual"):
            raise ValueError("Mode de rétractation invalide")
        self.auto_hide = self.retract_mode == "auto"
        if type(self.always_on_top) is not bool or type(self.holo_enabled) is not bool:
            raise ValueError("Option affichage invalide")
        for name in ("hud_enabled", "dock_left_enabled", "dock_right_enabled",
                     "xfce_skin_enabled", "xfce_skin_offer_done", "bottom_dock_enabled"):
            if type(getattr(self, name)) is not bool:
                raise ValueError(f"Activation de barre invalide : {name}")
        if not (self.hud_enabled or self.dock_left_enabled or self.dock_right_enabled or self.xfce_skin_enabled or (self.bottom_dock_enabled and sys.platform.startswith("linux"))):
            raise ValueError("Activer au moins une barre NovaBar ou le panneau XFCE")
        if (type(self.xfce_skin_delay_seconds) is not int or
                not 1 <= self.xfce_skin_delay_seconds <= 120 or
                type(self.xfce_skin_scale_percent) is not int or
                not 100 <= self.xfce_skin_scale_percent <= 200 or
                type(self.xfce_skin_fx_intensity) is not int or
                not 0 <= self.xfce_skin_fx_intensity <= 100):
            raise ValueError("Délai ou intensité des effets XFCE invalide")
        if sorted((self.dock_left_kind, self.dock_right_kind)) != ["apps", "folders"]:
            raise ValueError("Un dock Dossiers et un dock Applications sont requis")
        for key in ("dock_folder_paths", "dock_app_paths", "bottom_pinned_apps"):
            values = getattr(self, key)
            if values is None:
                continue
            if not isinstance(values, list) or len(values) > 128 or any(
                    not isinstance(p, str) or len(p) > 2048 or "\\x00" in p for p in values):
                raise ValueError(f"Favoris de dock invalides : {key}")
        if (not isinstance(self.dock_aliases,dict) or len(self.dock_aliases)>256 or
                any(not isinstance(k,str) or len(k)>2048 or "\\x00" in k or
                    not isinstance(v,str) or not 1<=len(v)<=80 or
                    any(ord(c)<32 for c in v) for k,v in self.dock_aliases.items())):
            raise ValueError("Alias des raccourcis invalides")
        if self.theme not in ("redblack-0822", "cyber-futuriste", "blue-neon", "green-matrix", "red-blood"):
            raise ValueError("Thème non reconnu")
        expected = ["cpu", "gpu", "ram", "storage", "fans", "network"]
        available = expected + ["power"]
        if self.slot_order is None:
            self.slot_order = expected.copy()
        if (not isinstance(self.slot_order, list)
            or sorted(self.slot_order) not in (sorted(expected), sorted(available))):
            raise ValueError("Disposition des modules invalide")
        if (not isinstance(self.hidden_modules, list)
            or len(set(self.hidden_modules)) != len(self.hidden_modules)
            or any(slot not in available for slot in self.hidden_modules)):
            raise ValueError("Liste de modules masqués invalide")
        if not any(slot not in self.hidden_modules for slot in available):
            raise ValueError("Au moins un plugin doit rester affiché")
        if not isinstance(self.shortcuts, list) or len(self.shortcuts) > 20:
            raise ValueError("Liste de raccourcis invalide")
        seen = set()
        for binding in self.shortcuts:
            if not isinstance(binding, dict) or binding.get("action") not in ("toggle", "expand", "preferences"):
                raise ValueError("Action de raccourci invalide")
            sequence = binding.get("sequence", "")
            if not isinstance(sequence, str) or not 1 <= len(sequence) <= 80 or "," in sequence:
                raise ValueError("Combinaison de raccourci invalide")
            if sequence.casefold() in seen:
                raise ValueError("Raccourci en double")
            seen.add(sequence.casefold())
        return self

    @classmethod
    def load(cls):
        try:
            raw = json.loads((data_dir() / "settings.json").read_text(encoding="utf-8"))
            if raw.get("theme") in ("blackred-studio","blackred-neon"):
                # Keep every existing favorite, dock and hardware preference.
                raw["theme"]="redblack-0822"
            if "layout_revision" not in raw and raw.get("thickness", 200) == 200:
                raw["thickness"] = 72
            if type(raw.get("thickness")) is int:
                raw["thickness"] = max(50,min(150,raw["thickness"]))
            return cls(**{k: v for k, v in raw.items() if k in cls.__dataclass_fields__}).validate()
        except (OSError, ValueError, TypeError, AttributeError):
            return cls()

    def save(self):
        self.validate()
        root = data_dir()
        root.mkdir(parents=True, exist_ok=True)
        tmp = root / "settings.tmp"
        tmp.write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")
        tmp.replace(root / "settings.json")
        username = re.sub(r"[^A-Za-z0-9_-]+", "_", getpass.getuser())[:48] or "Default"
        profile = root / "App" / "Profils" / username
        profile.mkdir(parents=True, exist_ok=True)
        details = [
            "# NovaBar Profile.md",
            "",
            f"- Position: {self.position}",
            f"- Screen: {self.screen}",
            f"- Longueur: {self.length_percent}%",
            f"- Épaisseur: {self.thickness}px",
            f"- Alignement: {self.alignment}",
            f"- Opacité: {self.opacity}%",
            f"- Délai de rétractation: {self.hide_seconds}s",
            f"- Démarrage automatique: {self.autostart}",
            f"- NovaBar en haut: {self.hud_enabled}",
            f"- Dock gauche: {self.dock_left_enabled} ({self.dock_left_kind})",
            f"- Dock droit: {self.dock_right_enabled} ({self.dock_right_kind})",
            f"- Thème: {self.theme}",
            f"- Modules: {', '.join(self.slot_order)}",
            f"- Modules masqués: {', '.join(self.hidden_modules)}",
            f"- Habillage XFCE: {self.xfce_skin_enabled}",
            f"- Repli XFCE: {self.xfce_skin_delay_seconds}s",
            f"- Épaisseur XFCE: {self.xfce_skin_scale_percent}% de l'originale",
            "",
            "Le fichier settings.json est la source des préférences actives.",
        ]
        (profile / "Profile.md").write_text("\n".join(details) + "\n", encoding="utf-8")
        from .profiles import mirror_preferences
        mirror_preferences(asdict(self))
