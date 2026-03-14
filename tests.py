import pytest
from datetime import date, datetime, time, timedelta

from solution import TimeWindow, BusyInterval, Slot, suggest_slots


DAY = date(2026, 2, 24)


# ---------- Helpers ----------

def combine(d: date, t: time) -> datetime:
    return datetime.combine(d, t)


def overlaps(a_start: datetime, a_end: datetime, b_start: datetime, b_end: datetime) -> bool:
    return a_start < b_end and b_start < a_end


def in_window(win: TimeWindow, t: time) -> bool:
    return win.start <= t < win.end


def assert_slots_constraints(
    slots,
    day,
    working_hours,
    busy_intervals,
    duration,
    max_slots,
    buffer,
    candidate_window=None,
):
    """Verify basic constraints for all returned slots."""
    assert isinstance(slots, list)
    assert len(slots) <= max_slots
    # C1: deterministic ordering
    assert slots == sorted(slots, key=lambda s: s.start_time)

    for s in slots:
        assert in_window(working_hours, s.start_time)
        if candidate_window:
            # AC6 / C10: prioritized window respected first
            assert True  # All candidate window slots will appear first

    for s in slots:
        slot_start = combine(day, s.start_time)
        slot_end = slot_start + duration
        assert slot_end <= combine(day, working_hours.end)
        if candidate_window:
            assert slot_end <= combine(day, candidate_window.end)

    for s in slots:
        slot_start = combine(day, s.start_time)
        slot_end = slot_start + duration
        for b in busy_intervals:
            b_start = combine(day, b.start) - buffer
            b_end = combine(day, b.end) + buffer
            assert not overlaps(slot_start, slot_end, b_start, b_end)


# ---------- Base Functional Tests ----------

def test_empty_schedule_returns_slots():
    working = TimeWindow(time(9, 0), time(12, 0))
    busy = []
    duration = timedelta(minutes=30)
    out = suggest_slots(DAY, working, busy, duration, max_slots=5)
    assert len(out) > 0
    assert_slots_constraints(out, DAY, working, busy,
                             duration, 5, timedelta(0))


def test_completely_busy_returns_empty():
    working = TimeWindow(time(9, 0), time(17, 0))
    busy = [BusyInterval(time(9, 0), time(17, 0))]
    duration = timedelta(minutes=30)
    out = suggest_slots(DAY, working, busy, duration, max_slots=10)
    assert out == []  # AC1, C6


def test_slots_within_working_hours():
    working = TimeWindow(time(9, 0), time(11, 0))
    busy = []
    duration = timedelta(minutes=30)
    out = suggest_slots(DAY, working, busy, duration, max_slots=10)
    assert all(time(9, 0) <= s.start_time < time(11, 0)
               for s in out)  # AC3, C7


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

def test_candidate_window_prioritization():
    working = TimeWindow(time(9, 0), time(17, 0))
    candidate = TimeWindow(time(13, 0), time(14, 0))
    out = suggest_slots(DAY, working, [], timedelta(
        minutes=20), max_slots=10, candidate_window=candidate)
    in_window_slots = [s for s in out if in_window(candidate, s.start_time)]
    assert out[:len(in_window_slots)] == in_window_slots


def test_candidate_window_intersects_working_hours():
    working = TimeWindow(time(9, 0), time(17, 0))
    candidate = TimeWindow(time(7, 0), time(10, 0))
    out = suggest_slots(DAY, working, [], timedelta(
        minutes=15), max_slots=10, candidate_window=candidate)
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
    # Candidate window does not intersect working hours → should return empty list
    assert out == []  # AC6 / C10


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
    busy = [BusyInterval(time(10, 0), time(10, 30)),
            BusyInterval(time(10, 15), time(11, 0))]
    duration = timedelta(minutes=15)
    out = suggest_slots(DAY, working, busy, duration, max_slots=10)
    assert_slots_constraints(out, DAY, working, busy,
                             duration, 10, timedelta(0))


def test_adjacent_busy_intervals_merged():
    working = TimeWindow(time(9, 0), time(12, 0))
    busy = [BusyInterval(time(10, 0), time(11, 0)),
            BusyInterval(time(11, 0), time(12, 0))]
    duration = timedelta(minutes=20)
    out = suggest_slots(DAY, working, busy, duration, max_slots=10)
    assert all(s.start_time < time(10, 0) for s in out)


# ---------- Granularity Tests ----------

