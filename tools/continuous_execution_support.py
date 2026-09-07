"""Exact access footprints and fail-closed continuity checks for a separate study."""
from __future__ import annotations


def access_offsets(horizon: int, lookahead: tuple[int, ...] = (0,)) -> tuple[int, ...]:
    """Include initial/terminal observations and every declared reference offset."""
    if type(horizon) is not int or horizon < 1 or not lookahead:
        raise ValueError('positive integer horizon and explicit lookahead required')
    if any(type(offset) is not int for offset in lookahead):
        raise ValueError('lookahead offsets must be integers')
    return tuple(sorted({step + offset for step in range(horizon + 1)
                         for offset in (0, *lookahead)}))


def legal_starts(start: int, stop: int, horizon: int,
                 lookahead: tuple[int, ...] = (0,)) -> range:
    """Return starts contained in this one half-open admitted interval."""
    if type(start) is not int or type(stop) is not int or not 0 <= start < stop:
        raise ValueError('invalid admitted interval')
    offsets = access_offsets(horizon, lookahead)
    return range(start - min(offsets), max(start - min(offsets), stop - max(offsets)))


def verify_transition(before: list[int], after: list[int], active: list[bool],
                      starts: list[int], stops: list[int], step: int,
                      lookahead: tuple[int, ...] = (0,)) -> None:
    """Require monotone single-frame access through the terminal observation."""
    if not (len(before) == len(after) == len(active) == len(starts) == len(stops)):
        raise ValueError('world count mismatch')
    for b, a, live, first, stop in zip(before, after, active, starts, stops, strict=True):
        if live and (b != first + step - 1 or a != first + step
                     or min(b, a) + min(0, *lookahead) < first
                     or max(b, a) + max(0, *lookahead) >= stop):
            raise ValueError('active reference skipped, wrapped or escaped support')


def permit_reset(ids: list[int], active: list[bool]) -> None:
    """Retired worlds may reset for vector housekeeping; scored worlds may not."""
    if any(active[index] for index in ids):
        raise ValueError('reset or reference-state write inside a scored attempt')
