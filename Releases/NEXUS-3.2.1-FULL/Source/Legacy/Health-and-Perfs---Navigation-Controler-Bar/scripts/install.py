"""Source bootstrap: prepare the downloader GUI; --offline keeps the build wizard."""
import os
import subprocess
import sys
import venv
from pathlib import Path


def main():
    if sys.version_info < (3,10):raise SystemExit("Python 3.10+ est nécessaire pour le lanceur source.")
    source=Path(__file__).resolve().parents[1]
    root=Path.home()/".cyber-nexus-installer"
    venv.EnvBuilder(with_pip=True).create(root/"venv")
    python=root/("venv/Scripts/python.exe" if sys.platform=="win32" else "venv/bin/python")
    print("Préparation du lanceur CYBER NEXUS HUD…",flush=True)
    subprocess.run([str(python),"-m","pip","install",str(source)],check=True)
    env=dict(os.environ,HEALTHBAR_SOURCE_ROOT=str(source))
    module="healthbar.installer" if "--offline" in sys.argv or sys.platform=="darwin" else "healthbar.bootstrapper"
    raise SystemExit(subprocess.call([str(python),"-c",f"from {module} import main; raise SystemExit(main())"],env=env))


if __name__=="__main__":main()
