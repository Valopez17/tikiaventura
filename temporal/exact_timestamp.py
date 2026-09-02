"""Exact calendar-time lookup. Missing t−L is ineligible. No nearest-bar fallback."""

from __future__ import annotations

import pandas as pd
import numpy as np


def as_utc_index(ts: pd.DatetimeIndex | pd.Series) -> pd.DatetimeIndex:
    idx = pd.DatetimeIndex(ts)
    if idx.tz is None:
        idx = idx.tz_localize("UTC")
    else:
        idx = idx.tz_convert("UTC")
    return idx


def lookup_exact(ts: pd.DatetimeIndex, target: pd.Timestamp) -> int | None:
    """Index of `target` if that exact UTC timestamp exists, else None."""
    ts = as_utc_index(ts)
    target = pd.Timestamp(target)
    if target.tzinfo is None:
        target = target.tz_localize("UTC")
    else:
        target = target.tz_convert("UTC")
    loc = ts.get_indexer(pd.DatetimeIndex([target]))
    i = int(loc[0])
    return i if i >= 0 else None


def lookback_index(ts: pd.DatetimeIndex, t: pd.Timestamp, lookback: pd.Timedelta) -> int | None:
    """Index of exact timestamp t − lookback, or None if that bar is missing."""
    return lookup_exact(ts, pd.Timestamp(t) - lookback)


def ahead_index(ts: pd.DatetimeIndex, t: pd.Timestamp, delta: pd.Timedelta) -> int | None:
    """Index of exact timestamp t + delta, or None if that bar is missing."""
    return lookup_exact(ts, pd.Timestamp(t) + delta)


def window_indices_excluding_t(
    ts: pd.DatetimeIndex,
    t: pd.Timestamp,
    lookback: pd.Timedelta,
    require_complete: bool = True,
) -> list[int] | None:
    """Indices with timestamp in [t − lookback, t).

    If require_complete, every expected hourly bar in that interval must exist;
    otherwise return None (observation ineligible). Current bar t is excluded.
    """
    ts = as_utc_index(ts)
    t = pd.Timestamp(t)
    if t.tzinfo is None:
        t = t.tz_localize("UTC")
    else:
        t = t.tz_convert("UTC")
    start = t - lookback
    if lookup_exact(ts, start) is None:
        return None
    if require_complete:
        expected = pd.date_range(start, t, freq="h", inclusive="left")
        out: list[int] = []
        for e in expected:
            i = lookup_exact(ts, e)
            if i is None:
                return None
            out.append(i)
        return out
    mask = (ts >= start) & (ts < t)
    return [int(i) for i in range(len(ts)) if bool(mask[i])]


def rolling_high_excluding_t(
    high: pd.Series,
    ts: pd.DatetimeIndex,
    t: pd.Timestamp,
    lookback: pd.Timedelta,
) -> float | None:
    idxs = window_indices_excluding_t(ts, t, lookback, require_complete=True)
    if not idxs:
        return None
    return float(high.iloc[idxs].max())


def expanding_values_before_t(values: pd.Series, ts: pd.DatetimeIndex, t: pd.Timestamp) -> pd.Series:
    """Observations with timestamp strictly before t (no lookahead)."""
    ts = as_utc_index(ts)
    t = pd.Timestamp(t)
    if t.tzinfo is None:
        t = t.tz_localize("UTC")
    else:
        t = t.tz_convert("UTC")
    mask = ts < t
    return values.iloc[np.asarray(mask)]
