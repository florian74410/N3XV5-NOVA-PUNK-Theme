"""Run in tagged release CI after all runtime archives have been downloaded."""
import hashlib
import json
import re
import sys
from pathlib import Path
repo="florian74410/Health-and-Perfs---Navigation-Controler-Bar"
tag=sys.argv[1]
if not re.fullmatch(r"v\d+\.\d+\.\d+",tag):raise SystemExit("Release tags must be vMAJOR.MINOR.PATCH")
platforms={}
for path in Path('release').glob('NovaBar-runtime-*.zip'):
    key=path.name.removeprefix('NovaBar-runtime-').removesuffix('.zip')
    platforms[key]={"url":f"https://github.com/{repo}/releases/download/{tag}/{path.name}",
                    "sha256":hashlib.sha256(path.read_bytes()).hexdigest()}
required={"linux-x86_64","windows-x86_64","macos-arm64","macos-x86_64"}
if set(platforms)!=required:raise SystemExit("Runtime release set is incomplete")
Path('release/novabar-update-manifest.json').write_text(json.dumps({"schema_version":1,
    "version":tag[1:],"platforms":platforms},indent=2),encoding='utf-8')

# Bind native packages to the same immutable release tag and hashes.
packages={key:[] for key in required}
for path in Path('release').iterdir():
    suffix=path.suffix
    if suffix not in ('.deb','.run','.exe','.dmg') or path.name.startswith('NovaBarDownloader-'):continue
    key=('windows-x86_64' if suffix=='.exe' else
         'macos-arm64' if suffix=='.dmg' and 'arm64' in path.name else
         'macos-x86_64' if suffix=='.dmg' else 'linux-x86_64')
    packages[key].append({'name':path.name,'format':suffix,
        'url':f'https://github.com/{repo}/releases/download/{tag}/{path.name}',
        'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
for key,suffix in [('linux-x86_64','.deb'),('linux-x86_64','.run'),('windows-x86_64','.exe')]:
    if not any(asset['format']==suffix for asset in packages[key]):raise SystemExit('Missing native package '+key+suffix)
Path('release/novabar-bootstrap-manifest.json').write_text(json.dumps({
    'schema_version':1,'version':tag[1:],'packages':packages},indent=2),encoding='utf-8')
