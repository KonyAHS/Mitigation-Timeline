"""Always-on-top overlay that counts down to your next mechanic and its mitigation."""

from __future__ import annotations

import argparse
import math
import queue
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, ttk
from types import SimpleNamespace

from mitigation_timeline import __version__, theme
from mitigation_timeline.paths import default_plans_dir, discover_plans
from mitigation_timeline.plan import Mechanic, PlanError, format_time, load_plan
from mitigation_timeline.theme import (
    ACCENT,
    ACCENT_2,
    BG,
    BORDER,
    DANGER,
    FG,
    FONT,
    FONT_SEMIBOLD,
    MONO,
    MUTED,
    SURFACE,
    SURFACE_HI,
    WARN,
)
from mitigation_timeline.timeline import Timeline

# Global hotkeys (work while the game has focus), in `keyboard` library syntax.
HOTKEYS = {
    "start": "shift+t",
    "next": "shift+right",
    "back": "shift+left",
    "reset": "shift+}",
    "quit": "shift+q",
}
# Window-only fallbacks for when global hotkeys are unavailable.
TK_BINDINGS = {
    "start": "<Shift-T>",
    "next": "<Shift-Right>",
    "back": "<Shift-Left>",
    "reset": "<Shift-braceright>",
    "quit": "<Shift-Q>",
}
HINT = "Shift+T pull  ·  Shift+←/→ step  ·  Shift+} reset  ·  Shift+Q quit"
TICK_MS = 100
WIDTH_PT = 270


def format_countdown(seconds: float) -> str:
    seconds = max(0, math.ceil(seconds))
    return f"{seconds // 60}:{seconds % 60:02}" if seconds >= 60 else f"{seconds}s"


def urgency_color(seconds: float) -> str:
    if seconds <= 5:
        return DANGER
    if seconds <= 10:
        return WARN
    return FG


