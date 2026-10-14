# -*- coding: utf-8 -*-
# Lazy Earth & Maps - a QGIS plugin by Lazy by Design (Sheldon Willie)
# Derived from "Open Google Maps" by Harry King (GPL). See NOTICE.txt.
# Licensed under the GNU General Public License v2 or (at your option) any later version.
"""Locate / launch Google Earth Pro. Pure stdlib."""
import os
import shutil
import subprocess
import sys


def detect_earth_pro():
    """Return an executable path (or .app bundle on macOS), or '' if not found."""
    cands = []
    if sys.platform.startswith("win"):
        for env in ("ProgramFiles", "ProgramFiles(x86)", "LOCALAPPDATA"):
            base = os.environ.get(env)
            if base:
                cands.append(os.path.join(base, "Google", "Google Earth Pro", "client", "googleearth.exe"))
    elif sys.platform == "darwin":
        cands += ["/Applications/Google Earth Pro.app",
                  os.path.expanduser("~/Applications/Google Earth Pro.app")]
    else:
        cands += [shutil.which("google-earth-pro") or "", "/opt/google/earth/pro/google-earth-pro",
                  "/usr/bin/google-earth-pro"]
    for c in cands:
        if c and os.path.exists(c):
            return c
    return ""


def launch_earth_pro(exe, path):
    """Open a KML/KMZ in Earth Pro. Returns True if the process was started."""
    try:
        if sys.platform == "darwin" and exe.endswith(".app"):
            subprocess.Popen(["open", "-a", exe, path])
        else:
            subprocess.Popen([exe, path])
        return True
    except Exception:
        return False
