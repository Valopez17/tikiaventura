"""Legacy lookback: N rows back. This is the E-02 failure mode. Do not use in new work."""

from __future__ import annotations


def lookback_index_row_offset(i: int, n_rows: int) -> int | None:
    j = int(i) - int(n_rows)
    return j if j >= 0 else None