class Overlay:
    def __init__(self, root: tk.Tk, plan: Path | None = None, opacity: float = 0.85,
                 topmost: bool = True, global_hotkeys: bool = True) -> None:
        self.root = root
        self.timeline = Timeline()
        self.plan_path: Path | None = None
        self.plans: dict[str, Path] = {}
        self.error: str | None = None
        self.actions: queue.SimpleQueue[str] = queue.SimpleQueue()
        self._keyboard = None
        self._closing = False
        self._after_id: str | None = None

        root.title("Mitigation Timeline")
        root.attributes("-topmost", topmost)
        root.attributes("-alpha", max(0.2, min(1.0, opacity)))
        root.resizable(True, False)
        root.minsize(theme.px(root, WIDTH_PT), 0)
        root.protocol("WM_DELETE_WINDOW", self.quit)

        self._build()
        self.refresh_plans(select=plan)
        if not (global_hotkeys and self._register_global_hotkeys()):
            self._bind_window_hotkeys()
        self._tick()

    # -- layout ------------------------------------------------------------------
    def _build(self) -> None:
        root = self.root
        pad = theme.px(root, 7)
        wrap = theme.px(root, WIDTH_PT) - 4 * pad

        self.setup = ttk.Frame(root, padding=(pad, pad, pad, 0))
        self.plan_var = tk.StringVar()
        self.combo = ttk.Combobox(self.setup, textvariable=self.plan_var, state="readonly")
        self.combo.pack(side="left", fill="x", expand=True)
        self.combo.bind("<<ComboboxSelected>>", self._on_combo)
        ttk.Button(self.setup, text="Open…", command=self.browse).pack(
            side="left", padx=(theme.px(root, 4), 0))
        self.setup.pack(fill="x")

        self.now = self._card("NEXT", big=True, wrap=wrap, pad=pad)
        self.then = self._card("THEN", big=False, wrap=wrap, pad=pad)

        footer = tk.Frame(root, bg=BG)
        footer.pack(fill="x", padx=pad, pady=(pad // 2, 0))
        self.clock_label = tk.Label(footer, text="00:00", font=(MONO, 18, "bold"), bg=BG, fg=FG)
        self.clock_label.pack(side="left")
        self.status_label = tk.Label(footer, font=(FONT, 9), bg=BG, fg=MUTED, anchor="e")
        self.status_label.pack(side="right", fill="x", expand=True)
        tk.Label(root, text=HINT, font=(FONT, 8), bg=BG, fg=MUTED, anchor="w").pack(
            fill="x", padx=pad, pady=(0, pad))

    def _card(self, caption: str, big: bool, wrap: int, pad: int) -> SimpleNamespace:
        outer = tk.Frame(self.root, bg=SURFACE, highlightthickness=1,
                         highlightbackground=BORDER, highlightcolor=BORDER)
        outer.pack(fill="x", padx=pad, pady=(pad, 0))
        inner = tk.Frame(outer, bg=SURFACE)
        inner.pack(fill="both", expand=True, padx=pad, pady=pad)

        top = tk.Frame(inner, bg=SURFACE)
        top.pack(fill="x")
        tk.Label(top, text=caption, font=(FONT_SEMIBOLD, 8), bg=SURFACE, fg=MUTED).pack(
            side="left", anchor="n")
        countdown = tk.Label(top, font=(MONO, 20 if big else 12, "bold"), bg=SURFACE, fg=MUTED)
        countdown.pack(side="right")

        def label(font, fg, lines):
            widget = tk.Label(inner, font=font, bg=SURFACE, fg=fg, anchor="nw", justify="left",
                              height=lines, wraplength=wrap)
            widget.pack(fill="x")
            return widget

        card = SimpleNamespace(frame=outer, countdown=countdown, notes=None, bar=None)
        card.name = label((FONT_SEMIBOLD, 15 if big else 11), FG, 1)
        card.mitigation = label((FONT_SEMIBOLD, 12 if big else 10), ACCENT if big else ACCENT_2, 2)
        if big:
            card.notes = label((FONT, 9), MUTED, 2)
            card.bar = tk.Canvas(inner, height=theme.px(self.root, 3), bg=SURFACE_HI,
                                 highlightthickness=0, bd=0)
            card.bar.pack(fill="x", pady=(theme.px(self.root, 5), 0))
            card.fill = card.bar.create_rectangle(0, 0, 0, 0, width=0, fill=ACCENT)

        def rewrap(event):
            for widget in (card.name, card.mitigation, card.notes):
                if widget is not None:
                    widget.configure(wraplength=max(50, event.width))

        inner.bind("<Configure>", rewrap)
        return card

    # -- plans -------------------------------------------------------------------
    def refresh_plans(self, select: Path | None = None) -> None:
        paths = discover_plans()
        if select is not None and select not in paths:
            paths.insert(0, select)
        names = [p.name for p in paths]
        self.plans = {
            (f"{p.name}  ({p.parent.name})" if names.count(p.name) > 1 else p.name): p
            for p in paths
        }
        self.combo["values"] = list(self.plans)
        if select is None and self.plan_path in paths:
            select = self.plan_path
        if select is None and paths:
            select = paths[0]
        if select is not None:
            self.select_plan(select)
        else:
            self.error = f"No plans found - put .txt plans in {default_plans_dir()}"

    def select_plan(self, path: Path) -> None:
        self.plan_path = path
        for label, candidate in self.plans.items():
            if candidate == path:
                self.plan_var.set(label)
        self.load(path)

    def load(self, path: Path) -> bool:
        try:
            mechanics = load_plan(path)
        except (OSError, PlanError) as exc:
            self.error = f"{path.name}: {exc}"
            self.timeline.load([])
            return False
        self.error = None if mechanics else f"{path.name} contains no mechanics"
        self.timeline.load(mechanics)
        return bool(mechanics)

    def browse(self) -> None:
        folder = default_plans_dir()
        chosen = filedialog.askopenfilename(
            parent=self.root, title="Open mitigation plan",
            initialdir=str(folder) if folder.is_dir() else None,
            filetypes=[("Mitigation plans", "*.txt"), ("All files", "*.*")],
        )
        if chosen:
            self.refresh_plans(select=Path(chosen).resolve())

    def _on_combo(self, _event=None) -> None:
        path = self.plans.get(self.plan_var.get())
        if path is not None:
            self.select_plan(path)

    # -- actions -----------------------------------------------------------------
    def start(self) -> None:
        if self.timeline.running or self.plan_path is None:
            return
        if self.load(self.plan_path):  # re-read so edits made in the designer apply
            self.timeline.start()
            self.setup.pack_forget()

    def reset(self) -> None:
        self.timeline.reset()
        self.setup.pack(fill="x", before=self.now.frame)
        self.refresh_plans()

    def quit(self) -> None:
        self._closing = True
        if self._after_id is not None:
            self.root.after_cancel(self._after_id)
        if self._keyboard is not None:
            try:
                self._keyboard.unhook_all_hotkeys()
            except Exception:  # noqa: BLE001 - shutting down anyway
                pass
        self.root.destroy()

    def dispatch(self, action: str) -> None:
        handlers = {
            "start": self.start,
            "next": self.timeline.advance,
            "back": self.timeline.back,
            "reset": self.reset,
            "quit": self.quit,
        }
        handlers[action]()

    def _register_global_hotkeys(self) -> bool:
        try:
            import keyboard
        except Exception:  # noqa: BLE001 - ImportError, or no permission on Linux/macOS
            return False
        try:
            for action, combo in HOTKEYS.items():
                # Called from the keyboard hook thread: only enqueue, Tk is not thread-safe.
                keyboard.add_hotkey(combo, self.actions.put, args=(action,))
        except Exception:  # noqa: BLE001
            keyboard.unhook_all_hotkeys()
            return False
        self._keyboard = keyboard
        return True

    def _bind_window_hotkeys(self) -> None:
        for action, sequence in TK_BINDINGS.items():
            self.root.bind(sequence, lambda _e, a=action: self.actions.put(a))

    # -- rendering ---------------------------------------------------------------
    def _tick(self) -> None:
        while not self._closing:
            try:
                action = self.actions.get_nowait()
            except queue.Empty:
                break
            self.dispatch(action)
        if self._closing:
            return
        self.render()
        self._after_id = self.root.after(TICK_MS, self._tick)

    def render(self) -> None:
        timeline = self.timeline
        self.clock_label.configure(text=format_time(timeline.elapsed()))
        if self.error:
            status, color = self.error, DANGER
        elif not timeline.running:
            status, color = "Press Shift+T on the pull", MUTED
        elif timeline.finished:
            status, color = "Plan complete ✓", ACCENT
        else:
            status = f"{timeline.upcoming_index() + 1} / {len(timeline.mechanics)}"
            color = MUTED
        self.status_label.configure(text=status, fg=color)
        self._fill(self.now, timeline.upcoming(0))
        self._fill(self.then, timeline.upcoming(1))

    def _fill(self, card: SimpleNamespace, mechanic: Mechanic | None) -> None:
        if mechanic is None:
            card.countdown.configure(text="")
            card.name.configure(text="—", fg=MUTED)
            card.mitigation.configure(text="")
            if card.notes is not None:
                card.notes.configure(text="")
            self._draw_bar(card, 1.0 if self.timeline.finished else 0.0, ACCENT)
            return

        if self.timeline.running:
            remaining = self.timeline.time_until(mechanic)
            color = urgency_color(remaining)
            card.countdown.configure(text=format_countdown(remaining), fg=color)
        else:
            color = ACCENT
            card.countdown.configure(text=format_time(mechanic.time), fg=MUTED)
        card.name.configure(text=mechanic.name, fg=FG)
        card.mitigation.configure(text=mechanic.mitigation or "No mitigation planned")
        if card.notes is not None:
            card.notes.configure(text=mechanic.notes)
        self._draw_bar(card, self.timeline.progress() if self.timeline.running else 0.0,
                       ACCENT if color == FG else color)

    @staticmethod
    def _draw_bar(card: SimpleNamespace, fraction: float, color: str) -> None:
        if card.bar is None:
            return
        width, height = card.bar.winfo_width(), card.bar.winfo_height()
        card.bar.coords(card.fill, 0, 0, width * fraction, height)
        card.bar.itemconfigure(card.fill, fill=color)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="mitigation-overlay",
        description="Always-on-top FFXIV overlay that walks you through your mitigation plan.",
    )
    parser.add_argument("plan", nargs="?", type=Path, help="plan file to preselect")
    parser.add_argument("--opacity", type=float, default=0.85, help="0.2-1.0 (default 0.85)")
    parser.add_argument("--no-topmost", action="store_true", help="don't keep the window on top")
    parser.add_argument("--no-global-hotkeys", action="store_true",
                        help="only react to hotkeys while the overlay is focused")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    args = parser.parse_args(argv)

    theme.enable_dpi_awareness()
    root = tk.Tk()
    theme.setup_window(root, "KonyAHS.MitigationTimeline.Overlay")
    Overlay(
        root,
        plan=args.plan.resolve() if args.plan else None,
        opacity=args.opacity,
        topmost=not args.no_topmost,
        global_hotkeys=not args.no_global_hotkeys,
    )
    root.mainloop()


if __name__ == "__main__":
    main()
