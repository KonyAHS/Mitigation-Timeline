from pathlib import Path

import pytest

from mitigation_timeline.plan import (
    Mechanic,
    PlanError,
    format_plan,
    format_time,
    load_plan,
    looks_like_plan,
    parse_plan,
    parse_time,
    save_plan,
)

EXAMPLE = Path(__file__).resolve().parents[1] / "plans" / "example.txt"


def test_parse_time():
    assert parse_time("00:05") == 5
    assert parse_time("1:30") == 90
    assert parse_time(" 10:00 ") == 600


@pytest.mark.parametrize("bad", ["", "5", "00:60", "aa:bb", "-1:00"])
def test_parse_time_rejects_bad_input(bad):
    with pytest.raises(PlanError):
        parse_time(bad)


def test_format_time():
    assert format_time(0) == "00:00"
    assert format_time(95) == "01:35"
    assert format_time(-3) == "00:00"


def test_parse_plan_reads_blocks_and_tolerates_noise():
    text = """
    # comment
    Mechanic: Tankbuster: big one
    Notes: ouch
    Mitigation: Rampart + Reprisal
    Time: 00:05
    random line

    mechanic: Raidwide
    Time: 0:20
    """
    assert parse_plan(text) == [
        Mechanic(name="Tankbuster: big one", time=5, mitigation="Rampart + Reprisal",
                 notes="ouch"),
        Mechanic(name="Raidwide", time=20),
    ]


def test_parse_plan_errors_name_the_line():
    with pytest.raises(PlanError, match="line 1.*no 'Time:'"):
        parse_plan("Mechanic: Oops\nNotes: x\n")
    with pytest.raises(PlanError, match="before any 'Mechanic:'"):
        parse_plan("Time: 00:10\n")


def test_round_trip(tmp_path):
    mechanics = [Mechanic("A", 5, "Rampart", "multi\nline  notes"), Mechanic("B", 125)]
    path = tmp_path / "plan.txt"
    save_plan(path, mechanics)
    loaded = load_plan(path)
    assert loaded[0].notes == "multi line notes"
    assert [m.time for m in loaded] == [5, 125]
    assert format_plan(loaded) == path.read_text("utf-8")


def test_example_plan_loads():
    mechanics = load_plan(EXAMPLE)
    assert len(mechanics) >= 4
    assert looks_like_plan(EXAMPLE)


def test_looks_like_plan_ignores_other_txt(tmp_path):
    other = tmp_path / "requirements.txt"
    other.write_text("keyboard\n")
    assert not looks_like_plan(other)