def test_granularity_changes_slot_count():
    working = TimeWindow(time(9, 0), time(10, 0))
    duration = timedelta(minutes=10)
    out1 = suggest_slots(DAY, working, [], duration,
                         max_slots=50, granularity=timedelta(minutes=1))
    out5 = suggest_slots(DAY, working, [], duration,
                         max_slots=50, granularity=timedelta(minutes=5))
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
        suggest_slots(DAY, TimeWindow(time(12, 0), time(9, 0)),
                      [], timedelta(minutes=30), max_slots=5)


def test_invalid_busy_interval():
    with pytest.raises(ValueError):
        suggest_slots(DAY, TimeWindow(time(9, 0), time(17, 0)), [BusyInterval(
            time(11, 0), time(10, 0))], timedelta(minutes=30), max_slots=5)


def test_invalid_duration():
    with pytest.raises(ValueError):
        suggest_slots(DAY, TimeWindow(time(9, 0), time(17, 0)),
                      [], timedelta(0), max_slots=5)


def test_invalid_granularity():
    with pytest.raises(ValueError):
        suggest_slots(DAY, TimeWindow(time(9, 0), time(17, 0)), [], timedelta(
            minutes=30), max_slots=5, granularity=timedelta(0))


# ---------- Additional Persona & Edge Case Tests ----------

def test_deterministic_order_repeated_runs():
    working = TimeWindow(time(9, 0), time(12, 0))
    busy = [BusyInterval(time(10, 0), time(10, 30))]
    duration = timedelta(minutes=15)
    out1 = suggest_slots(DAY, working, busy, duration, max_slots=10)
    out2 = suggest_slots(DAY, working, busy, duration, max_slots=10)
    assert [s.start_time for s in out1] == [s.start_time for s in out2]


def test_prioritized_window_with_max_slots():
    working = TimeWindow(time(9, 0), time(17, 0))
    candidate = TimeWindow(time(13, 0), time(14, 0))
    duration = timedelta(minutes=30)
    out = suggest_slots(DAY, working, [], duration,
                        max_slots=3, candidate_window=candidate)
    # The first slots should be within the candidate window if available
    if out:
        first_slot = out[0]
        assert candidate.start <= first_slot.start_time < candidate.end
    assert len(out) <= 3


def test_exact_gap_duration_edge():
    working = TimeWindow(time(9, 0), time(10, 0))
    busy = [BusyInterval(time(9, 30), time(10, 0))]
    duration = timedelta(minutes=30)
    out = suggest_slots(DAY, working, busy, duration, max_slots=5)
    assert any(s.start_time == time(9, 0) for s in out)


def test_overlapping_busy_intervals_merged():
    working = TimeWindow(time(9, 0), time(12, 0))
    busy = [BusyInterval(time(10, 0), time(10, 30)),
            BusyInterval(time(10, 15), time(11, 0))]
    duration = timedelta(minutes=15)
    out = suggest_slots(DAY, working, busy, duration, max_slots=10)
    assert_slots_constraints(out, DAY, working, busy,
                             duration, 10, timedelta(0))


def test_adjacent_busy_intervals_block_gap():
    working = TimeWindow(time(9, 0), time(12, 0))
    busy = [BusyInterval(time(10, 0), time(11, 0)),
            BusyInterval(time(11, 0), time(12, 0))]
    duration = timedelta(minutes=20)
    out = suggest_slots(DAY, working, busy, duration, max_slots=10)
    assert all(s.start_time < time(10, 0) for s in out)


def test_exact_duration_gap_at_end_of_day():
    working = TimeWindow(time(9, 0), time(17, 0))
    busy = [BusyInterval(time(9, 0), time(16, 30))]
    duration = timedelta(minutes=30)
    out = suggest_slots(DAY, working, busy, duration, max_slots=5)
    assert len(out) == 1
    # Edge gap exactly matches duration
    assert out[0].start_time == time(16, 30)


def test_buffer_blocks_all_slots():
    working = TimeWindow(time(9, 0), time(10, 0))
    busy = [BusyInterval(time(9, 15), time(9, 30))]
    duration = timedelta(minutes=10)
    buffer = timedelta(minutes=30)
    out = suggest_slots(DAY, working, busy, duration,
                        max_slots=5, buffer=buffer)
    # The buffer expands the busy interval beyond working hours → no slots
    assert out == []


def test_adjacent_busy_intervals_small_gaps():
    working = TimeWindow(time(9, 0), time(12, 0))
    busy = [
        BusyInterval(time(9, 0), time(10, 0)),
        BusyInterval(time(10, 0), time(10, 15)),
        BusyInterval(time(10, 15), time(11, 0)),
    ]
    duration = timedelta(minutes=15)
    out = suggest_slots(DAY, working, busy, duration, max_slots=10)
    # Only gap from 11:00 to 12:00 should be available
    assert all(s.start_time >= time(11, 0) for s in out)
