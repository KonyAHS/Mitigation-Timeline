from mitigation_timeline.plan import Mechanic
from mitigation_timeline.timeline import Timeline


class FakeClock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


def make():
    clock = FakeClock()
    mechanics = [Mechanic("C", 30), Mechanic("A", 10), Mechanic("B", 20)]
    return clock, Timeline(mechanics, clock=clock)


def test_sorted_and_idle_until_started():
    clock, tl = make()
    assert [m.name for m in tl.mechanics] == ["A", "B", "C"]
    clock.now += 50
    assert not tl.running
    assert tl.elapsed() == 0
    assert tl.upcoming().name == "A"


def test_auto_progress_with_clock():
    clock, tl = make()
    tl.start()
    clock.now += 4
    assert tl.upcoming().name == "A"
    assert tl.time_until(tl.upcoming()) == 6
    assert tl.upcoming(1).name == "B"
    assert tl.progress() == 0.4
    clock.now += 6  # exactly at A -> A has happened
    assert tl.upcoming().name == "B"
    clock.now += 100
    assert tl.upcoming() is None
    assert tl.finished


def test_advance_resyncs_clock_to_upcoming_mechanic():
    clock, tl = make()
    tl.start()
    clock.now += 3
    tl.advance()  # boss did A early
    assert tl.elapsed() == 10
    assert tl.upcoming().name == "B"


def test_back_undoes_one_step():
    clock, tl = make()
    tl.start()
    clock.now += 15  # A done, B upcoming
    tl.back()
    assert tl.upcoming().name == "A"
    assert tl.elapsed() == 0
    tl.advance()
    tl.advance()
    assert tl.upcoming().name == "C"
    tl.back()
    assert tl.upcoming().name == "B"
    assert tl.elapsed() == 10


def test_steps_ignored_before_start_and_reset_stops():
    clock, tl = make()
    tl.advance()
    tl.back()
    assert not tl.running
    tl.start()
    clock.now += 12
    tl.reset()
    assert not tl.running and tl.upcoming().name == "A"
