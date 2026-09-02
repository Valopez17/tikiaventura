#!/usr/bin/env python3
"""Phase 1: BTC capitulation entry event study.

Not a strategy. Thresholds are pre-specified. 2024-08-05 is a case study only.
"""

from __future__ import annotations

import json
import ssl
import time
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd

PHASE = Path(__file__).resolve().parents[1]
RESULTS = PHASE / "results"
RAW = PHASE / "data" / "raw"
TSR = PHASE.parent
MSO = TSR.parent
REPO = MSO.parent.parent
TRUSTED_PRICES = REPO / "btc_tsmom_replication" / "data" / "btcusd_daily.csv"

BINANCE_LISTING = date(2017, 8, 17)
SPLICE_DATE = BINANCE_LISTING
CASE_DATE = pd.Timestamp("2024-08-05")
PRE2024_END = pd.Timestamp("2023-12-31")
CASE_THR_END = pd.Timestamp("2024-08-04")
MIN_HIST = 365
COOLDOWN_DAYS = 7
Q_TAIL = 5.0
Q_VOL = 80.0
HORIZONS = (1, 3, 7, 14, 30, 60, 90)
DEFS = ("EXTREME_1D", "EXTREME_MULTI_DAY", "CAPITULATION_PLUS_STRESS")
BINANCE_KLINES = "https://api.binance.com/api/v3/klines"
UA = "tikiaventura-capitulation-phase1/1.0 (academic research)"
SSL_CTX = ssl.create_default_context()


def log(msg: str) -> None:
    print(msg, flush=True)


def last_complete_utc_day() -> date:
    return datetime.now(timezone.utc).date() - timedelta(days=1)


def http_get(url: str, timeout: int = 90, retries: int = 4) -> bytes:
    last_err: Exception | None = None
    for attempt in range(1, retries + 1):
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        try:
            with urllib.request.urlopen(req, timeout=timeout, context=SSL_CTX) as resp:
                payload = resp.read()
            if len(payload) >= 64:
                return payload
            last_err = RuntimeError(f"short payload {len(payload)}")
        except (urllib.error.URLError, TimeoutError, ssl.SSLError) as exc:
            last_err = exc
            log(f"  retry {attempt}/{retries} {exc}")
        time.sleep(1.2 * attempt)
    raise RuntimeError(f"GET failed: {url}\n{last_err}")


def download_binance_daily(end: date) -> pd.DataFrame:
    start_ms = int(datetime(2017, 8, 17, tzinfo=timezone.utc).timestamp() * 1000)
    end_ms = int(
        datetime(end.year, end.month, end.day, tzinfo=timezone.utc).timestamp() * 1000
    ) + 86_400_000
    rows = []
    while start_ms < end_ms:
        url = (
            f"{BINANCE_KLINES}?symbol=BTCUSDT&interval=1d&limit=1000&startTime={start_ms}"
        )
        batch = json.loads(http_get(url).decode())
        if not batch:
            break
        rows.extend(batch)
        last_open = int(batch[-1][0])
        if len(batch) < 1000:
            break
        start_ms = last_open + 86_400_000
    if not rows:
        raise RuntimeError("Binance returned no BTCUSDT 1d klines.")
    out = pd.DataFrame(
        {
            "date": [datetime.utcfromtimestamp(k[0] / 1000).date() for k in rows],
            "close": [float(k[4]) for k in rows],
            "volume": [float(k[5]) for k in rows],
        }
    )
    out = out.loc[out["date"] <= end].copy()
    out["source"] = "binance_btcusdt"
    return out.drop_duplicates("date").sort_values("date").reset_index(drop=True)


