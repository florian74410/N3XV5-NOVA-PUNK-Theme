"""Verify the updater's extracted payload, not just the original build tree."""
import os
import subprocess
import sys
import tempfile
from pathlib import Path
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'src'))
from healthbar.updates import extract_runtime, platform_key
from healthbar.install_engine import payload_executable
from healthbar import __version__
with tempfile.TemporaryDirectory() as temporary:
    extract_runtime(root/('NovaBar-runtime-'+platform_key()+'.zip'),temporary)
    executable=payload_executable(temporary)
    if not executable:raise SystemExit('Runtime missing')
    subprocess.run([str(executable),'--self-test','--expect-version',__version__],
        env=dict(os.environ,QT_QPA_PLATFORM='offscreen',HEALTHBAR_DATA_DIR=str(Path(temporary)/'profile')),check=True,timeout=45)
