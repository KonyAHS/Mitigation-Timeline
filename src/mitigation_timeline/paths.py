"""Locations of bundled assets and user plan files."""

from __future__ import annotations

import sys
from pathlib import Path

from mitigation_timeline.plan import looks_like_plan

PACKAGE_DIR = Path(__file__).resolve().parent
ICON_PNG = PACKAGE_DIR / "assets" / "icon.png"


def app_dirs() -> list[Path]:
    """Folders searched for plans: the app folder (exe or source checkout), then the CWD."""
    dirs: list[Path] = []
    if getattr(sys, "frozen", False):
        dirs.append(Path(sys.executable).resolve().parent)
    else:
        root = PACKAGE_DIR.parents[1]
        if (root / "pyproject.toml").is_file():
            dirs.append(root)
    dirs.append(Path.cwd().resolve())
    return list(dict.fromkeys(dirs))


def default_plans_dir() -> Path:
    return app_dirs()[0] / "plans"


def discover_plans() -> list[Path]:
    """All plan files in ``<app>/plans/`` plus legacy plans sitting next to the app."""
    found: list[Path] = []
    for base in app_dirs():
        for folder in (base / "plans", base):
            if not folder.is_dir():
                continue
            for path in sorted(folder.glob("*.txt"), key=lambda p: p.name.lower()):
                path = path.resolve()
                if path not in found and looks_like_plan(path):
                    found.append(path)
    return found
