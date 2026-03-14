# Student Name: Peter Saleeb
# Student ID: 215605322

"""
Task A: Appointment Timeslot Recommender (Stub)

In this lab, you will design and implement an Appointment Slot Recommender using an LLM assistant
as your primary programming collaborator.

You are asked to implement a Python module that recommends available meeting slots within a
defined working window.

The system must:
  • Accept working hours (start and end time).
  • Accept a list of existing busy intervals.
  • Accept a required meeting duration.
  • Accept an optional buffer time between meetings.
  • Optionally restrict suggestions to a candidate time window.
  • Return chronologically ordered appointment slots that satisfy all constraints.

The system must ensure that:
  • Suggested slots fall within working hours.
  • Suggested slots do not overlap busy intervals.
  • Buffer time is respected when evaluating availability.
  • Output ordering is deterministic under identical inputs.

The module must preserve the following invariants:
  • Returned slots must be at least as long as the required duration.
  • No returned slot may violate buffer constraints.
  • The returned list must reflect the current system state.

The system must correctly handle non-trivial scenarios such as:
  • Adjacent busy intervals.
  • Very small gaps between meetings.
  • Buffers eliminating otherwise valid availability.
  • Overlapping or unsorted busy intervals.
  • A meeting duration longer than any available gap.
  • No availability within the working window.

Output:
  The output consists of the next N valid appointment suggestions in chronological order.
  Behavior must be deterministic under ties (if any).

See the lab handout for full requirements.
"""

from dataclasses import dataclass
from datetime import date, datetime, timedelta, time
from typing import List, Optional


# ---------------- Data Models ----------------

@dataclass(frozen=True)
class TimeWindow:
    """A daily time window (non-wrapping)."""
    start: time
    end: time


@dataclass(frozen=True)
class BusyInterval:
    """A busy interval on a given day."""
    start: time
    end: time


@dataclass(frozen=True)
class Slot:
    """A recommended appointment slot."""
    start_time: time


class InfeasibleSchedule(Exception):
    """Reserved for future versions."""
    pass


# ---------------- Helper Functions ----------------

def _to_datetime(day: date, t: time) -> datetime:
    return datetime.combine(day, t)


def _merge_intervals(intervals: List[tuple]) -> List[tuple]:
    """Merge overlapping or adjacent intervals using [start, end) semantics."""
    if not intervals:
        return []

    intervals.sort(key=lambda x: x[0])
    merged = [intervals[0]]

    for start, end in intervals[1:]:
        last_start, last_end = merged[-1]

        if start <= last_end:  # overlap or adjacency
            merged[-1] = (last_start, max(last_end, end))
        else:
            merged.append((start, end))

    return merged


def _intersect_windows(w1: TimeWindow, w2: TimeWindow) -> Optional[TimeWindow]:
    start = max(w1.start, w2.start)
    end = min(w1.end, w2.end)

    if start >= end:
        return None
    return TimeWindow(start, end)


# ---------------- Core Function ----------------

def suggest_slots(
    day: date,
    working_hours: TimeWindow,
    busy_intervals: List[BusyInterval],
    duration: timedelta,
    max_slots: int,
    buffer: timedelta = timedelta(0),
    candidate_window: Optional[TimeWindow] = None,
    granularity: timedelta = timedelta(minutes=1),
) -> List[Slot]:
    """Suggest up to max_slots valid appointment slots."""

    # ---------------- Input Validation ----------------
    if working_hours.start >= working_hours.end:
        raise ValueError(
            "working_hours.start must be before working_hours.end")
    if duration <= timedelta(0):
        raise ValueError("duration must be positive")
    if granularity <= timedelta(0):
        raise ValueError("granularity must be positive")
    if buffer < timedelta(0):
        raise ValueError("buffer must be non-negative")
    if max_slots < 0:
        raise ValueError("max_slots must be >= 0")
    if candidate_window is not None and candidate_window.start >= candidate_window.end:
        raise ValueError(
            "candidate_window.start must be before candidate_window.end")
    for b in busy_intervals:
        if b.start >= b.end:
            raise ValueError("Busy interval start must be before end")
    if max_slots == 0:
        return []

# ---------------- Determine Effective Window ----------------
    effective_window = working_hours

    if candidate_window is not None:
        intersected = _intersect_windows(working_hours, candidate_window)
        if intersected is None:
            return []  # No overlap → no slots
        effective_window = intersected

    work_start_dt = _to_datetime(day, effective_window.start)
    work_end_dt = _to_datetime(day, effective_window.end)

    # ---------------- Expand Busy Intervals by Buffer ----------------
    expanded = []
    for b in busy_intervals:
        start_dt = max(_to_datetime(day, b.start) - buffer, work_start_dt)
        end_dt = min(_to_datetime(day, b.end) + buffer, work_end_dt)
        if start_dt < end_dt:
            expanded.append((start_dt, end_dt))

    # ---------------- Merge Busy Intervals ----------------
    merged_busy = _merge_intervals(expanded)

    # ---------------- Compute Free Gaps ----------------
    free_gaps = []
    cursor = work_start_dt

    for start, end in merged_busy:
        if end <= work_start_dt:
            continue
        if start >= work_end_dt:
            break
        start = max(start, work_start_dt)
        end = min(end, work_end_dt)
        if cursor < start:
            free_gaps.append((cursor, start))
        cursor = max(cursor, end)

    if cursor < work_end_dt:
        free_gaps.append((cursor, work_end_dt))

    # ---------------- Generate Slots ----------------
    slots: List[Slot] = []

    for gap_start, gap_end in free_gaps:
        # Align first slot to granularity
        offset = (gap_start - work_start_dt) % granularity
        if offset != timedelta(0):
            gap_start += granularity - offset

        current = gap_start
        while current + duration <= gap_end:
            slots.append(Slot(start_time=current.time()))
            if len(slots) >= max_slots:
                break
            current += granularity

        if len(slots) >= max_slots:
            break

    # ---------------- Prioritize Candidate Window ----------------
    if candidate_window is not None:
        in_window = []
        out_window = []
        for s in slots:
            if candidate_window.start <= s.start_time < candidate_window.end:
                in_window.append(s)
            else:
                out_window.append(s)
        slots = in_window + out_window

    # ---------------- Final Deterministic Sort ----------------
    slots.sort(key=lambda s: s.start_time)
    return slots
