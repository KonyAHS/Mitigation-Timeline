"""Build the Windows release: two standalone .exe files zipped with the example plan.

Usage:  uv run --group build python scripts/build.py
Output: dist/MitigationTimeline-<version>-windows.zip
"""

from __future__ import annotations

import os
import shutil
import zipfile
from pathlib import Path

import PyInstaller.__main__

from mitigation_timeline import __version__

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "src" / "mitigation_timeline"
DIST = ROOT / "dist"
WORK = ROOT / "build"
APPS = {
    "MitigationOverlay": PKG / "overlay.py",
    "PlanDesigner": PKG / "designer.py",
}


def build_exe(name: str, script: Path) -> Path:
    PyInstaller.__main__.run([
        str(script),
        "--name", name,
        "--onefile",
        "--windowed",
        "--noconfirm",
        "--clean",
        "--icon", str(ROOT / "assets" / "icon.ico"),
        "--add-data", f"{PKG / 'assets' / 'icon.png'}{os.pathsep}mitigation_timeline/assets",
        "--distpath", str(DIST / "exe"),
        "--workpath", str(WORK),
        "--specpath", str(WORK),
    ])
    return DIST / "exe" / f"{name}.exe"


def main() -> None:
    shutil.rmtree(DIST, ignore_errors=True)
    exes = [build_exe(name, script) for name, script in APPS.items()]

    archive = DIST / f"MitigationTimeline-{__version__}-windows.zip"
    folder = "MitigationTimeline"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zf:
        for exe in exes:
            zf.write(exe, f"{folder}/{exe.name}")
        zf.write(ROOT / "plans" / "example.txt", f"{folder}/plans/example.txt")
        zf.write(ROOT / "README.md", f"{folder}/README.md")
    print(f"\nBuilt {archive}")


if __name__ == "__main__":
    main()
