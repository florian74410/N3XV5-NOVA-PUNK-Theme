#!/usr/bin/env python3
"""Non-destructive N3XV5 graphic archive collector.

Requires Pillow. Example:
 python Tools/AssetPipeline/import_assets.py --source ~/NOVA-083 \
   --source ~/NOVA-DEV --source ~/Téléchargements --version legacy --dry-run
Then review sources and rerun without --dry-run.

Sheet slicing is EXPLICIT: --sheet path/to/sheet.png --grid 4x4.
White background transparency is edge-connected only, with originals untouched.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import shutil
from collections import deque
from datetime import datetime, timezone
from pathlib import Path

MEDIA = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg", ".bmp", ".ico", ".apng", ".tif", ".tiff"}
ARCHIVES = {".zip", ".deb"}
SKIP_DIRS = {".git", ".venv", "__pycache__", "node_modules", ".cache"}
MAX_SIZE = 200 * 1024 * 1024

def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def safe_name(text: str) -> str:
    return "".join(c if c.isalnum() or c in "-_." else "_" for c in text)[:100]

def make_unique(root: Path, name: str, sha: str) -> Path:
    stem = safe_name(Path(name).stem)
    suffix = Path(name).suffix.lower()
    return root / f"{stem}__{sha[:12]}{suffix}"

def connected_white_background(image, threshold: int = 247):
    """Turn ONLY near-white background connected to image perimeter transparent.

    Preserves white objects surrounded by darker pixels; works for sheets with
    uniform white canvas, never edits the original. Returns RGBA result.
    """
    from PIL import Image
    img = image.convert("RGBA")
    w,h = img.size
    px = img.load()
    seen = bytearray(w*h)
    q = deque()
    for x in range(w):
        q.append((x,0))
        if h > 1: q.append((x,h-1))
    for y in range(1,h-1):
        q.append((0,y))
        if w > 1: q.append((w-1,y))
    while q:
        x,y=q.popleft()
        i=y*w+x
        if seen[i]: continue
        seen[i]=1
        r,g,b,a=px[x,y]
        if not (r>=threshold and g>=threshold and b>=threshold and a>0):
            continue
        px[x,y]=(r,g,b,0)
        if x>0:q.append((x-1,y))
        if x+1<w:q.append((x+1,y))
        if y>0:q.append((x,y-1))
        if y+1<h:q.append((x,y+1))
    return img

def collect(sources: list[Path], root: Path, version: str, dry: bool):
    records=[]
    hashes={}
    for base in sources:
        if not base.exists():
            records.append({"source":str(base),"status":"missing"})
            continue
        paths=[base] if base.is_file() else base.rglob("*")
        for p in paths:
            if not p.is_file() or any(s in SKIP_DIRS for s in p.parts):
                continue
            if p.suffix.lower() not in MEDIA|ARCHIVES:
                continue
            try:
                if p.stat().st_size > MAX_SIZE:
                    records.append({"source":str(p),"status":"oversize"})
                    continue
                binary=p.read_bytes()
                sha=digest(binary)
                relative=(p.relative_to(base).as_posix() if base.is_dir() else p.name)
                category="Sheets" if "sheet" in p.name.lower() or "planche" in p.name.lower() else "Originals"
                subroot=root/category/safe_name(version)/safe_name(base.name)
                target=make_unique(subroot,p.name,sha)
                entry={"source":str(p),"relative":relative,"sha256":sha,
                       "bytes":len(binary),"target":str(target.relative_to(root))}
                if sha in hashes:
                    entry["duplicate_of"]=hashes[sha]
                    entry["status"]="duplicate"
                else:
                    hashes[sha]=entry["target"]
                    entry["status"]="indexed" if dry else "copied"
                    if not dry:
                        target.parent.mkdir(parents=True,exist_ok=True)
                        if not target.exists():
                            shutil.copy2(p,target)
                records.append(entry)
            except (OSError,ValueError) as e:
                records.append({"source":str(p),"status":"error","error":str(e)})
    return records

def split_sheet(sheet: Path, root: Path, version: str, grid: tuple[int,int],
                threshold: int, dry: bool):
    from PIL import Image
    with Image.open(sheet) as raw:
        img=raw.convert("RGBA")
    cols,rows=grid
    if cols<1 or rows<1 or img.width<cols or img.height<rows:
        raise ValueError("Invalid sheet dimensions or grid")
    results=[]
    sha=digest(sheet.read_bytes())
    targetdir=root/"Extracted"/safe_name(version)/f"{safe_name(sheet.stem)}__{sha[:12]}"
    alphadir=root/"Transparent"/safe_name(version)/f"{safe_name(sheet.stem)}__{sha[:12]}"
    for row in range(rows):
        for col in range(cols):
            box=(round(col*img.width/cols),round(row*img.height/rows),
                 round((col+1)*img.width/cols),round((row+1)*img.height/rows))
            sprite=img.crop(box)
            name=f"r{row+1:02d}_c{col+1:02d}.png"
            info={"sheet":str(sheet),"sheet_sha256":sha,"cell":[row,col],
                  "box":box,"raw":str((targetdir/name).relative_to(root)),
                  "transparent":str((alphadir/name).relative_to(root))}
            if not dry:
                targetdir.mkdir(parents=True,exist_ok=True)
                alphadir.mkdir(parents=True,exist_ok=True)
                sprite.save(targetdir/name)
                connected_white_background(sprite,threshold).save(alphadir/name)
            results.append(info)
    return results

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--source",type=Path,action="append",default=[])
    parser.add_argument("--root",type=Path,default=Path(__file__).resolve().parents[2]/"App"/"Assets")
    parser.add_argument("--version",default="legacy")
    parser.add_argument("--dry-run",action="store_true")
    parser.add_argument("--sheet",type=Path)
    parser.add_argument("--grid",help="Explicit grid COLSxROWS, e.g. 4x4")
    parser.add_argument("--white-threshold",type=int,default=247)
    args=parser.parse_args()
    if not (0<=args.white_threshold<=255):
        parser.error("white threshold must be 0..255")
    if args.sheet and not args.grid:
        parser.error("--sheet requires --grid; never guess sheet layout")
    if not args.source and not args.sheet:
        parser.error("provide --source or --sheet")
    data={"schema":1,"created":datetime.now(timezone.utc).isoformat(),
          "version":args.version,"dry_run":args.dry_run,
          "assets":collect(args.source,args.root,args.version,args.dry_run)}
    if args.sheet:
        a=args.grid.lower().split("x")
        if len(a)!=2 or not all(v.isdigit() for v in a):
            parser.error("grid syntax is COLSxROWS")
        data["sprites"]=split_sheet(args.sheet,args.root,args.version,
                                    (int(a[0]),int(a[1])),
                                    args.white_threshold,args.dry_run)
    out=json.dumps(data,indent=2,ensure_ascii=False)
    if args.dry_run:
        print(out)
    else:
        m=args.root/"Manifests"
        m.mkdir(parents=True,exist_ok=True)
        dest=m/f"import-{safe_name(args.version)}-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
        dest.write_text(out+"\n",encoding="utf-8")
        print(f"Manifest: {dest}; items: {len(data['assets'])}; sprites: {len(data.get('sprites',[]))}")

if __name__=="__main__":
    main()
