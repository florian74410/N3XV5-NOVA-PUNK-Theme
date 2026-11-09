"""Build the runtime and an offline native installer containing that exact runtime."""
import os
import subprocess
import sys
from pathlib import Path

root=Path(__file__).resolve().parents[1]
from build_plugins import build as build_plugins
build_plugins(root/"src/healthbar/assets/plugins")
sys.path.insert(0, str(root/"src"))
from healthbar.app_icon import save_brand_assets
_, windows_icon = save_brand_assets(root/"dist")
common=[sys.executable,"-m","PyInstaller","--noconfirm","--clean","--windowed",
        "--paths",str(root/"src"),"--add-data",str(root/"src/healthbar/assets")+os.pathsep+"healthbar/assets"]
if sys.platform == "win32":
    common += ["--icon", str(windows_icon)]
elif sys.platform.startswith("linux"):
    # Must execute before Qt/GIO loads, in all frozen entrypoints.
    common += ["--runtime-hook", str(root/"scripts/runtime_linux_gio.py")]
# Some managed Python distributions load a companion CA policy file from ssl.py.
# Preserve that trust policy when freezing; normal CPython needs no extra file.
import ssl
ssl_policy=Path(ssl.__file__).with_name("codex-rejected-cas.pem")
if ssl_policy.is_file():common += ["--add-data",str(ssl_policy)+os.pathsep+"."]
subprocess.run(common+["--name","HealthPerfsBar","--osx-bundle-identifier","com.healthperfs.bar",
    str(root/"scripts/entrypoint.py")],cwd=root,check=True)
subprocess.run([sys.executable,str(root/"scripts/package_runtime.py")],cwd=root,check=True)
sys.path.insert(0,str(root/"src"))
from healthbar.updates import platform_key
payload=root/("NovaBar-runtime-"+platform_key()+".zip")
# Embed an opaque ZIP: PyInstaller must not re-sign the inner macOS application.
subprocess.run(common+["--name","CyberNexusInstaller","--osx-bundle-identifier","com.cybernexushud.installer",
    "--add-data",str(payload)+os.pathsep+"payload",
    str(root/"scripts/installer_entrypoint.py")],cwd=root,check=True)

# The downloader is a separate small bootstrap entry point; offline installers
# remain independent so they cannot recursively download themselves.
name="NovaBarDownloader-"+platform_key()
subprocess.run(common+["--onefile","--name",name,str(root/"scripts/bootstrap_entrypoint.py")],cwd=root,check=True)
