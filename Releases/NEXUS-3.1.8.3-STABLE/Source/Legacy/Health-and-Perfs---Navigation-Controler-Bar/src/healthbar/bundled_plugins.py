"""Seed first-party data-only plugins on fresh installs; never overwrite extensions."""
from pathlib import Path
from .config import data_dir
from .plugins import PluginRegistry

def seed_bundled_plugins(settings):
    marker=data_dir()/'bundled-plugins-v1'
    if marker.exists():return
    registry=PluginRegistry()
    if registry.installed():
        # Existing activation choices and versions remain authoritative.
        marker.parent.mkdir(parents=True,exist_ok=True);marker.write_text('existing plugins preserved\n');return
    archives=sorted((Path(__file__).parent/'assets/plugins').glob('*.zip'))
    if not archives:return  # Source checkout: plugins are installed via the manager.
    for archive in archives:
        manifest,digest=registry.inspect(archive)
        registry.install(archive,digest)
        registry.set_enabled(manifest['id'],settings.holo_enabled)
    marker.parent.mkdir(parents=True,exist_ok=True);marker.write_text('seeded\n')
