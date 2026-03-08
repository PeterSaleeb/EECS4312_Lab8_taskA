import pytest
from datetime import date, datetime, time, timedelta

from solution import TimeWindow, BusyInterval, Slot, suggest_slots


# ---------- Helpers ----------

def combine(d: date, t: time) -> datetime:
    return datetime.combine(d, t)


def overlaps(a_start: datetime, a_end: datetime, b_start: datetime, b_end: datetime) -> bool:
    return a_start < b_end and b_start < a_end


def in_window(win: TimeWindow, t: time) -> bool:
    return win.start <= t < win.end


def assert_slots_basic_constraints(
    slots,
    day,
    working_hours,
    busy_intervals,
    duration,
    max_slots,
    buffer,
    candidate_window,
):
    assert isinstance(slots, list)
    assert len(slots) <= max_slots

    assert slots == sorted(slots, key=lambda s: s.start_time)

    for s in slots:
        assert in_window(working_hours, s.start_time)
        if candidate_window is not None:
            assert in_window(candidate_window, s.start_time)

    for s in slots:
        start_dt = combine(day, s.start_time)
        end_dt = start_dt + duration

        wh_end = combine(day, working_hours.end)
        assert end_dt <= wh_end

        if candidate_window is not None:
            cw_end = combine(day, candidate_window.end)
            assert end_dt <= cw_end

    for s in slots:
        slot_start = combine(day, s.start_time)
        slot_end = slot_start + duration

        for b in busy_intervals:
            b_start = combine(day, b.start) - buffer
            b_end = combine(day, b.end) + buffer
            assert not overlaps(slot_start, slot_end, b_start, b_end)


# ---------- Base Setup ----------

DAY = date(2026, 2, 24)


# ---------- Core Functional Tests ----------

def test_empty_schedule_returns_slots():
    working = TimeWindow(time(9, 0), time(12, 0))
    busy = []
    duration = timedelta(minutes=30)

    out = suggest_slots(DAY, working, busy, duration, max_slots=5)

    assert len(out) > 0
    assert_slots_basic_constraints(
        out, DAY, working, busy, duration, 5, timedelta(0), None)


def test_completely_busy_returns_empty():
    working = TimeWindow(time(9, 0), time(17, 0))
    busy = [BusyInterval(time(9, 0), time(17, 0))]
    duration = timedelta(minutes=30)

    out = suggest_slots(DAY, working, busy, duration, max_slots=10)

    assert out == []


def test_slots_within_working_hours():
    working = TimeWindow(time(9, 0), time(11, 0))
    busy = []
    duration = timedelta(minutes=30)

    out = suggest_slots(DAY, working, busy, duration, max_slots=10)

    assert all(time(9, 0) <= s.start_time < time(11, 0) for s in out)


def test_unordered_busy_intervals():
    working = TimeWindow(time(9, 0), time(12, 0))
    busy1 = [
        BusyInterval(time(11, 0), time(11, 30)),
        BusyInterval(time(9, 30), time(10, 0)),
    ]

    busy2 = list(reversed(busy1))

    duration = timedelta(minutes=15)

    out1 = suggest_slots(DAY, working, busy1, duration, max_slots=10)
    out2 = suggest_slots(DAY, working, busy2, duration, max_slots=10)

    assert [s.start_time for s in out1] == [s.start_time for s in out2]


def test_output_chronological_order():
    working = TimeWindow(time(9, 0), time(12, 0))
    duration = timedelta(minutes=20)

    out = suggest_slots(DAY, working, [], duration, max_slots=10)

    times = [s.start_time for s in out]
    assert times == sorted(times)


# ---------- Buffer Tests ----------

def test_buffer_expansion_blocks_slots():
    working = TimeWindow(time(9, 0), time(11, 0))
    busy = [BusyInterval(time(10, 0), time(10, 30))]
    duration = timedelta(minutes=15)

    no_buffer = suggest_slots(DAY, working, busy, duration, max_slots=20)

    buffer = timedelta(minutes=10)
    with_buffer = suggest_slots(
        DAY, working, busy, duration, max_slots=20, buffer=buffer)

    assert len(with_buffer) <= len(no_buffer)


def test_buffer_large_blocks_all():
    working = TimeWindow(time(9, 0), time(11, 0))
    busy = [BusyInterval(time(10, 0), time(10, 10))]
    duration = timedelta(minutes=30)

    buffer = timedelta(minutes=300)

    out = suggest_slots(DAY, working, busy, duration,
                        max_slots=10, buffer=buffer)

    assert out == []


# ---------- Candidate Window Tests ----------

def test_candidate_window_filters_slots():
    working = TimeWindow(time(9, 0), time(17, 0))
    candidate = TimeWindow(time(13, 0), time(14, 0))

    out = suggest_slots(
        DAY,
        working,
        [],
        timedelta(minutes=20),
        max_slots=10,
        candidate_window=candidate,
    )

    assert all(candidate.start <= s.start_time < candidate.end for s in out)


