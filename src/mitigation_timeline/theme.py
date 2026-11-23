"""Shared dark theme, fonts, window icon and Windows niceties."""

from __future__ import annotations

import sys
import tkinter as tk
from tkinter import font as tkfont
from tkinter import ttk

from mitigation_timeline.paths import ICON_PNG

BG = "#11141b"
SURFACE = "#1a1f2b"
SURFACE_HI = "#232a3b"
BORDER = "#2a3142"
FG = "#e6e9ef"
MUTED = "#8b93a7"
ACCENT = "#5eead4"
ACCENT_2 = "#60a5fa"
WARN = "#fbbf24"
DANGER = "#f87171"
SELECT = "#2d3a52"

IS_WINDOWS = sys.platform == "win32"
FONT = "Segoe UI" if IS_WINDOWS else "Helvetica"
FONT_SEMIBOLD = "Segoe UI Semibold" if IS_WINDOWS else "Helvetica"
MONO = "Consolas" if IS_WINDOWS else "Courier"


def enable_dpi_awareness() -> None:
    """Crisp text on high-DPI Windows displays. Call before creating ``tk.Tk()``."""
    if not IS_WINDOWS:
        return
    import ctypes

    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except (AttributeError, OSError):
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except (AttributeError, OSError):
            pass


def window_handle(window: tk.Misc) -> int:
    window.update_idletasks()
    try:
        return int(window.wm_frame(), 16)
    except (tk.TclError, ValueError):
        return window.winfo_id()


def use_dark_title_bar(window: tk.Misc) -> None:
    if not IS_WINDOWS:
        return
    import ctypes

    try:
        value = ctypes.c_int(1)
        for attribute in (20, 19):  # DWMWA_USE_IMMERSIVE_DARK_MODE (new, old builds)
            if ctypes.windll.dwmapi.DwmSetWindowAttribute(
                window_handle(window), attribute, ctypes.byref(value), ctypes.sizeof(value)
            ) == 0:
                break
    except (AttributeError, OSError):
        pass


def set_app_id(app_id: str) -> None:
    """Give the process its own taskbar identity so our icon is shown instead of Python's."""
    if not IS_WINDOWS:
        return
    import ctypes

    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
    except (AttributeError, OSError):
        pass


def set_icon(window: tk.Tk) -> None:
    try:
        window._icon_image = tk.PhotoImage(file=str(ICON_PNG))  # keep a reference
        window.iconphoto(True, window._icon_image)
    except tk.TclError:
        pass


def px(window: tk.Misc, points: float) -> int:
    """Convert typographic points to pixels for the current display scaling."""
    return int(round(window.winfo_fpixels(f"{points}p")))


def apply_theme(root: tk.Tk) -> ttk.Style:
    root.configure(bg=BG)
    for name in ("TkDefaultFont", "TkTextFont", "TkMenuFont", "TkHeadingFont"):
        try:
            tkfont.nametofont(name).configure(family=FONT, size=10)
        except tk.TclError:
            pass

    style = ttk.Style(root)
    style.theme_use("clam")
    style.configure(
        ".",
        background=BG, foreground=FG, fieldbackground=SURFACE, bordercolor=BORDER,
        lightcolor=SURFACE, darkcolor=SURFACE, troughcolor=BG, focuscolor=ACCENT,
        selectbackground=SELECT, selectforeground=FG, insertcolor=FG, font=(FONT, 10),
    )
    style.configure("TFrame", background=BG)
    style.configure("Card.TFrame", background=SURFACE)
    style.configure("TLabel", background=BG, foreground=FG)
    style.configure("Muted.TLabel", background=BG, foreground=MUTED, font=(FONT, 9))
    style.configure("Error.TLabel", background=BG, foreground=DANGER, font=(FONT, 9))

    style.configure("TButton", background=SURFACE, foreground=FG, bordercolor=BORDER,
                    padding=(px(root, 7), px(root, 3)), relief="flat")
    style.map("TButton", background=[("pressed", SELECT), ("active", SURFACE_HI)],
              bordercolor=[("focus", ACCENT)])
    style.configure("Accent.TButton", background=ACCENT, foreground=BG,
                    font=(FONT_SEMIBOLD, 10), bordercolor=ACCENT)
    style.map("Accent.TButton", background=[("pressed", "#2dd4bf"), ("active", "#99f6e4")])

    style.configure("TEntry", fieldbackground=SURFACE, foreground=FG, bordercolor=BORDER,
                    padding=px(root, 3))
    style.map("TEntry", bordercolor=[("focus", ACCENT)], lightcolor=[("focus", ACCENT)])

    style.configure("TCombobox", fieldbackground=SURFACE, background=SURFACE, foreground=FG,
                    arrowcolor=FG, bordercolor=BORDER, padding=px(root, 3))
    style.map("TCombobox",
              fieldbackground=[("readonly", SURFACE)], foreground=[("readonly", FG)],
              selectbackground=[("readonly", SURFACE)], selectforeground=[("readonly", FG)],
              bordercolor=[("focus", ACCENT)], background=[("active", SURFACE_HI)])
    root.option_add("*TCombobox*Listbox.background", SURFACE)
    root.option_add("*TCombobox*Listbox.foreground", FG)
    root.option_add("*TCombobox*Listbox.selectBackground", SELECT)
    root.option_add("*TCombobox*Listbox.selectForeground", FG)
    root.option_add("*TCombobox*Listbox.font", (FONT, 10))

    line = tkfont.Font(root=root, family=FONT, size=10).metrics("linespace")
    style.configure("Treeview", background=SURFACE, fieldbackground=SURFACE, foreground=FG,
                    bordercolor=BORDER, rowheight=line + px(root, 8))
    style.map("Treeview", background=[("selected", SELECT)], foreground=[("selected", FG)])
    style.configure("Treeview.Heading", background=BG, foreground=MUTED, bordercolor=BORDER,
                    font=(FONT_SEMIBOLD, 9), padding=(px(root, 5), px(root, 4)), relief="flat")
    style.map("Treeview.Heading", background=[("active", SURFACE_HI)])

    style.configure("Vertical.TScrollbar", background=SURFACE_HI, troughcolor=BG,
                    bordercolor=BG, arrowcolor=MUTED, relief="flat")
    style.map("Vertical.TScrollbar", background=[("active", SELECT)])
    return style


def setup_window(root: tk.Tk, app_id: str) -> None:
    set_app_id(app_id)
    set_icon(root)
    apply_theme(root)
    use_dark_title_bar(root)
