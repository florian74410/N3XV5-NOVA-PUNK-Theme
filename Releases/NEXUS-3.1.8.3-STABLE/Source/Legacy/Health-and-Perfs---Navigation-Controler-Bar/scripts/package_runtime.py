"""Small release archive containing runtime only, never user profiles or plugins."""
import os
import platform
import stat
import sys
import zipfile
from pathlib import Path
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/"src"))
from healthbar.updates import platform_key
payload=root/"dist"/("HealthPerfsBar.app" if sys.platform=="darwin" else "HealthPerfsBar")
out=root/("NovaBar-runtime-"+platform_key()+".zip")
with zipfile.ZipFile(out,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=4) as package:
    for path in sorted(payload.rglob("*")):
        if path.is_symlink():
            info=zipfile.ZipInfo(path.relative_to(payload.parent).as_posix())
            info.create_system=3
            info.external_attr=(stat.S_IFLNK | 0o777)<<16
            package.writestr(info,os.readlink(path).encode("utf-8"))
            continue
        if not path.is_file():continue
        # Preserve bundle links exactly; the extractor validates their internal targets.
        name=path.relative_to(payload.parent).as_posix()
        info=zipfile.ZipInfo(name)
        info.external_attr=(stat.S_IFREG | (0o755 if path.stat().st_mode&0o111 else 0o644))<<16
        info.compress_type=zipfile.ZIP_DEFLATED
        package.writestr(info,path.read_bytes())
print(out.name)