def test_candidate_window_intersection_with_working_hours():
    working = TimeWindow(time(9, 0), time(17, 0))
    candidate = TimeWindow(time(7, 0), time(10, 0))

    out = suggest_slots(
        DAY,
        working,
        [],
        timedelta(minutes=15),
        max_slots=10,
        candidate_window=candidate,
    )

    assert all(time(9, 0) <= s.start_time < time(10, 0) for s in out)


def test_candidate_window_outside_working_hours_returns_empty():
    working = TimeWindow(time(9, 0), time(17, 0))
    candidate = TimeWindow(time(6, 0), time(8, 0))

    out = suggest_slots(
        DAY,
        working,
        [],
        timedelta(minutes=30),
        max_slots=10,
        candidate_window=candidate,
    )

    assert out == []


# ---------- Duration Edge Cases ----------

def test_duration_exact_gap():
    working = TimeWindow(time(9, 0), time(10, 0))
    busy = [BusyInterval(time(9, 30), time(10, 0))]
    duration = timedelta(minutes=30)

    out = suggest_slots(DAY, working, busy, duration, max_slots=5)

    assert any(s.start_time == time(9, 0) for s in out)


def test_duration_larger_than_any_gap():
    working = TimeWindow(time(9, 0), time(12, 0))
    busy = [
        BusyInterval(time(9, 0), time(10, 0)),
        BusyInterval(time(10, 30), time(11, 30)),
    ]
    duration = timedelta(minutes=45)

    out = suggest_slots(DAY, working, busy, duration, max_slots=5)

    assert out == []


def test_duration_equals_workday():
    working = TimeWindow(time(9, 0), time(17, 0))
    duration = timedelta(hours=8)

    out = suggest_slots(DAY, working, [], duration, max_slots=5)

    assert len(out) == 1
    assert out[0].start_time == time(9, 0)


# ---------- Interval Merging Tests ----------

def test_overlapping_busy_intervals_merged():
    working = TimeWindow(time(9, 0), time(12, 0))
    busy = [
        BusyInterval(time(10, 0), time(10, 30)),
        BusyInterval(time(10, 15), time(11, 0)),
    ]

    duration = timedelta(minutes=15)

    out = suggest_slots(DAY, working, busy, duration, max_slots=10)

    assert_slots_basic_constraints(
        out, DAY, working, busy, duration, 10, timedelta(0), None)


def test_adjacent_busy_intervals_merged():
    working = TimeWindow(time(9, 0), time(12, 0))
    busy = [
        BusyInterval(time(10, 0), time(11, 0)),
        BusyInterval(time(11, 0), time(12, 0)),
    ]

    duration = timedelta(minutes=20)

    out = suggest_slots(DAY, working, busy, duration, max_slots=10)

    assert all(s.start_time < time(10, 0) for s in out)


# ---------- Granularity Tests ----------

def test_granularity_changes_slot_count():
    working = TimeWindow(time(9, 0), time(10, 0))
    duration = timedelta(minutes=10)

    out1 = suggest_slots(
        DAY,
        working,
        [],
        duration,
        max_slots=50,
        granularity=timedelta(minutes=1),
    )

    out5 = suggest_slots(
        DAY,
        working,
        [],
        duration,
        max_slots=50,
        granularity=timedelta(minutes=5),
    )

    assert len(out1) >= len(out5)


# ---------- max_slots Limit ----------

def test_max_slots_limit_respected():
    working = TimeWindow(time(9, 0), time(17, 0))
    duration = timedelta(minutes=10)

    out = suggest_slots(DAY, working, [], duration, max_slots=3)

    assert len(out) <= 3


# ---------- Determinism ----------

def test_same_inputs_same_outputs():
    working = TimeWindow(time(9, 0), time(17, 0))
    busy = [BusyInterval(time(11, 0), time(12, 0))]

    duration = timedelta(minutes=20)

    out1 = suggest_slots(DAY, working, busy, duration, max_slots=10)
    out2 = suggest_slots(DAY, working, busy, duration, max_slots=10)

    assert [s.start_time for s in out1] == [s.start_time for s in out2]


# ---------- Invalid Input Tests ----------

def test_invalid_working_hours():
    with pytest.raises(ValueError):
        suggest_slots(
            DAY,
            TimeWindow(time(12, 0), time(9, 0)),
            [],
            timedelta(minutes=30),
            max_slots=5,
        )


def test_invalid_busy_interval():
    with pytest.raises(ValueError):
        suggest_slots(
            DAY,
            TimeWindow(time(9, 0), time(17, 0)),
            [BusyInterval(time(11, 0), time(10, 0))],
            timedelta(minutes=30),
            max_slots=5,
        )


def test_invalid_duration():
    with pytest.raises(ValueError):
        suggest_slots(
            DAY,
            TimeWindow(time(9, 0), time(17, 0)),
            [],
            timedelta(0),
            max_slots=5,
        )


def test_invalid_granularity():
    with pytest.raises(ValueError):
        suggest_slots(
            DAY,
            TimeWindow(time(9, 0), time(17, 0)),
            [],
            timedelta(minutes=30),
            max_slots=5,
            granularity=timedelta(0),
        )
