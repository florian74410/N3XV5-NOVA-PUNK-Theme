"""Exercise the embedded runtime and render the exact distributed installer."""
import os
import subprocess
import sys
import tempfile
from pathlib import Path
root=Path(__file__).resolve().parents[1]
if sys.platform=='darwin':
    executable=root/'dist/CyberNexusInstaller.app/Contents/MacOS/CyberNexusInstaller'
else:
    executable=root/'dist/CyberNexusInstaller'/('CyberNexusInstaller.exe' if sys.platform=='win32' else 'CyberNexusInstaller')
with tempfile.TemporaryDirectory(prefix='nexus-launcher-qa-') as temporary:
    env=dict(os.environ,QT_QPA_PLATFORM='offscreen',HEALTHBAR_DATA_DIR=temporary)
    subprocess.run([str(executable),'--verify-payload'],env=env,check=True,timeout=90)
    image=Path(temporary)/'installer.png'
    subprocess.run([str(executable),'--preview',str(image)],env=env,check=True,timeout=45)
    if not image.is_file() or image.stat().st_size<1000:raise SystemExit('Installer screenshot missing')
