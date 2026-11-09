#!/usr/bin/python3
"""Minimal NovaBar privileged helper. Only toggles supported kernel boost nodes.

Installed root-owned at /usr/libexec/novabar-turbo-helper by the Debian package.
Not an unrestricted shell, does not accept paths or commands from the caller.
"""
import os
import sys
from pathlib import Path

NODES=(
    (Path("/sys/devices/system/cpu/intel_pstate/no_turbo"),True),
    (Path("/sys/devices/system/cpu/cpufreq/boost"),False),
)

def main(args=None):
    argv=sys.argv[1:] if args is None else args
    if os.geteuid()!=0 or len(argv)!=1 or argv[0] not in ("on","off"):
        print("Commande ou privilèges invalides",file=sys.stderr)
        return 2
    enabled=argv[0]=="on"
    for path,inverted in NODES:
        if not path.is_file():
            continue
        desired="0" if (enabled and inverted) else "1" if (enabled or inverted) else "0"
        # Fixed kernel sysfs node. Explicitly reject redirection/symlink.
        if path.is_symlink():
            print("Lien symbolique de capteur interdit",file=sys.stderr)
            return 3
        try:
            fd=os.open(str(path),os.O_WRONLY|os.O_NOFOLLOW)
            try:
                os.write(fd,desired.encode("ascii"))
            finally:
                os.close(fd)
            actual=path.read_text(encoding="ascii").strip()
            if actual!=desired:
                print("Commutation CPU non confirmée",file=sys.stderr)
                return 4
            print("Turbo ON" if enabled else "NORMAL MODE")
            return 0
        except OSError as exc:
            print(str(exc),file=sys.stderr)
            return 5
    print("Aucun commutateur CPU Turbo pris en charge par le noyau",file=sys.stderr)
    return 6

if __name__=="__main__":
    raise SystemExit(main())
