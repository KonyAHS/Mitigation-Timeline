"""Spreadsheet-style editor for mitigation plan files."""

from __future__ import annotations

import argparse
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from mitigation_timeline import __version__, theme
from mitigation_timeline.paths import default_plans_dir
from mitigation_timeline.plan import (
    Mechanic,
    PlanError,
    format_time,
    load_plan,
    parse_time,
    save_plan,
)
from mitigation_timeline.theme import BG, SURFACE_HI

# (key, heading, width in points, stretch)
COLUMNS = (
    ("time", "Time", 45, False),
    ("name", "Mechanic", 130, True),
    ("mitigation", "Mitigation", 170, True),
    ("notes", "Notes", 190, True),
)
HINT = "Shift+A add · Enter edit · Del delete · Shift+U/M move · Ctrl+S save"
FILETYPES = [("Mitigation plans", "*.txt"), ("All files", "*.*")]


class MechanicDialog(tk.Toplevel):
    """Modal form to add or edit one mechanic. ``result`` is set on save."""

    def __init__(self, parent: tk.Misc, title: str, mechanic: Mechanic) -> None:
        super().__init__(parent)
        self.result: Mechanic | None = None
        self.withdraw()
        self.title(title)
        self.configure(bg=BG)
        self.transient(parent)
        self.resizable(True, False)

        p = lambda points: theme.px(self, points)  # noqa: E731
        frame = ttk.Frame(self, padding=p(10))
        frame.pack(fill="both", expand=True)
        fields = (
            ("time", "Time (MM:SS)", format_time(mechanic.time)),
            ("name", "Mechanic", mechanic.name),
            ("mitigation", "Mitigation", mechanic.mitigation),
            ("notes", "Notes", mechanic.notes),
        )
        self.vars: dict[str, tk.StringVar] = {}
        self.entries: dict[str, ttk.Entry] = {}
        for row, (key, label, value) in enumerate(fields):
            ttk.Label(frame, text=label).grid(
                row=row, column=0, sticky="w", padx=(0, p(8)), pady=p(3))
            self.vars[key] = tk.StringVar(value=value)
            self.entries[key] = ttk.Entry(frame, textvariable=self.vars[key], width=44)
            self.entries[key].grid(row=row, column=1, sticky="ew", pady=p(3))
        frame.columnconfigure(1, weight=1)

        self.error = ttk.Label(frame, style="Error.TLabel")
        self.error.grid(row=len(fields), column=0, columnspan=2, sticky="w")
        buttons = ttk.Frame(frame)
        buttons.grid(row=len(fields) + 1, column=0, columnspan=2, sticky="e", pady=(p(6), 0))
        ttk.Button(buttons, text="Cancel", command=self.destroy).pack(side="right")
        ttk.Button(buttons, text="Save", style="Accent.TButton", command=self.ok).pack(
            side="right", padx=(0, p(6)))
        self.bind("<Return>", lambda _e: self.ok())
        self.bind("<Escape>", lambda _e: self.destroy())

        self.update_idletasks()
        x = parent.winfo_rootx() + (parent.winfo_width() - self.winfo_reqwidth()) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - self.winfo_reqheight()) // 3
        self.geometry(f"+{max(0, x)}+{max(0, y)}")
        theme.use_dark_title_bar(self)
        self.deiconify()
        focus = self.entries["name" if not mechanic.name else "mitigation"]
        focus.focus_set()
        focus.select_range(0, "end")
        self.grab_set()
        self.wait_window()

    def ok(self) -> None:
        try:
            seconds = parse_time(self.vars["time"].get())
        except PlanError:
            self.error.configure(text="Time must look like MM:SS, for example 01:35.")
            self.entries["time"].focus_set()
            return
        name = self.vars["name"].get().strip()
        if not name:
            self.error.configure(text="Give the mechanic a name.")
            self.entries["name"].focus_set()
            return
        self.result = Mechanic(
            name=name,
            time=seconds,
            mitigation=self.vars["mitigation"].get().strip(),
            notes=self.vars["notes"].get().strip(),
        )
        self.destroy()


