"""Trade-leg invariants: entry after signal, exact exit, omit missing legs, fees, block bounds."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from temporal.exact_timestamp import ahead_index, lookup_exact

HOUR = pd.Timedelta(hours=1)


@dataclass(frozen=True)
class TradeLegs:
    signal_ts: pd.Timestamp
    entry_ts: pd.Timestamp
    exit_ts: pd.Timestamp
    entry_px: float
    exit_px: float


def net_return(entry_px: float, exit_px: float, fee_entry: float, fee_exit: float) -> float:
    return (1.0 - fee_entry) * (exit_px / entry_px) * (1.0 - fee_exit) - 1.0


def build_trade(
    ts: pd.DatetimeIndex,
    opens: pd.Series,
    signal_ts: pd.Timestamp,
    hold: pd.Timedelta,
) -> TradeLegs | None:
    """Signal known at bar t. Entry = exact open of t+1h. Exit = exact open hold after entry.

    Omit the trade if any required timestamp is missing. Entry is strictly after signal.
    """
    if lookup_exact(ts, signal_ts) is None:
        return None
    entry_i = ahead_index(ts, signal_ts, HOUR)
    if entry_i is None:
        return None
    entry_ts = ts[entry_i]
    if not (entry_ts > pd.Timestamp(signal_ts)):
        return None
    exit_i = ahead_index(ts, entry_ts, hold)
    if exit_i is None:
        return None
    exit_ts = ts[exit_i]
    return TradeLegs(
        signal_ts=pd.Timestamp(signal_ts),
        entry_ts=entry_ts,
        exit_ts=exit_ts,
        entry_px=float(opens.iloc[entry_i]),
        exit_px=float(opens.iloc[exit_i]),
    )


def fully_inside_block(
    legs: TradeLegs,
    block_start: pd.Timestamp,
    block_end: pd.Timestamp,
) -> bool:
    """Signal, entry, and exit all contained in [block_start, block_end)."""
    return (
        legs.signal_ts >= block_start
        and legs.entry_ts >= block_start
        and legs.exit_ts >= block_start
        and legs.signal_ts < block_end
        and legs.entry_ts < block_end
        and legs.exit_ts < block_end
    )
