"""Optional user palette overrides. Original v0.6.11 artwork is untouched.

Three editable colours affect the shared electric-neon accents and glass
background when chosen. No override means identical native palette.
"""
from __future__ import annotations
import json
import os
import re
import tempfile
from .config import data_dir

THEMES=("cyber-futuriste","blue-neon","green-matrix","red-blood","redblack-0822")
PARTS=("primary","secondary","background")
HEX=re.compile(r"^#[0-9A-Fa-f]{6}$")

def validate(raw):
    result={}
    if not isinstance(raw,dict):return result
    for theme in THEMES:
        val=raw.get(theme)
        if not isinstance(val,dict):continue
        colors={name:val[name].upper() for name in PARTS
                if isinstance(val.get(name),str) and HEX.fullmatch(val[name])}
        if colors:result[theme]=colors
    return result

def path():
    return data_dir()/"theme-overrides.json"

def load():
    try:return validate(json.loads(path().read_text(encoding="utf-8")))
    except (OSError,ValueError,TypeError):return {}

def save(raw):
    target=path()
    target.parent.mkdir(parents=True,exist_ok=True)
    fd,temp=tempfile.mkstemp(prefix=".theme-",dir=target.parent)
    try:
        with os.fdopen(fd,"w",encoding="utf-8") as out:
            json.dump(validate(raw),out,indent=2,ensure_ascii=False)
            out.flush()
            os.fsync(out.fileno())
        os.replace(temp,target)
    finally:
        if os.path.exists(temp):os.unlink(temp)
