"""Reading and writing mitigation plan files.

A plan is a plain-text file made of blocks like::

    Mechanic: Tankbuster 1
    Notes: Single target heavy damage on tank
    Mitigation: Rampart + Reprisal
    Time: 00:05

Blocks are separated by blank lines, ``#`` starts a comment line and unknown
lines are ignored. ``Time`` is required and counts from the pull (MM:SS).
"""

from __future__ import annotations

import locale
import re
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

_TIME_RE = re.compile(r"^\s*(\d{1,3}):([0-5]\d)\s*$")
_FIELDS = {"mechanic": "name", "notes": "notes", "mitigation": "mitigation", "time": "time"}


class PlanError(ValueError):
    """Raised when a plan file cannot be understood."""


@dataclass
class Mechanic:
    name: str
    time: int  # seconds since the pull
    mitigation: str = ""
    notes: str = ""


def parse_time(text: str) -> int:
    """Convert ``MM:SS`` (or ``M:SS``) to seconds."""
    match = _TIME_RE.match(text)
    if not match:
        raise PlanError(f"invalid time {text.strip()!r}, expected MM:SS")
    return int(match[1]) * 60 + int(match[2])


def format_time(seconds: float) -> str:
    """Convert seconds to ``MM:SS``."""
    seconds = max(0, int(seconds))
    return f"{seconds // 60:02}:{seconds % 60:02}"


def parse_plan(text: str) -> list[Mechanic]:
    blocks: list[tuple[int, dict[str, str]]] = []
    for lineno, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        key, sep, value = line.partition(":")
        field = _FIELDS.get(key.strip().lower())
        if not sep or field is None:
            continue  # tolerate stray lines, like the original parser did
        value = value.strip()
        if field == "name":
            blocks.append((lineno, {"name": value}))
        elif not blocks:
            raise PlanError(f"line {lineno}: '{key.strip()}' appears before any 'Mechanic:' line")
        else:
            blocks[-1][1][field] = value

    mechanics = []
    for lineno, block in blocks:
        if "time" not in block:
            raise PlanError(f"line {lineno}: mechanic {block['name']!r} has no 'Time:'")
        try:
            seconds = parse_time(block["time"])
        except PlanError as exc:
            raise PlanError(f"line {lineno}: mechanic {block['name']!r}: {exc}") from None
        mechanics.append(
            Mechanic(
                name=block["name"],
                time=seconds,
                mitigation=block.get("mitigation", ""),
                notes=block.get("notes", ""),
            )
        )
    return mechanics


def _one_line(text: str) -> str:
    return " ".join(str(text).split())


def format_plan(mechanics: Iterable[Mechanic]) -> str:
    return "".join(
        f"Mechanic: {_one_line(m.name)}\n"
        f"Notes: {_one_line(m.notes)}\n"
        f"Mitigation: {_one_line(m.mitigation)}\n"
        f"Time: {format_time(m.time)}\n\n"
        for m in mechanics
    )


def read_text(path: str | Path) -> str:
    """Read a text file as UTF-8, falling back to the system code page (older plans)."""
    data = Path(path).read_bytes()
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return data.decode(locale.getpreferredencoding(False), errors="replace")


def load_plan(path: str | Path) -> list[Mechanic]:
    return parse_plan(read_text(path))


def save_plan(path: str | Path, mechanics: Iterable[Mechanic]) -> None:
    Path(path).write_text(format_plan(mechanics), encoding="utf-8")


def looks_like_plan(path: Path) -> bool:
    try:
        with path.open("rb") as fh:
            head = fh.read(4096).lower()
    except OSError:
        return False
    return b"mechanic:" in head and b"time:" in head