class PlanDesigner:
    def __init__(self, root: tk.Tk | tk.Toplevel, path: Path | None = None) -> None:
        self.root = root
        self.path: Path | None = None
        self.dirty = False
        self.message = ""

        root.geometry(f"{theme.px(root, 640)}x{theme.px(root, 330)}")
        root.minsize(theme.px(root, 420), theme.px(root, 220))
        root.protocol("WM_DELETE_WINDOW", self.quit)
        self._build()
        self._bind_keys()
        if path is not None:
            self.open(path)
        self._refresh()

    # -- layout ------------------------------------------------------------------
    def _build(self) -> None:
        root = self.root
        p = lambda points: theme.px(root, points)  # noqa: E731

        toolbar = ttk.Frame(root, padding=(p(6), p(6)))
        toolbar.pack(fill="x")

        def button(text, command, style="TButton"):
            # negative width = minimum width, so short labels get compact buttons
            ttk.Button(toolbar, text=text, command=command, style=style, width=-3).pack(
                side="left", padx=(0, p(3)))

        button("New", self.new)
        button("Open…", self.open)
        button("Save", self.save)
        ttk.Frame(toolbar, width=p(8)).pack(side="left")
        button("+ Add", self.add, "Accent.TButton")
        button("Edit", self.edit)
        button("Delete", self.delete)
        button("▲", lambda: self.move(-1))
        button("▼", lambda: self.move(1))
        button("Sort by time", self.sort)

        body = ttk.Frame(root, padding=(p(6), 0))
        body.pack(fill="both", expand=True)
        self.tree = ttk.Treeview(body, columns=[c[0] for c in COLUMNS], show="headings",
                                 selectmode="browse")
        for key, heading, width, stretch in COLUMNS:
            self.tree.heading(key, text=heading, anchor="w")
            self.tree.column(key, width=p(width), minwidth=p(35), stretch=stretch, anchor="w")
        self.tree.tag_configure("odd", background=SURFACE_HI)
        scroll = ttk.Scrollbar(body, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        self.tree.pack(side="left", fill="both", expand=True)

        status = ttk.Frame(root, padding=(p(6), p(4)))
        status.pack(fill="x")
        self.status = ttk.Label(status, style="Muted.TLabel")
        self.status.pack(side="left")
        ttk.Label(status, text=HINT, style="Muted.TLabel").pack(side="right")

    def _bind_keys(self) -> None:
        bindings = {
            "<Control-n>": self.new,
            "<Control-o>": self.open,
            "<Control-s>": self.save,
            "<Control-S>": self.save_as,  # Ctrl+Shift+S
            "<Shift-A>": self.add,
            "<Shift-E>": self.edit,
            "<Shift-D>": self.delete,
            "<Shift-U>": lambda: self.move(-1),
            "<Shift-M>": lambda: self.move(1),
        }
        for sequence, command in bindings.items():
            self.root.bind(sequence, lambda _e, c=command: c())
        self.tree.bind("<Return>", lambda _e: self.edit())
        self.tree.bind("<Delete>", lambda _e: self.delete())
        self.tree.bind("<Double-1>", self._on_double_click)

    # -- rows --------------------------------------------------------------------
    def _values(self, mechanic: Mechanic) -> tuple[str, str, str, str]:
        return format_time(mechanic.time), mechanic.name, mechanic.mitigation, mechanic.notes

    def _mechanic(self, item: str) -> Mechanic:
        time, name, mitigation, notes = (str(v) for v in self.tree.item(item, "values"))
        return Mechanic(name=name, time=parse_time(time), mitigation=mitigation, notes=notes)

    def mechanics(self) -> list[Mechanic]:
        return [self._mechanic(item) for item in self.tree.get_children()]

    def set_mechanics(self, mechanics: list[Mechanic]) -> None:
        self.tree.delete(*self.tree.get_children())
        for mechanic in mechanics:
            self.tree.insert("", "end", values=self._values(mechanic))

    def _selected(self) -> str | None:
        selection = self.tree.selection()
        if not selection:
            self.message = "Select a row first."
            self._refresh()
            return None
        return selection[0]

    def _select(self, item: str) -> None:
        self.tree.selection_set(item)
        self.tree.focus(item)
        self.tree.see(item)

    def _changed(self, message: str = "") -> None:
        self.dirty = True
        self.message = message
        self._refresh()

    def _on_double_click(self, event: tk.Event) -> None:
        if self.tree.identify_region(event.x, event.y) == "cell":
            self.edit()

    # -- commands ----------------------------------------------------------------
    def add(self) -> None:
        selection = self.tree.selection()
        items = self.tree.get_children()
        anchor = selection[0] if selection else (items[-1] if items else None)
        start = self._mechanic(anchor).time + 5 if anchor else 0
        dialog = MechanicDialog(self.root, "Add mechanic", Mechanic(name="", time=start))
        if dialog.result is None:
            return
        index = self.tree.index(anchor) + 1 if anchor else "end"
        item = self.tree.insert("", index, values=self._values(dialog.result))
        self._select(item)
        self._changed(f"Added {dialog.result.name}.")

    def edit(self) -> None:
        item = self._selected()
        if item is None:
            return
        dialog = MechanicDialog(self.root, "Edit mechanic", self._mechanic(item))
        if dialog.result is not None:
            self.tree.item(item, values=self._values(dialog.result))
            self._changed(f"Updated {dialog.result.name}.")

    def delete(self) -> None:
        item = self._selected()
        if item is None:
            return
        name = self._mechanic(item).name
        neighbour = self.tree.next(item) or self.tree.prev(item)
        self.tree.delete(item)
        if neighbour:
            self._select(neighbour)
        self._changed(f"Deleted {name}.")

    def move(self, delta: int) -> None:
        item = self._selected()
        if item is None:
            return
        index = self.tree.index(item) + delta
        if 0 <= index < len(self.tree.get_children()):
            self.tree.move(item, "", index)
            self._select(item)
            self._changed()

    def sort(self) -> None:
        mechanics = self.mechanics()
        ordered = sorted(mechanics, key=lambda m: m.time)
        if ordered != mechanics:
            self.set_mechanics(ordered)
            self._changed("Sorted by time.")

    def new(self) -> None:
        if self._confirm_discard():
            self.set_mechanics([])
            self.path, self.dirty, self.message = None, False, ""
            self._refresh()

    def open(self, path: Path | None = None) -> None:
        if not self._confirm_discard():
            return
        if path is None:
            folder = default_plans_dir()
            chosen = filedialog.askopenfilename(
                parent=self.root, title="Open mitigation plan", filetypes=FILETYPES,
                initialdir=str(folder) if folder.is_dir() else None)
            if not chosen:
                return
            path = Path(chosen)
        try:
            mechanics = load_plan(path)
        except (OSError, PlanError) as exc:
            messagebox.showerror("Could not open plan", f"{path.name}: {exc}", parent=self.root)
            return
        self.set_mechanics(mechanics)
        self.path, self.dirty, self.message = path, False, f"Opened {path.name}."
        self._refresh()

    def save(self) -> bool:
        if self.path is None:
            return self.save_as()
        try:
            save_plan(self.path, self.mechanics())
        except OSError as exc:
            messagebox.showerror("Could not save plan", str(exc), parent=self.root)
            return False
        self.dirty, self.message = False, f"Saved {self.path.name}."
        self._refresh()
        return True

    def save_as(self) -> bool:
        folder = self.path.parent if self.path else default_plans_dir()
        folder.mkdir(parents=True, exist_ok=True)
        chosen = filedialog.asksaveasfilename(
            parent=self.root, title="Save mitigation plan", filetypes=FILETYPES,
            defaultextension=".txt", initialdir=str(folder),
            initialfile=self.path.name if self.path else "my_plan.txt")
        if not chosen:
            return False
        self.path = Path(chosen)
        return self.save()

    def quit(self) -> None:
        if self._confirm_discard():
            self.root.destroy()

    def _confirm_discard(self) -> bool:
        if not self.dirty:
            return True
        answer = messagebox.askyesnocancel(
            "Unsaved changes", f"Save changes to {self.path.name if self.path else 'this plan'}?",
            parent=self.root)
        if answer is None:
            return False
        return self.save() if answer else True

    # -- status ------------------------------------------------------------------
    def _refresh(self) -> None:
        items = self.tree.get_children()
        for index, item in enumerate(items):
            self.tree.item(item, tags=("odd",) if index % 2 else ())
        name = self.path.name if self.path else "Untitled"
        self.root.title(f"{'● ' if self.dirty else ''}{name} — Mitigation Plan Designer")
        summary = f"{len(items)} mechanic{'s' if len(items) != 1 else ''}"
        if items:
            summary += f" · last at {format_time(max(m.time for m in self.mechanics()))}"
        self.status.configure(text=f"{summary}   {self.message}".rstrip())


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="mitigation-designer",
                                     description="Create and edit mitigation plan files.")
    parser.add_argument("plan", nargs="?", type=Path, help="plan file to open")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    args = parser.parse_args(argv)

    theme.enable_dpi_awareness()
    root = tk.Tk()
    theme.setup_window(root, "KonyAHS.MitigationTimeline.Designer")
    PlanDesigner(root, args.plan)
    root.mainloop()


if __name__ == "__main__":
    main()
