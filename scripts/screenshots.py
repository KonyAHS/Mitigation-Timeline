"""Regenerate the README screenshots in docs/screenshots/ (Windows only).

Usage:  uv run --with pillow python scripts/screenshots.py
"""

from __future__ import annotations

import ctypes
import tkinter as tk
from ctypes import wintypes
from pathlib import Path

from PIL import ImageGrab

from mitigation_timeline import theme
from mitigation_timeline.designer import PlanDesigner
from mitigation_timeline.overlay import Overlay

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "screenshots"
PLAN = ROOT / "plans" / "example.txt"


def window_rect(window: tk.Misc) -> tuple[int, int, int, int]:
    """Visible window bounds including the title bar, minus the invisible resize border."""
    rect = wintypes.RECT()
    ctypes.windll.dwmapi.DwmGetWindowAttribute(
        theme.window_handle(window), 9, ctypes.byref(rect), ctypes.sizeof(rect))  # EXTENDED_FRAME
    return rect.left, rect.top, rect.right, rect.bottom


def capture(window: tk.Misc, name: str) -> None:
    window.update()
    window.after(400)  # let DWM finish compositing the dark title bar
    window.update()
    OUT.mkdir(parents=True, exist_ok=True)
    ImageGrab.grab(window_rect(window), all_screens=True).save(OUT / name)
    print("wrote", OUT / name)


def main() -> None:
    theme.enable_dpi_awareness()

    root = tk.Tk()
    theme.setup_window(root, "KonyAHS.MitigationTimeline.Screenshots")
    root.geometry("+80+80")
    overlay = Overlay(root, plan=PLAN, opacity=1.0, global_hotkeys=False)
    overlay.start()
    overlay.timeline.seek(57.6)  # mid-fight: a few seconds before "Heavy Raidwide"
    overlay.render()
    root.update()
    overlay.render()  # second pass once the progress bar has its real width
    capture(root, "overlay.png")
    overlay.quit()

    root = tk.Tk()
    theme.setup_window(root, "KonyAHS.MitigationTimeline.Screenshots")
    root.geometry("+80+80")
    root.attributes("-topmost", True)
    designer = PlanDesigner(root, PLAN)
    designer.tree.selection_set(designer.tree.get_children()[3])
    capture(root, "designer.png")
    root.destroy()


if __name__ == "__main__":
    main()
