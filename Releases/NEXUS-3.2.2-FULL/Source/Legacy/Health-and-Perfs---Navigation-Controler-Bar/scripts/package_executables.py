"""Place self-contained installers at the repository root after native CI succeeds."""
import gzip
import hashlib
import io
import json
import os
import posixpath
import re
import shutil
import stat
import sys
import tarfile
import tempfile
import zipfile
from pathlib import Path, PurePosixPath

LIMIT=100*1024*1024
HEADER='''#!/bin/sh
# CYBER NEXUS HUD / NovaBar @VERSION@ - autonomous Linux installer
set -eu
case "${1-}" in
  --help) echo 'CYBER NEXUS HUD - Mint XFCE / Ubuntu / Bazzite Desktop'; echo 'Run: sh CyberNexusHUD-Linux-x86_64.run'; echo 'Checks: --check (archive) / --verify (isolated native self-test)'; exit 0 ;;
  --version) echo '@VERSION@'; exit 0 ;;
esac
actual=$(tail -n +@LINE@ "$0" | sha256sum | cut -d ' ' -f 1)
if [ "$actual" != '@DIGEST@' ]; then
  echo 'The installer download is incomplete or corrupted.' >&2
  exit 1
fi
if [ "${1-}" = '--check' ]; then echo 'SHA-256 OK'; exit 0; fi
work_dir=$(mktemp -d "${TMPDIR:-/tmp}/cyber-nexus.XXXXXX")
trap 'rm -rf -- "$work_dir"' EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
tail -n +@LINE@ "$0" | gzip -dc | tar -xf - -C "$work_dir"
if [ "${1-}" = '--verify' ]; then
  QT_QPA_PLATFORM=offscreen HEALTHBAR_DATA_DIR="$work_dir/qa" "$work_dir/HealthPerfsBar/HealthPerfsBar" --self-test --expect-version @VERSION@
else
  "$work_dir/HealthPerfsBar/HealthPerfsBar" --setup
fi
exit 0
# __CYBER_NEXUS_PAYLOAD__
'''


def linux_run(archive,output,version):
    output=Path(output)
    with tempfile.TemporaryDirectory(prefix='nexus-run-build-') as temporary:
        packed=Path(temporary)/'runtime.tar.gz'
        with zipfile.ZipFile(archive) as package, tarfile.open(packed,'w:gz',compresslevel=5) as target:
            for item in package.infolist():
                name=PurePosixPath(item.filename)
                if name.is_absolute() or '..' in name.parts or '\\' in item.filename or ':' in item.filename:
                    raise ValueError('Unsafe runtime archive path')
                info=tarfile.TarInfo(name.as_posix());info.mode=(item.external_attr>>16)&0o777
                if stat.S_ISLNK(item.external_attr>>16):
                    link=package.read(item).decode('utf-8')
                    normalized=posixpath.normpath(posixpath.join(str(name.parent),link))
                    if link.startswith('/') or normalized=='..' or normalized.startswith('../'):
                        raise ValueError('External runtime link')
                    info.type=tarfile.SYMTYPE;info.linkname=link;target.addfile(info)
                elif item.is_dir():
                    info.type=tarfile.DIRTYPE;target.addfile(info)
                else:
                    info.size=item.file_size
                    with package.open(item) as source:target.addfile(info,source)
        digest=hashlib.sha256(packed.read_bytes()).hexdigest()
        header=HEADER.replace('@VERSION@',version).replace('@DIGEST@',digest)
        header=header.replace('@LINE@',str(header.count('\n')+1))
        output.parent.mkdir(parents=True,exist_ok=True)
        with output.open('wb') as dest,packed.open('rb') as source:
            dest.write(header.encode('utf-8'));shutil.copyfileobj(source,dest)
        output.chmod(0o755)
        if output.stat().st_size>=LIMIT:raise ValueError('Linux installer exceeds GitHub file limit')
    return output


def one_file(root,pattern):
    found=list(Path(root).rglob(pattern))
    if len(found)!=1:raise ValueError(f'Expected exactly one {pattern}, found {len(found)}')
    return found[0]


def retire_stale_linux_packages(output):
    """Remove only previous downloadable DEB/Flatpak builds from the output folder.

    Never modify user profiles, runtime installations, or unrelated files.
    """
    root = Path(output) / 'Linux'
    for pattern in ('NovaBar_*_amd64.deb', 'NovaBar_*_x86_64.flatpak'):
        for old in root.glob(pattern):
            if old.is_file() and not old.is_symlink():
                old.unlink()


def assemble(artifacts,output,version,source_sha=''):
    output=Path(output)
    for folder in ('Linux','Windows','MacOS'):(output/folder).mkdir(parents=True,exist_ok=True)
    retire_stale_linux_packages(output)
    files=[linux_run(one_file(artifacts,'NovaBar-runtime-linux-x86_64.zip'),output/'Linux/CyberNexusHUD-Linux-x86_64.run',version)]
    for pattern,folder in (('NovaBar_*_amd64.deb','Linux'),
                           ('NovaBar_*_x86_64.flatpak','Linux'),
                           ('CyberNexusHUD-Setup-Windows.exe','Windows'),
                           ('CyberNexusHUD-macOS-arm64.dmg','MacOS'),
                           ('CyberNexusHUD-macOS-x86_64.dmg','MacOS')):
        source=one_file(artifacts,pattern)
        if source.stat().st_size>=LIMIT:raise ValueError(f'{source.name} exceeds GitHub file limit')
        dest=output/folder/source.name;shutil.copy2(source,dest);files.append(dest)
    checks={str(path.relative_to(output)):{'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                                         'bytes':path.stat().st_size} for path in files}
    (output/'manifest.json').write_text(json.dumps({'project':'CYBER NEXUS HUD','application':'NovaBar',
        'version':version,'source_commit':source_sha,'contains_novabar':True,'files':checks},indent=2)+'\n',encoding='utf-8')
    (output/'SHA256SUMS').write_text(''.join(f"{value['sha256']}  {name}\n" for name,value in checks.items()),encoding='utf-8')
    return files


if __name__=='__main__':
    import tomllib
    root=Path(__file__).resolve().parents[1]
    version=tomllib.loads((root/'pyproject.toml').read_text())['project']['version']
    if not re.fullmatch(r'\d+\.\d+\.\d+(?:\.\d+)?',version):raise SystemExit('Invalid project version')
    for path in assemble(sys.argv[1],root/'Executable',version,os.getenv('NEXUS_BUILD_SHA','')):
        print(f'{path.relative_to(root)}: {path.stat().st_size/1024/1024:.1f} MiB')