def load_series() -> tuple[pd.DataFrame, dict]:
    if not TRUSTED_PRICES.exists():
        raise RuntimeError(
            f"Trusted BTC daily file missing: {TRUSTED_PRICES}. "
            "No silent source substitution."
        )
    trusted = pd.read_csv(TRUSTED_PRICES, parse_dates=["date"])
    trusted["date"] = pd.to_datetime(trusted["date"]).dt.normalize()
    trusted["close"] = pd.to_numeric(trusted["close"], errors="coerce")
    if "source" not in trusted.columns:
        raise RuntimeError("Trusted file has no source column; refuse to guess.")
    end = last_complete_utc_day()
    RAW.mkdir(parents=True, exist_ok=True)
    log("Downloading Binance BTCUSDT 1d (UTC close + volume)")
    bn = download_binance_daily(end)
    bn["date"] = pd.to_datetime(bn["date"])
    bn.to_csv(RAW / "binance_btcusdt_1d.csv", index=False)

    t_bn = trusted.loc[trusted["source"] == "binance_btcusdt", ["date", "close"]].copy()
    overlap = t_bn.merge(bn[["date", "close"]], on="date", suffixes=("_trusted", "_bn"))
    if overlap.empty:
        raise RuntimeError("No overlapping Binance dates vs trusted file.")
    rel = np.abs(overlap["close_bn"] / overlap["close_trusted"] - 1.0)
    max_rel = float(rel.max())
    if max_rel > 1e-6:
        raise RuntimeError(
            f"Binance download diverges from trusted closes (max rel {max_rel:.3e}). STOP."
        )
    log(f"Binance vs trusted close match max rel={max_rel:.3e} n={len(overlap)}")

    pre = trusted.loc[
        trusted["source"] == "bitstamp_btcusd", ["date", "close", "source"]
    ].copy()
    pre = pre.loc[pre["date"].dt.date < BINANCE_LISTING].copy()
    pre["volume"] = np.nan
    post = bn.loc[bn["date"].dt.date >= BINANCE_LISTING, ["date", "close", "volume"]].copy()
    post["source"] = "binance_btcusdt"
    # CDD Bitstamp "Volume BTC" / "Volume USD" are swapped in the early sample
    # (2014-11-28 Volume BTC=3.2e6 cannot be BTC; 2026 rows look like true BTC).
    # Do not mix those units with Binance base-asset volume.
    vol_note = (
        "Relative volume uses Binance BTC base volume only from 2017-08-17. "
        "Bitstamp CDD volume columns are internally inconsistent in the pre-listing "
        "sample (BTC/USD fields swapped) and were not used."
    )
    log(vol_note)

    px = pd.concat([pre[["date", "close", "volume", "source"]], post], ignore_index=True)
    px = px.sort_values("date").drop_duplicates("date").reset_index(drop=True)
    px = px.loc[px["date"].dt.date <= end].copy()
    dates = pd.to_datetime(px["date"])
    full = pd.date_range(dates.min(), dates.max(), freq="D")
    missing = full.difference(dates)
    splice_pct = np.nan
    b_on = trusted.loc[
        (trusted["source"] == "bitstamp_btcusd")
        & (trusted["date"].dt.date == BINANCE_LISTING),
        "close",
    ]
    n_on = post.loc[post["date"].dt.date == BINANCE_LISTING, "close"]
    if len(b_on) and len(n_on):
        splice_pct = float(n_on.iloc[0] / float(b_on.iloc[0]) - 1.0)
    meta = {
        "trusted_file": "btc_tsmom_replication/data/btcusd_daily.csv",
        "source_description": (
            "Empalme: Bitstamp BTCUSD (CryptoDataDownload / trusted project file) "
            f"until 2017-08-16; Binance BTCUSDT spot 1d UTC from {BINANCE_LISTING}. "
            "Closes are not interpolated. Incomplete current UTC day dropped."
        ),
        "date_start": dates.min().date().isoformat(),
        "date_end": dates.max().date().isoformat(),
        "n_obs": int(len(px)),
        "n_missing_calendar_days": int(len(missing)),
        "missing_dates": [d.date().isoformat() for d in missing[:25]],
        "n_bitstamp": int((px["source"] == "bitstamp_btcusd").sum()),
        "n_binance": int((px["source"] == "binance_btcusdt").sum()),
        "n_volume_finite": int(pd.to_numeric(px["volume"], errors="coerce").notna().sum()),
        "splice_binance_vs_bitstamp_2017_08_17": splice_pct,
        "volume_note": vol_note,
        "timezone": "UTC",
    }
    if CASE_DATE not in set(px["date"]):
        raise RuntimeError("2024-08-05 is missing from the daily series. STOP.")
    return px.reset_index(drop=True), meta


def add_features(px: pd.DataFrame) -> pd.DataFrame:
    df = px.copy()
    c = pd.to_numeric(df["close"], errors="coerce")
    df["ret_1d"] = c.pct_change()
    df["ret_3d"] = c / c.shift(3) - 1.0
    df["ret_7d"] = c / c.shift(7) - 1.0
    roll_high = c.rolling(30, min_periods=30).max()
    df["dd_30"] = c / roll_high - 1.0
    df["vol_20"] = df["ret_1d"].rolling(20, min_periods=20).std()
    vol = pd.to_numeric(df["volume"], errors="coerce")
    med20 = vol.shift(1).rolling(20, min_periods=20).median()
    df["rel_volume"] = vol / med20
    splice = pd.Timestamp(SPLICE_DATE)
    df.loc[df["date"] == splice, "ret_1d"] = np.nan
    return df


def expanding_pctl_and_flag(x: np.ndarray, q: float, side: str, min_n: int):
    n = len(x)
    flag = np.zeros(n, dtype=bool)
    pctl = np.full(n, np.nan)
    for t in range(n):
        xt = x[t]
        if not np.isfinite(xt):
            continue
        hist = x[:t]
        hist = hist[np.isfinite(hist)]
        if hist.size < min_n:
            continue
        pctl[t] = 100.0 * float(np.mean(hist <= xt))
        thr = float(np.percentile(hist, q))
        if side == "low":
            flag[t] = xt <= thr
        else:
            flag[t] = xt >= thr
    return flag, pctl


def frozen_pctl(hist: np.ndarray, xt: float) -> float:
    hist = hist[np.isfinite(hist)]
    if hist.size < MIN_HIST or not np.isfinite(xt):
        return np.nan
    return 100.0 * float(np.mean(hist <= xt))


def decluster(flag: np.ndarray, dates: pd.Series, cooldown: int) -> np.ndarray:
    out = np.zeros(len(flag), dtype=bool)
    last = None
    for i, (f, d) in enumerate(zip(flag, dates)):
        if not f:
            continue
        if last is None or (pd.Timestamp(d) - last).days > cooldown:
            out[i] = True
            last = pd.Timestamp(d)
    return out


def path_stats(close: np.ndarray, t: int, h: int) -> dict:
    out = {
        "fut": np.nan,
        "pos": np.nan,
        "gt10": np.nan,
        "gt20": np.nan,
        "lt10": np.nan,
        "lt20": np.nan,
        "maxdd": np.nan,
        "maxru": np.nan,
    }
    if t + h >= len(close):
        return out
    p0 = close[t]
    path = close[t : t + h + 1]
    if (not np.isfinite(p0)) or p0 <= 0 or (not np.isfinite(path).all()):
        return out
    fut = float(path[-1] / p0 - 1.0)
    peak = np.maximum.accumulate(path)
    dd = path / peak - 1.0
    ru = path / p0 - 1.0
    out["fut"] = fut
    out["pos"] = float(fut > 0)
    out["gt10"] = float(fut > 0.10)
    out["gt20"] = float(fut > 0.20)
    out["lt10"] = float(fut < -0.10)
    out["lt20"] = float(fut < -0.20)
    out["maxdd"] = float(np.min(dd))
    out["maxru"] = float(np.max(ru))
    return out


