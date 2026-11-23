"""Pure fight-timeline logic (no GUI), driven by an injectable clock."""

from __future__ import annotations

import time
from collections.abc import Callable, Iterable

from mitigation_timeline.plan import Mechanic


class Timeline:
    """Tracks the fight clock and which mechanic is coming up next.

    The *upcoming* mechanic is the first one whose time is still in the future.
    Stepping forward means "the upcoming mechanic is happening right now", which
    re-syncs the clock to that mechanic - handy when the boss is early or late.
    """

    def __init__(self, mechanics: Iterable[Mechanic] = (),
                 clock: Callable[[], float] = time.monotonic) -> None:
        self.clock = clock
        self.mechanics: list[Mechanic] = []
        self._start: float | None = None
        self.load(mechanics)

    def load(self, mechanics: Iterable[Mechanic]) -> None:
        self.mechanics = sorted(mechanics, key=lambda m: m.time)
        self.reset()

    # -- clock -----------------------------------------------------------------
    @property
    def running(self) -> bool:
        return self._start is not None

    def start(self) -> None:
        if not self.running:
            self._start = self.clock()

    def reset(self) -> None:
        self._start = None

    def elapsed(self) -> float:
        if self._start is None:
            return 0.0
        return max(0.0, self.clock() - self._start)

    def seek(self, seconds: float) -> None:
        self._start = self.clock() - max(0.0, seconds)

    # -- mechanics ---------------------------------------------------------------
    def upcoming_index(self) -> int:
        elapsed = self.elapsed()
        for index, mechanic in enumerate(self.mechanics):
            if mechanic.time > elapsed:
                return index
        return len(self.mechanics)

    def upcoming(self, offset: int = 0) -> Mechanic | None:
        index = self.upcoming_index() + offset
        return self.mechanics[index] if 0 <= index < len(self.mechanics) else None

    def time_until(self, mechanic: Mechanic) -> float:
        return mechanic.time - self.elapsed()

    def progress(self) -> float:
        """Fraction (0..1) of the way from the previous mechanic to the upcoming one."""
        index = self.upcoming_index()
        if index >= len(self.mechanics):
            return 1.0
        previous = self.mechanics[index - 1].time if index > 0 else 0
        span = self.mechanics[index].time - previous
        if span <= 0:
            return 1.0
        return min(1.0, max(0.0, (self.elapsed() - previous) / span))

    @property
    def finished(self) -> bool:
        return self.running and self.upcoming_index() >= len(self.mechanics)

    def advance(self) -> None:
        """Mark the upcoming mechanic as happening now."""
        if not self.running:
            return
        index = self.upcoming_index()
        if index < len(self.mechanics):
            self.seek(self.mechanics[index].time)

    def back(self) -> None:
        """Undo one step: the previously resolved mechanic becomes upcoming again."""
        if not self.running:
            return
        index = self.upcoming_index()
        self.seek(self.mechanics[index - 2].time if index >= 2 else 0)