def add_outcomes(df: pd.DataFrame) -> pd.DataFrame:
    close = pd.to_numeric(df["close"], errors="coerce").to_numpy(dtype=float)
    recs = {f"{k}_{h}": np.full(len(df), np.nan) for h in HORIZONS for k in (
        "fut", "pos", "gt10", "gt20", "lt10", "lt20", "maxdd", "maxru"
    )}
    for t in range(len(df)):
        for h in HORIZONS:
            st = path_stats(close, t, h)
            for k, v in st.items():
                recs[f"{k}_{h}"][t] = v
    for col, arr in recs.items():
        df[col] = arr
    return df


def summarize_block(sub: pd.DataFrame, h: int) -> dict:
    fut = pd.to_numeric(sub[f"fut_{h}"], errors="coerce")
    m = fut.notna()
    x = fut[m].to_numpy(dtype=float)
    rec = {
        "N": int(m.sum()),
        "mean": np.nan,
        "median": np.nan,
        "p25": np.nan,
        "p75": np.nan,
        "p_pos": np.nan,
        "p_gt10": np.nan,
        "p_gt20": np.nan,
        "p_lt10": np.nan,
        "p_lt20": np.nan,
        "med_dd": np.nan,
        "med_ru": np.nan,
    }
    if rec["N"] == 0:
        return rec
    rec["mean"] = float(np.mean(x))
    rec["median"] = float(np.median(x))
    rec["p25"] = float(np.percentile(x, 25))
    rec["p75"] = float(np.percentile(x, 75))
    rec["p_pos"] = float(np.mean(x > 0))
    rec["p_gt10"] = float(np.mean(x > 0.10))
    rec["p_gt20"] = float(np.mean(x > 0.20))
    rec["p_lt10"] = float(np.mean(x < -0.10))
    rec["p_lt20"] = float(np.mean(x < -0.20))
    rec["med_dd"] = float(np.nanmedian(pd.to_numeric(sub.loc[m, f"maxdd_{h}"], errors="coerce")))
    rec["med_ru"] = float(np.nanmedian(pd.to_numeric(sub.loc[m, f"maxru_{h}"], errors="coerce")))
    return rec


def eligible_mask(df: pd.DataFrame) -> np.ndarray:
    return (
        np.isfinite(df["ret_1d"].to_numpy(dtype=float))
        & np.isfinite(df["pctl_ret_1d"].to_numpy(dtype=float))
        & (df["date"] != pd.Timestamp(SPLICE_DATE))
    )


def iqr(s: pd.Series) -> float:
    x = pd.to_numeric(s, errors="coerce").dropna()
    if len(x) < 4:
        return np.nan
    return float(np.percentile(x, 75) - np.percentile(x, 25))


def pct(x, nd=1) -> str:
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return "NA"
    return f"{100.0 * float(x):.{nd}f}%"


def num(x, nd=3) -> str:
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return "NA"
    return f"{float(x):.{nd}f}"


def row_md(label: str, a: dict, b: dict | None = None) -> str:
    parts = [
        f"| {label} | {a['N']} | {pct(a['mean'])} | {pct(a['median'])} | "
        f"{pct(a['p25'])} | {pct(a['p75'])} | {pct(a['p_pos'])} | {pct(a['p_gt10'])} | "
        f"{pct(a['p_gt20'])} | {pct(a['p_lt10'])} | {pct(a['p_lt20'])} | "
        f"{pct(a['med_dd'])} | {pct(a['med_ru'])} |"
    ]
    if b is not None:
        parts = [
            f"| {label} | {a['N']} | {pct(a['median'])} | {pct(b['median'])} | "
            f"{pct(a['median'] - b['median'] if np.isfinite(a['median']) and np.isfinite(b['median']) else np.nan)} | "
            f"{pct(a['p_pos'])} | {pct(b['p_pos'])} | "
            f"{pct(a['p_pos'] - b['p_pos'] if np.isfinite(a['p_pos']) and np.isfinite(b['p_pos']) else np.nan)} | "
            f"{pct(a['p_gt10'])} | {pct(b['p_gt10'])} | {pct(a['p_gt20'])} | {pct(b['p_gt20'])} | "
            f"{pct(a['p_lt10'])} | {pct(b['p_lt10'])} | {pct(a['p_lt20'])} | {pct(b['p_lt20'])} |"
        ]
    return parts[0]


def disposition(stats: dict) -> str:
    """Pre-specified on CAPITULATION_PLUS_STRESS, declustered, pre-2024, 30/60/90d."""
    hits = 0
    checked = 0
    n_ok = True
    for h in (30, 60, 90):
        cap = stats[h]["cap"]
        base = stats[h]["base"]
        if cap["N"] < 20:
            n_ok = False
        checked += 1
        med_ok = np.isfinite(cap["median"]) and np.isfinite(base["median"]) and cap["median"] > base["median"]
        pos_ok = np.isfinite(cap["p_pos"]) and np.isfinite(base["p_pos"]) and cap["p_pos"] > base["p_pos"]
        if med_ok and pos_ok:
            hits += 1
    if hits >= 2 and n_ok:
        return "PROMISING"
    if hits == 0:
        return "NO EDGE"
    return "WEAK"


def write_report(
    df: pd.DataFrame,
    meta: dict,
    case: dict,
    tables: dict,
    goodbad: dict,
    bigger: dict,
    disp: str,
) -> None:
    lines = []
    lines.append("# Capitulation entry study — Phase 1")
    lines.append("")
    lines.append(
        "BTC-only daily event study. Not a trading strategy. Not a backtest. "
        "Thresholds 5% / 80% were frozen before looking at 2024-08-05. "
        "Primary counts use event dates **before 2024-01-01**."
    )
    lines.append("")
    lines.append("P(return > 0) is an empirical conditional frequency in this sample, not a true future probability.")
    lines.append("Median + X% means half of qualifying historical events returned more than X%, half less.")
    lines.append("Max drawdown after entry is the typical path pain after buying the event close.")
    lines.append("Max runup is the best close-to-close upside available within the horizon.")
    lines.append("Differences vs baseline are descriptive, not causal effects.")
    lines.append("")
    lines.append("## Data")
    lines.append("")
    lines.append("| item | value |")
    lines.append("|---|---|")
    lines.append(f"| source | {meta['source_description']} |")
    lines.append(f"| trusted prices | `{meta['trusted_file']}` |")
    lines.append(f"| date range | {meta['date_start']} → {meta['date_end']} |")
    lines.append(f"| N days | {meta['n_obs']} |")
    lines.append(f"| missing calendar days | {meta['n_missing_calendar_days']} |")
    miss = ", ".join(meta["missing_dates"]) if meta["missing_dates"] else "(none)"
    lines.append(f"| first missing dates | {miss} |")
    lines.append(f"| Bitstamp days | {meta['n_bitstamp']} |")
    lines.append(f"| Binance days | {meta['n_binance']} |")
    lines.append(f"| days with volume | {meta['n_volume_finite']} |")
    spl = meta["splice_binance_vs_bitstamp_2017_08_17"]
    lines.append(f"| splice jump 2017-08-17 | {pct(spl) if np.isfinite(spl) else 'NA (no Bitstamp print that day)'} |")
    lines.append(f"| volume | {meta['volume_note']} |")
    lines.append("| timezone | UTC daily close |")
    lines.append("| splice-day return | 2017-08-17 `ret_1d` set to NaN (source join, not a market crash) |")
    lines.append("")
    lines.append("## Definitions")
    lines.append("")
    lines.append("- Features at t: 1d/3d/7d simple return, drawdown from trailing 30d high, 20d stdev of daily returns, volume / prior-20d median volume.")
    lines.append("- Expanding percentiles use only s < t, min 365 finite observations.")
    lines.append("- EXTREME_1D: 1d return ≤ historical 5th percentile.")
    lines.append("- EXTREME_MULTI_DAY: 3d **or** 7d return ≤ historical 5th percentile.")
    lines.append("- CAPITULATION_PLUS_STRESS: (EXTREME_1D or EXTREME_MULTI_DAY) **and** 20d vol ≥ historical 80th percentile.")
    lines.append("- De-cluster: keep the first event, then 7 calendar-day cooldown. Raw flags are retained.")
    lines.append("- Forward return over H days: P_{t+H}/P_t − 1 (event-day crash is excluded).")
    lines.append("- Baseline: every eligible BTC day in the same era (pre-2024, enough history, finite H-day outcome).")
    lines.append("")
    lines.append("## 1. How many capitulation events exist?")
    lines.append("")
    lines.append("| definition | raw pre-2024 | declustered pre-2024 | raw full sample | declustered full sample |")
    lines.append("|---|---:|---:|---:|---:|")
    for name in DEFS:
        lines.append(
            f"| {name} | {int(tables['counts'][name]['raw_pre'])} | {int(tables['counts'][name]['dc_pre'])} | "
            f"{int(tables['counts'][name]['raw_all'])} | {int(tables['counts'][name]['dc_all'])} |"
        )
    lines.append("")
    lines.append("Primary analysis below uses **declustered, pre-2024** events.")
    lines.append("")

    hdr_full = (
        "| sample | N | mean | median | p25 | p75 | P(>0) | P(>+10%) | P(>+20%) | "
        "P(<-10%) | P(<-20%) | median max DD | median max runup |"
    )
    sep_full = "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"
    hdr_diff = (
        "| sample | N | med cap | med base | Δ med | P(>0) cap | P(>0) base | Δ P(>0) | "
        "P(>+10%) cap | P(>+10%) base | P(>+20%) cap | P(>+20%) base | "
        "P(<-10%) cap | P(<-10%) base | P(<-20%) cap | P(<-20%) base |"
    )
    sep_diff = "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"

    for name in DEFS:
        lines.append(f"## {name} — declustered pre-2024 vs baseline")
        lines.append("")
        for h in HORIZONS:
            cap = tables[name][h]["cap"]
            base = tables[name][h]["base"]
            lines.append(f"### Horizon {h}d")
            lines.append("")
            lines.append(hdr_full)
            lines.append(sep_full)
            lines.append(row_md("capitulation", cap))
            lines.append(row_md("baseline (all eligible days)", base))
            lines.append("")
            lines.append(hdr_diff)
            lines.append(sep_diff)
            lines.append(row_md("cap − base", cap, base))
            lines.append("")

    lines.append("## 6. Bigger crash, better future return?")
    lines.append("")
    lines.append(
        "Within pre-2024 declustered EXTREME_1D, split by median event-day 1d return "
        "(more negative vs less negative). Same 60d outcome. Not a new threshold."
    )
    lines.append("")
    lines.append("| half | N | median 1d return | median 60d future | P(60d > 0) |")
    lines.append("|---|---:|---:|---:|---:|")
    for key, lab in (("worse", "more severe 1d"), ("milder", "less severe 1d")):
        g = bigger[key]
        lines.append(
            f"| {lab} | {g['N']} | {pct(g['med_1d'])} | {pct(g['med_60'])} | {pct(g['p_pos_60'])} |"
        )
    lines.append("")
    if bigger["worse"]["N"] and bigger["milder"]["N"]:
        if np.isfinite(bigger["worse"]["med_60"]) and np.isfinite(bigger["milder"]["med_60"]):
            if bigger["worse"]["med_60"] > bigger["milder"]["med_60"]:
                lines.append(
                    "In this split, the more severe half had a **higher** median 60d return. "
                    "That is weak descriptive support for “bigger crash, better bounce,” not a rule."
                )
            elif bigger["worse"]["med_60"] < bigger["milder"]["med_60"]:
                lines.append(
                    "In this split, the more severe half had a **lower** median 60d return. "
                    "“The bigger the crash, the better the future return” is **not** supported here."
                )
            else:
                lines.append("The two halves had the same median 60d return.")
    lines.append("")
    lines.append("Bucket comparison, same 60d outcome, declustered pre-2024:")
    lines.append("")
    lines.append("| definition | N | median 60d | P(60d > 0) |")
    lines.append("|---|---:|---:|---:|")
    for name in DEFS:
        s = tables[name][60]["cap"]
        lines.append(f"| {name} | {s['N']} | {pct(s['median'])} | {pct(s['p_pos'])} |")
    lines.append("")

    lines.append("## 7. Do volatility and abnormal volume distinguish GOOD vs BAD 60d outcomes?")
    lines.append("")
    lines.append(
        "GOOD_60D = future 60d return > +20%. BAD_60D = future 60d return < 0%. "
        "OTHER = the rest. Labels are outcomes, not inputs. Sample: declustered pre-2024 CAPITULATION_PLUS_STRESS."
    )
    lines.append("")
    lines.append("| outcome | N | median 1d ret | median 3d ret | median 7d ret | median 30d DD | median vol pctl | IQR vol pctl | median rel-vol pctl | IQR rel-vol pctl |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for lab in ("GOOD_60D", "BAD_60D", "OTHER"):
        g = goodbad[lab]
        lines.append(
            f"| {lab} | {g['N']} | {pct(g['med_1d'])} | {pct(g['med_3d'])} | {pct(g['med_7d'])} | "
            f"{pct(g['med_dd'])} | {num(g['med_volp'], 1)} | {num(g['iqr_volp'], 1)} | "
            f"{num(g['med_relp'], 1)} | {num(g['iqr_relp'], 1)} |"
        )
    lines.append("")
    g, b = goodbad["GOOD_60D"], goodbad["BAD_60D"]
    if g["N"] < 8 or b["N"] < 8:
        lines.append("Sample too small to treat vol/volume as a separator. Descriptive only.")
    else:
        vol_sep = np.isfinite(g["med_volp"]) and np.isfinite(b["med_volp"]) and abs(g["med_volp"] - b["med_volp"]) >= 5
        rel_sep = np.isfinite(g["med_relp"]) and np.isfinite(b["med_relp"]) and abs(g["med_relp"] - b["med_relp"]) >= 5
        if vol_sep or rel_sep:
            lines.append(
                "Medians differ by at least 5 percentile points on "
                + ("vol " if vol_sep else "")
                + ("and " if vol_sep and rel_sep else "")
                + ("relative volume " if rel_sep else "")
                + "— a candidate pattern, not a classifier."
            )
        else:
            lines.append(
                "GOOD and BAD look similar on vol and relative-volume percentiles at event time. "
                "Those two observables do not cleanly separate better vs worse capitulations here."
            )
    lines.append("")

    lines.append("## 8–9. Case study: 2024-08-05")
    lines.append("")
    lines.append("Thresholds and percentiles use **only** data through 2024-08-04. Outcomes below were not known at t.")
    lines.append("")
    lines.append("| observable | value | percentile vs history through 2024-08-04 |")
    lines.append("|---|---:|---:|")
    for key, lab in (
        ("ret_1d", "daily return"),
        ("ret_3d", "3d return"),
        ("ret_7d", "7d return"),
        ("dd_30", "30d drawdown"),
        ("vol_20", "20d volatility"),
        ("rel_volume", "relative volume"),
    ):
        lines.append(f"| {lab} | {num(case[key], 4) if key in ('vol_20', 'rel_volume') else pct(case[key])} | {num(case[f'pctl_{key}'], 1)} |")
    lines.append("")
    lines.append("| bucket | triggered? |")
    lines.append("|---|---|")
    for name in DEFS:
        lines.append(f"| {name} | {'YES' if case[name] else 'no'} |")
    lines.append("")
    lines.append("| horizon | future return | >0 | >+10% | >+20% | <-10% | <-20% | max DD | max runup |")
    lines.append("|---:|---:|---|---|---|---|---|---:|---:|")
    for h in HORIZONS:
        lines.append(
            f"| +{h}d | {pct(case[f'fut_{h}'])} | {int(case[f'pos_{h}']) if np.isfinite(case[f'pos_{h}']) else 'NA'} | "
            f"{int(case[f'gt10_{h}']) if np.isfinite(case[f'gt10_{h}']) else 'NA'} | "
            f"{int(case[f'gt20_{h}']) if np.isfinite(case[f'gt20_{h}']) else 'NA'} | "
            f"{int(case[f'lt10_{h}']) if np.isfinite(case[f'lt10_{h}']) else 'NA'} | "
            f"{int(case[f'lt20_{h}']) if np.isfinite(case[f'lt20_{h}']) else 'NA'} | "
            f"{pct(case[f'maxdd_{h}'])} | {pct(case[f'maxru_{h}'])} |"
        )
    lines.append("")
    lines.append(case["rank_note"])
    lines.append("")
    lines.append(case["exceptional_note"])
    lines.append("")

    lines.append("## Answers")
    lines.append("")
    c = tables["CAPITULATION_PLUS_STRESS"]
    lines.append(
        f"1. How many capitulation events exist? "
        f"Pre-2024 declustered: EXTREME_1D N={tables['counts']['EXTREME_1D']['dc_pre']}, "
        f"EXTREME_MULTI_DAY N={tables['counts']['EXTREME_MULTI_DAY']['dc_pre']}, "
        f"CAPITULATION_PLUS_STRESS N={tables['counts']['CAPITULATION_PLUS_STRESS']['dc_pre']}."
    )
    h60 = c[60]
    better_pos = []
    for h in HORIZONS:
        cap, base = c[h]["cap"], c[h]["base"]
        if np.isfinite(cap["p_pos"]) and np.isfinite(base["p_pos"]) and cap["p_pos"] > base["p_pos"]:
            better_pos.append(str(h))
    lines.append(
        "2. After extreme selloffs, is BTC historically more likely to rise than on an unconditional day? "
        + (
            f"On CAPITULATION_PLUS_STRESS, P(>0) exceeds baseline at horizons {', '.join(h + 'd' for h in better_pos)}."
            if better_pos
            else "On CAPITULATION_PLUS_STRESS, P(>0) does not exceed the unconditional baseline at the studied horizons."
        )
    )
    med_up = []
    for h in HORIZONS:
        cap, base = c[h]["cap"], c[h]["base"]
        if np.isfinite(cap["median"]) and np.isfinite(base["median"]) and cap["median"] > base["median"]:
            med_up.append(f"{h}d (Δ {pct(cap['median'] - base['median'])})")
    lines.append(
        "3. At which horizons does the difference appear? "
        + ("Median future return above baseline at " + "; ".join(med_up) + "." if med_up else "No horizon shows a higher median than baseline.")
    )
    lines.append(
        f"4. How large is the median upside? CAPITULATION_PLUS_STRESS 30d median={pct(c[30]['cap']['median'])}, "
        f"60d={pct(c[60]['cap']['median'])}, 90d={pct(c[90]['cap']['median'])} "
        f"(unconditional 60d median={pct(c[60]['base']['median'])})."
    )
    lines.append(
        f"5. What is the downside / max-drawdown risk after buying? "
        f"CAPITULATION_PLUS_STRESS median max DD 30d={pct(c[30]['cap']['med_dd'])}, "
        f"60d={pct(c[60]['cap']['med_dd'])}, 90d={pct(c[90]['cap']['med_dd'])}; "
        f"P(60d < −20%)={pct(c[60]['cap']['p_lt20'])} vs baseline {pct(c[60]['base']['p_lt20'])}."
    )
    w, m = bigger["worse"], bigger["milder"]
    if np.isfinite(w["med_60"]) and np.isfinite(m["med_60"]) and w["med_60"] < m["med_60"]:
        q6 = (
            f"False in this sample. More severe EXTREME_1D half median 60d={pct(w['med_60'])} "
            f"vs less severe {pct(m['med_60'])}."
        )
    elif np.isfinite(w["med_60"]) and np.isfinite(m["med_60"]) and w["med_60"] > m["med_60"]:
        q6 = (
            f"Weakly true in this split only: more severe half median 60d={pct(w['med_60'])} "
            f"vs less severe {pct(m['med_60'])}. Not a rule."
        )
    else:
        q6 = "Not estimable from the split."
    lines.append(f"6. Does “the bigger the crash, the better the future return” appear true or false? {q6}")
    g7, b7 = goodbad["GOOD_60D"], goodbad["BAD_60D"]
    lines.append(
        f"7. Do volatility and abnormal volume distinguish better vs worse capitulations? "
        f"GOOD_60D N={g7['N']} median vol pctl={num(g7['med_volp'], 1)}, rel-vol pctl={num(g7['med_relp'], 1)}; "
        f"BAD_60D N={b7['N']} median vol pctl={num(b7['med_volp'], 1)}, rel-vol pctl={num(b7['med_relp'], 1)}. "
        "Outcome labels only; no classifier."
    )
    lines.append(
        f"8. Where does 2024-08-05 rank historically? 1d return {pct(case['ret_1d'])} "
        f"(pctl {num(case['pctl_ret_1d'], 1)}), 7d {pct(case['ret_7d'])} "
        f"(pctl {num(case['pctl_ret_7d'], 1)}), rel-volume pctl {num(case['pctl_rel_volume'], 1)}, "
        f"20d vol pctl {num(case['pctl_vol_20'], 1)} vs history through 2024-08-04."
    )
    lines.append(
        "9. Did 2024-08-05 look like an exceptional candidate entry using information "
        f"that existed at the time? {case['exceptional_note']}"
    )
    lines.append(f"10. Does this evidence justify continuing toward a formal CAPITULATION ENTRY SETUP? **{disp}**")
    lines.append("")
    lines.append("## Decision")
    lines.append("")
    lines.append(f"**{disp}**")
    lines.append("")
    lines.append(
        "Research disposition only. This is not a validated trading signal. "
        "Macro is out of scope until a setup is economically meaningful. "
        "No thresholds were moved after seeing 2024-08-05."
    )
    lines.append("")
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "CAPITULATION_ENTRY_STUDY.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    px, meta = load_series()
    df = add_features(px)
    log("Expanding percentiles")
    f1, p1 = expanding_pctl_and_flag(df["ret_1d"].to_numpy(dtype=float), Q_TAIL, "low", MIN_HIST)
    f3, p3 = expanding_pctl_and_flag(df["ret_3d"].to_numpy(dtype=float), Q_TAIL, "low", MIN_HIST)
    f7, p7 = expanding_pctl_and_flag(df["ret_7d"].to_numpy(dtype=float), Q_TAIL, "low", MIN_HIST)
    _, pdd = expanding_pctl_and_flag(df["dd_30"].to_numpy(dtype=float), Q_TAIL, "low", MIN_HIST)
    fv, pv = expanding_pctl_and_flag(df["vol_20"].to_numpy(dtype=float), Q_VOL, "high", MIN_HIST)
    _, pr = expanding_pctl_and_flag(df["rel_volume"].to_numpy(dtype=float), Q_VOL, "high", MIN_HIST)
    df["pctl_ret_1d"] = p1
    df["pctl_ret_3d"] = p3
    df["pctl_ret_7d"] = p7
    df["pctl_dd_30"] = pdd
    df["pctl_vol_20"] = pv
    df["pctl_rel_volume"] = pr
    raw_a = f1
    raw_b = f3 | f7
    raw_c = (raw_a | raw_b) & fv
    df["raw_EXTREME_1D"] = raw_a
    df["raw_EXTREME_MULTI_DAY"] = raw_b
    df["raw_CAPITULATION_PLUS_STRESS"] = raw_c
    df["dc_EXTREME_1D"] = decluster(raw_a, df["date"], COOLDOWN_DAYS)
    df["dc_EXTREME_MULTI_DAY"] = decluster(raw_b, df["date"], COOLDOWN_DAYS)
    df["dc_CAPITULATION_PLUS_STRESS"] = decluster(raw_c, df["date"], COOLDOWN_DAYS)
    log("Forward outcomes")
    df = add_outcomes(df)
    fut60 = pd.to_numeric(df["fut_60"], errors="coerce")
    gb = np.full(len(df), "OTHER", dtype=object)
    gb = np.where(fut60 > 0.20, "GOOD_60D", gb)
    gb = np.where(fut60 < 0.0, "BAD_60D", gb)
    gb = np.where(~np.isfinite(fut60), "", gb)
    df["outcome_60d"] = gb

    pre = df["date"] <= PRE2024_END
    elig = eligible_mask(df)
    counts = {}
    tables: dict = {"counts": counts}
    for name in DEFS:
        raw = df[f"raw_{name}"].to_numpy(dtype=bool)
        dc = df[f"dc_{name}"].to_numpy(dtype=bool)
        counts[name] = {
            "raw_pre": int((raw & pre.to_numpy()).sum()),
            "dc_pre": int((dc & pre.to_numpy()).sum()),
            "raw_all": int(raw.sum()),
            "dc_all": int(dc.sum()),
        }
        tables[name] = {}
        for h in HORIZONS:
            cap_mask = dc & pre.to_numpy() & np.isfinite(df[f"fut_{h}"].to_numpy(dtype=float))
            base_mask = elig & pre.to_numpy() & np.isfinite(df[f"fut_{h}"].to_numpy(dtype=float))
            tables[name][h] = {
                "cap": summarize_block(df.loc[cap_mask], h),
                "base": summarize_block(df.loc[base_mask], h),
            }

    dc_a_pre = df["dc_EXTREME_1D"] & pre
    sub = df.loc[dc_a_pre & df["fut_60"].notna()].copy()
    bigger = {
        "worse": {"N": 0, "med_1d": np.nan, "med_60": np.nan, "p_pos_60": np.nan},
        "milder": {"N": 0, "med_1d": np.nan, "med_60": np.nan, "p_pos_60": np.nan},
    }
    if len(sub) >= 4:
        med = float(sub["ret_1d"].median())
        worse = sub.loc[sub["ret_1d"] <= med]
        milder = sub.loc[sub["ret_1d"] > med]
        for key, g in (("worse", worse), ("milder", milder)):
            bigger[key] = {
                "N": int(len(g)),
                "med_1d": float(g["ret_1d"].median()) if len(g) else np.nan,
                "med_60": float(g["fut_60"].median()) if len(g) else np.nan,
                "p_pos_60": float((g["fut_60"] > 0).mean()) if len(g) else np.nan,
            }

    stress_pre = df.loc[df["dc_CAPITULATION_PLUS_STRESS"] & pre & df["fut_60"].notna()].copy()
    goodbad = {}
    for lab in ("GOOD_60D", "BAD_60D", "OTHER"):
        g = stress_pre.loc[stress_pre["outcome_60d"] == lab]
        goodbad[lab] = {
            "N": int(len(g)),
            "med_1d": float(g["ret_1d"].median()) if len(g) else np.nan,
            "med_3d": float(g["ret_3d"].median()) if len(g) else np.nan,
            "med_7d": float(g["ret_7d"].median()) if len(g) else np.nan,
            "med_dd": float(g["dd_30"].median()) if len(g) else np.nan,
            "med_volp": float(g["pctl_vol_20"].median()) if len(g) else np.nan,
            "iqr_volp": iqr(g["pctl_vol_20"]) if len(g) else np.nan,
            "med_relp": float(g["pctl_rel_volume"].median()) if len(g) else np.nan,
            "iqr_relp": iqr(g["pctl_rel_volume"]) if len(g) else np.nan,
        }

    # Case study: freeze history through 2024-08-04 (same information set as expanding at t).
    i_case = int(df.index[df["date"] == CASE_DATE][0])
    hist = df.loc[df["date"] <= CASE_THR_END]
    case_row = df.iloc[i_case]
    case = {
        "ret_1d": float(case_row["ret_1d"]),
        "ret_3d": float(case_row["ret_3d"]),
        "ret_7d": float(case_row["ret_7d"]),
        "dd_30": float(case_row["dd_30"]),
        "vol_20": float(case_row["vol_20"]),
        "rel_volume": float(case_row["rel_volume"]),
        "pctl_ret_1d": frozen_pctl(hist["ret_1d"].to_numpy(dtype=float), float(case_row["ret_1d"])),
        "pctl_ret_3d": frozen_pctl(hist["ret_3d"].to_numpy(dtype=float), float(case_row["ret_3d"])),
        "pctl_ret_7d": frozen_pctl(hist["ret_7d"].to_numpy(dtype=float), float(case_row["ret_7d"])),
        "pctl_dd_30": frozen_pctl(hist["dd_30"].to_numpy(dtype=float), float(case_row["dd_30"])),
        "pctl_vol_20": frozen_pctl(hist["vol_20"].to_numpy(dtype=float), float(case_row["vol_20"])),
        "pctl_rel_volume": frozen_pctl(hist["rel_volume"].to_numpy(dtype=float), float(case_row["rel_volume"])),
    }
    thr1 = np.percentile(hist["ret_1d"].dropna().to_numpy(dtype=float), Q_TAIL)
    thr3 = np.percentile(hist["ret_3d"].dropna().to_numpy(dtype=float), Q_TAIL)
    thr7 = np.percentile(hist["ret_7d"].dropna().to_numpy(dtype=float), Q_TAIL)
    thrv = np.percentile(hist["vol_20"].dropna().to_numpy(dtype=float), Q_VOL)
    case["EXTREME_1D"] = bool(np.isfinite(case["ret_1d"]) and case["ret_1d"] <= thr1)
    case["EXTREME_MULTI_DAY"] = bool(
        (np.isfinite(case["ret_3d"]) and case["ret_3d"] <= thr3)
        or (np.isfinite(case["ret_7d"]) and case["ret_7d"] <= thr7)
    )
    case["CAPITULATION_PLUS_STRESS"] = bool(
        (case["EXTREME_1D"] or case["EXTREME_MULTI_DAY"])
        and np.isfinite(case["vol_20"])
        and case["vol_20"] >= thrv
    )
    for h in HORIZONS:
        for k in ("fut", "pos", "gt10", "gt20", "lt10", "lt20", "maxdd", "maxru"):
            case[f"{k}_{h}"] = float(case_row[f"{k}_{h}"])

    pre_dc_c = df.loc[df["dc_CAPITULATION_PLUS_STRESS"] & pre, "pctl_ret_1d"]
    if pre_dc_c.notna().any() and np.isfinite(case["pctl_ret_1d"]):
        rank = float(np.mean(pre_dc_c.dropna() <= case["pctl_ret_1d"]))
        case["rank_note"] = (
            f"Among pre-2024 declustered CAPITULATION_PLUS_STRESS events, the 2024-08-05 "
            f"1d-return percentile sits at empirical rank {100.0 * rank:.1f}% "
            f"(0% = more extreme than every prior event's percentile)."
        )
    else:
        case["rank_note"] = "Could not rank 2024-08-05 against pre-2024 events."

    extreme_1d = case["EXTREME_1D"] and np.isfinite(case["pctl_ret_1d"]) and case["pctl_ret_1d"] <= 2.0
    stressed = case["CAPITULATION_PLUS_STRESS"]
    if stressed and extreme_1d:
        case["exceptional_note"] = (
            "Using only pre-event information, 2024-08-05 triggered CAPITULATION_PLUS_STRESS "
            "and the 1d return was inside the most extreme 2% of history through 2024-08-04. "
            "That is an exceptional-looking candidate on the frozen definitions. "
            "The subsequent path is descriptive only and was not known at t."
        )
    elif stressed:
        case["exceptional_note"] = (
            "Using only pre-event information, 2024-08-05 triggered CAPITULATION_PLUS_STRESS. "
            "It qualified as a capitulation under the frozen rules, without being in the most "
            "extreme 2% of 1d history. Not a reason to change thresholds."
        )
    elif case["EXTREME_1D"] or case["EXTREME_MULTI_DAY"]:
        case["exceptional_note"] = (
            "Using only pre-event information, 2024-08-05 was an extreme return day but did not "
            "meet CAPITULATION_PLUS_STRESS (volatility gate). It is a case study, not a template."
        )
    else:
        case["exceptional_note"] = (
            "Using only pre-event information, 2024-08-05 did not trigger the frozen capitulation "
            "buckets. The motivating story is not used to loosen definitions."
        )

    disp = disposition(tables["CAPITULATION_PLUS_STRESS"])
    log(f"Disposition: {disp}")

    keep_raw = (
        df["raw_EXTREME_1D"]
        | df["raw_EXTREME_MULTI_DAY"]
        | df["raw_CAPITULATION_PLUS_STRESS"]
        | (df["date"] == CASE_DATE)
    )
    ev = df.loc[keep_raw].copy()
    cols = [
        "date",
        "source",
        "close",
        "ret_1d",
        "ret_3d",
        "ret_7d",
        "dd_30",
        "vol_20",
        "volume",
        "rel_volume",
        "pctl_ret_1d",
        "pctl_ret_3d",
        "pctl_ret_7d",
        "pctl_dd_30",
        "pctl_vol_20",
        "pctl_rel_volume",
        "raw_EXTREME_1D",
        "raw_EXTREME_MULTI_DAY",
        "raw_CAPITULATION_PLUS_STRESS",
        "dc_EXTREME_1D",
        "dc_EXTREME_MULTI_DAY",
        "dc_CAPITULATION_PLUS_STRESS",
        "outcome_60d",
    ]
    for h in HORIZONS:
        cols.extend([f"{k}_{h}" for k in ("fut", "pos", "gt10", "gt20", "lt10", "lt20", "maxdd", "maxru")])
    ev["date"] = pd.to_datetime(ev["date"]).dt.strftime("%Y-%m-%d")
    ev[cols].to_csv(RESULTS / "capitulation_events.csv", index=False)
    log(f"wrote {RESULTS / 'capitulation_events.csv'} n={len(ev)}")
    write_report(df, meta, case, tables, goodbad, bigger, disp)
    log(f"wrote {RESULTS / 'CAPITULATION_ENTRY_STUDY.md'}")


if __name__ == "__main__":
    main()
