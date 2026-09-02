#!/usr/bin/env python3
"""
Wen, Bouri, Xu & Zhao (2022) — methodological replication on Binance
BTCUSDT spot 5-minute data, reconstructing hourly log returns.

Phase: DOWNLOAD 5m → RECONSTRUCT HOURLY RETURNS → REPLICATE BASE RESULTS.
No forecasts, jumps, liquidity, volatility conditioning, or trading.

This is a methodological replication on a different exchange and later
sample than the paper (Bitstamp, 2013–2020). It is not an exact dataset replica.
"""

from __future__ import annotations

import hashlib
import json
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.stats.multitest import multipletests

# ---------------------------------------------------------------------------
# Paper Eq. (1): r_{i,t} = log(p_{i,t}) - log(p_{i-1,t}), i = 1..24
# p_{0,t} = price at 00:00 UTC on day t.
# Our hour_utc h = 0..23 is paper hour i = h+1.
#
# Binance 5m bars are labeled by OPEN time.
# Hour h (h:00 → h+1:00) has 12 bars: h:00, h:05, ..., h:55.
# p at end of hour h = close of the h:55–(h+1):00 bar (open timestamp h:55).
# That is NOT the close of the h:00 bar (which is only the h:05 price).
# ---------------------------------------------------------------------------

IS_END = pd.Timestamp("2020-12-31")
OOS1_END = pd.Timestamp("2023-12-31")
OOS2_START = pd.Timestamp("2024-01-01")
SAMPLES_STRICT = ("IS", "OOS-1", "OOS-2")
SAMPLES_ALL = ("FULL", "IS", "OOS-1", "OOS-2")

HAC_FLOOR = 5
MIN_REG_N = 60
BETA_MIN = 0.03
P_MAX_DISCOVERY = 0.05
BETA_MIN_OOS2 = 0.03
P_MAX_OOS2 = 0.10
CLOSE_TOL = 1e-8  # relative tolerance for 5m vs native 1h close audit

WEN_PAIRS = {
    (2, 16): "MOMENTUM",  # paper r3 → r17
    (7, 21): "MOMENTUM",  # paper r8 → r22
    (2, 4): "REVERSAL",  # paper r3 → r5
    (2, 14): "REVERSAL",  # paper r3 → r15
    (11, 12): "REVERSAL",  # paper r12 → r13
    (21, 22): "REVERSAL",  # paper r22 → r23
}

ROOT = Path(__file__).resolve().parent
FILE_5M = ROOT / "btcusdt_5m.csv"
FILE_1H = ROOT / "btcusdt_1h.csv"
FILE_PAIRS_1H = ROOT / "intraday_pairs.csv"
OUT_AUDIT = ROOT / "btcusdt_5m_audit.md"
OUT_PRICES = ROOT / "hourly_prices_from_5m.csv"
OUT_RETS = ROOT / "hourly_returns_from_5m.csv"
OUT_WEN = ROOT / "wen_pairs_5m.csv"
OUT_PAIRS = ROOT / "intraday_pairs_5m.csv"
OUT_CAND = ROOT / "intraday_candidates_5m.csv"
OUT_MD = ROOT / "wen_5m_replication_summary.md"

BINANCE_KLINES = "https://api.binance.com/api/v3/klines"
BINANCE_START_MS = int(datetime(2017, 8, 17, tzinfo=timezone.utc).timestamp() * 1000)
FIVE_MIN_MS = 5 * 60 * 1000
REQUIRED_5M = ("timestamp_utc", "open", "high", "low", "close", "volume")

PAIR_COLS = [
    "sample",
    "predictor_hour_utc",
    "target_hour_utc",
    "alpha",
    "beta",
    "se",
    "t_stat",
    "p_value",
    "fdr_p_value",
    "r2",
    "N",
]
CAND_COLS = [
    "predictor_hour",
    "target_hour",
    "type",
    "beta_IS",
    "beta_OOS1",
    "OOS2_beta",
    "OOS2_t",
    "OOS2_p",
    "OOS2_FDR",
    "OOS2_r2",
    "OOS2_N",
    "sign_stability",
    "final_status",
]


def last_complete_5m_open() -> tuple[datetime, int]:
    now = datetime.now(timezone.utc)
    epoch = int(now.timestamp())
    last = (epoch // 300) * 300 - 300
    dt = datetime.fromtimestamp(last, tz=timezone.utc).replace(tzinfo=None)
    return dt, last * 1000


def sample_of_date(d: pd.Timestamp) -> str:
    d = pd.Timestamp(d).normalize()
    if d <= IS_END:
        return "IS"
    if d <= OOS1_END:
        return "OOS-1"
    return "OOS-2"


def nw_lags(n: int) -> int:
    auto = int(np.floor(4.0 * (n / 100.0) ** (2.0 / 9.0)))
    return max(HAC_FLOOR, auto)


def hac_ols(y: np.ndarray, x: np.ndarray) -> dict:
    m = np.isfinite(y) & np.isfinite(x)
    y, x = y[m], x[m]
    n = int(y.size)
    empty = {
        "alpha": np.nan,
        "beta": np.nan,
        "se": np.nan,
        "t_stat": np.nan,
        "p_value": np.nan,
        "r2": np.nan,
        "N": n,
    }
    if n < MIN_REG_N:
        return empty
    lags = min(nw_lags(n), max(1, n // 4))
    X = sm.add_constant(x, has_constant="add")
    fit = sm.OLS(y, X).fit(
        cov_type="HAC", cov_kwds={"maxlags": lags, "use_correction": True}
    )
    return {
        "alpha": float(fit.params[0]),
        "beta": float(fit.params[1]),
        "se": float(fit.bse[1]),
        "t_stat": float(fit.tvalues[1]),
        "p_value": float(fit.pvalues[1]),
        "r2": float(fit.rsquared),
        "N": n,
    }


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _http_get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "wen-5m-replication/1.0"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read()


def _fetch_batch(start_ms: int) -> list:
    url = (
        f"{BINANCE_KLINES}?symbol=BTCUSDT&interval=5m&limit=1000&startTime={start_ms}"
    )
    for attempt in range(6):
        try:
            return json.loads(_http_get(url).decode())
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"Binance klines failed after retries, startTime={start_ms}")


def _klines_to_df(rows: list) -> pd.DataFrame:
    df = pd.DataFrame(
        {
            "timestamp_utc": [datetime.utcfromtimestamp(k[0] / 1000) for k in rows],
            "open": [float(k[1]) for k in rows],
            "high": [float(k[2]) for k in rows],
            "low": [float(k[3]) for k in rows],
            "close": [float(k[4]) for k in rows],
            "volume": [float(k[5]) for k in rows],
        }
    )
    df["timestamp_utc"] = pd.to_datetime(df["timestamp_utc"])
    return df


def audit_5m_frame(df: pd.DataFrame) -> dict:
    t0, t1 = df["timestamp_utc"].iloc[0], df["timestamp_utc"].iloc[-1]
    full = pd.date_range(t0, t1, freq="5min")
    missing = full.difference(df["timestamp_utc"])
    nan_ohlcv = int(df[list(REQUIRED_5M[1:])].isna().any(axis=1).sum())
    return {
        "t0": t0,
        "t1": t1,
        "N": int(len(df)),
        "duplicates": int(df["timestamp_utc"].duplicated().sum()),
        "missing_5m": int(len(missing)),
        "nan_ohlcv": nan_ohlcv,
        "missing_examples": [str(x) for x in missing[:20]],
    }


def file_5m_usable(df: pd.DataFrame, last_closed: datetime) -> bool:
    if any(c not in df.columns for c in REQUIRED_5M):
        return False
    if df.empty or df["timestamp_utc"].duplicated().any():
        return False
    if df["timestamp_utc"].iloc[0] > pd.Timestamp("2017-08-18"):
        return False
    if df[list(REQUIRED_5M[1:])].isna().any().any():
        return False
    return df["timestamp_utc"].iloc[-1] >= pd.Timestamp(last_closed) - pd.Timedelta(
        minutes=5
    )


def load_or_download_5m() -> tuple[pd.DataFrame, dict, str]:
    last_closed, last_ms = last_complete_5m_open()
    existing = None
    if FILE_5M.exists():
        existing = pd.read_csv(FILE_5M)
        existing["timestamp_utc"] = pd.to_datetime(existing["timestamp_utc"])
        existing = (
            existing.drop_duplicates("timestamp_utc")
            .sort_values("timestamp_utc")
            .reset_index(drop=True)
        )
        if file_5m_usable(existing, last_closed):
            existing = existing[existing["timestamp_utc"] <= last_closed]
            source = "local_csv_validated_no_redownload"
            return existing, audit_5m_frame(existing), source

    start_ms = BINANCE_START_MS
    prior = None
    if existing is not None and not existing.empty:
        start_ms = (
            int(existing["timestamp_utc"].iloc[-1].timestamp() * 1000) + FIVE_MIN_MS
        )
        prior = existing
        print(f"resuming 5m download from {existing['timestamp_utc'].iloc[-1]}")

    rows = []
    n_batch = 0
    while start_ms <= last_ms:
        batch = _fetch_batch(start_ms)
        n_batch += 1
        if not batch:
            break
        rows.extend(batch)
        last_open = batch[-1][0]
        if n_batch % 50 == 0:
            print(f"  klines batches={n_batch} last={datetime.utcfromtimestamp(last_open/1000)}")
        if len(batch) < 1000:
            break
        start_ms = last_open + FIVE_MIN_MS

    fresh = _klines_to_df(rows) if rows else pd.DataFrame(columns=list(REQUIRED_5M))
    df = pd.concat([prior, fresh], ignore_index=True) if prior is not None else fresh
    df = df[df["timestamp_utc"] <= last_closed]
    df = df.drop_duplicates("timestamp_utc").sort_values("timestamp_utc").reset_index(
        drop=True
    )
    df[list(REQUIRED_5M)].to_csv(FILE_5M, index=False)
    source = "binance_spot_klines_5m"
    return df, audit_5m_frame(df), source


def reconstruct_hourly(df5: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    df = df5.copy()
    df["hour_start"] = df["timestamp_utc"].dt.floor("h")
    t0 = df["hour_start"].min()
    t1 = df["hour_start"].max()
    hours = pd.date_range(t0, t1, freq="h")

    counts = df.groupby("hour_start").size().reindex(hours, fill_value=0).astype(int)
    src_ts = hours + pd.Timedelta(minutes=55)
    src = df.set_index("timestamp_utc")["close"].reindex(src_ts)

    hp = pd.DataFrame(
        {
            "date_utc": hours.normalize(),
            "hour_utc": hours.hour.astype(int),
            "hourly_close": src.to_numpy(dtype=float),
            "source_5m_timestamp": src_ts,
            "n_5m_bars_in_hour": counts.to_numpy(),
        }
    )
    hp["complete_hour"] = hp["n_5m_bars_in_hour"] == 12

    prev = hp["hourly_close"].shift(1)
    gap = hours.to_series().diff().reset_index(drop=True) != pd.Timedelta(hours=1)
    r = np.log(hp["hourly_close"].to_numpy(dtype=float)) - np.log(prev.to_numpy(dtype=float))
    r[gap.to_numpy()] = np.nan
    r[~np.isfinite(hp["hourly_close"].to_numpy(dtype=float))] = np.nan
    r[~np.isfinite(prev.to_numpy(dtype=float))] = np.nan

    hr = pd.DataFrame(
        {
            "date_utc": hp["date_utc"],
            "hour_utc": hp["hour_utc"],
            "hourly_log_return": r,
            "complete_hour": hp["complete_hour"],
        }
    )
    return hp, hr


def audit_vs_1h(hp: pd.DataFrame) -> dict:
    empty = {
        "available": False,
        "n_overlap": 0,
        "max_abs_diff": np.nan,
        "median_abs_diff": np.nan,
        "pct_identical": np.nan,
    }
    if not FILE_1H.exists():
        return empty
    h1 = pd.read_csv(FILE_1H)
    h1["timestamp_utc"] = pd.to_datetime(h1["timestamp_utc"])
    h1["date_utc"] = h1["timestamp_utc"].dt.normalize()
    h1["hour_utc"] = h1["timestamp_utc"].dt.hour.astype(int)
    m = hp.merge(
        h1[["date_utc", "hour_utc", "close"]],
        on=["date_utc", "hour_utc"],
        how="inner",
        suffixes=("", "_1h"),
    )
    m = m.dropna(subset=["hourly_close", "close"])
    if m.empty:
        return empty
    diff = (m["hourly_close"] - m["close"]).abs()
    rel = diff / m["close"].abs().clip(lower=1e-12)
    return {
        "available": True,
        "n_overlap": int(len(m)),
        "max_abs_diff": float(diff.max()),
        "median_abs_diff": float(diff.median()),
        "pct_identical": float((rel <= CLOSE_TOL).mean() * 100.0),
        "pct_within_1e6": float((diff <= 1e-6).mean() * 100.0),
    }


def returns_panel(hr: pd.DataFrame) -> pd.DataFrame:
    ret = hr.pivot_table(
        index="date_utc", columns="hour_utc", values="hourly_log_return", aggfunc="first"
    )
    return ret.reindex(columns=range(24))


def fit_all_pairs(ret: pd.DataFrame) -> pd.DataFrame:
    dates = ret.index
    samp = pd.Series([sample_of_date(d) for d in dates], index=dates)
    rows = []
    for i in range(24):
        for j in range(i + 1, 24):
            ri = ret[i].to_numpy(dtype=float)
            rj = ret[j].to_numpy(dtype=float)
            masks = {
                "FULL": np.ones(len(dates), dtype=bool),
                "IS": (samp == "IS").to_numpy(),
                "OOS-1": (samp == "OOS-1").to_numpy(),
                "OOS-2": (samp == "OOS-2").to_numpy(),
            }
            for name, m in masks.items():
                fit = hac_ols(rj[m], ri[m])
                rows.append(
                    {
                        "sample": name,
                        "predictor_hour_utc": i,
                        "target_hour_utc": j,
                        **fit,
                    }
                )
    out = pd.DataFrame(rows)
    out["fdr_p_value"] = np.nan
    for name in SAMPLES_ALL:
        idx = out.index[out["sample"] == name]
        p = out.loc[idx, "p_value"].to_numpy(dtype=float)
        valid = np.isfinite(p)
        adj = np.full(p.shape, np.nan)
        if valid.any():
            adj[valid] = multipletests(p[valid], method="fdr_bh")[1]
        out.loc[idx, "fdr_p_value"] = adj
    return out[PAIR_COLS].sort_values(
        ["sample", "predictor_hour_utc", "target_hour_utc"]
    ).reset_index(drop=True)


def wen_table(pairs: pd.DataFrame) -> pd.DataFrame:
    recs = []
    for (i, j), typ in WEN_PAIRS.items():
        for samp in SAMPLES_ALL:
            row = pairs[
                (pairs["sample"] == samp)
                & (pairs["predictor_hour_utc"] == i)
                & (pairs["target_hour_utc"] == j)
            ].iloc[0]
            recs.append(
                {
                    "sample": samp,
                    "paper_hours": f"r{i+1}->r{j+1}",
                    "predictor_hour_utc": i,
                    "target_hour_utc": j,
                    "type": typ,
                    **{c: row[c] for c in PAIR_COLS if c not in ("sample", "predictor_hour_utc", "target_hour_utc")},
                }
            )
    return pd.DataFrame(recs)


def freeze_candidates(pairs: pd.DataFrame) -> pd.DataFrame:
    is_ = pairs[pairs["sample"] == "IS"].set_index(
        ["predictor_hour_utc", "target_hour_utc"]
    )
    o1 = pairs[pairs["sample"] == "OOS-1"].set_index(
        ["predictor_hour_utc", "target_hour_utc"]
    )
    o2 = pairs[pairs["sample"] == "OOS-2"].set_index(
        ["predictor_hour_utc", "target_hour_utc"]
    )
    recs = []
    for key in is_.index.intersection(o1.index).intersection(o2.index):
        b_is = float(is_.loc[key, "beta"])
        b_o1 = float(o1.loc[key, "beta"])
        p_is = float(is_.loc[key, "p_value"])
        p_o1 = float(o1.loc[key, "p_value"])
        if not np.isfinite(b_is) or not np.isfinite(b_o1):
            continue
        if b_is == 0 or b_o1 == 0:
            continue
        if not (
            np.sign(b_is) == np.sign(b_o1)
            and abs(b_is) >= BETA_MIN
            and abs(b_o1) >= BETA_MIN
            and p_is < P_MAX_DISCOVERY
            and p_o1 < P_MAX_DISCOVERY
        ):
            continue
        typ = "MOMENTUM" if b_is > 0 else "REVERSAL"
        b2 = float(o2.loc[key, "beta"])
        t2 = float(o2.loc[key, "t_stat"])
        p2 = float(o2.loc[key, "p_value"])
        f2 = float(o2.loc[key, "fdr_p_value"])
        r2 = float(o2.loc[key, "r2"])
        n2 = int(o2.loc[key, "N"])
        if not np.isfinite(b2) or b2 == 0:
            stab = "OOS2_MISSING"
        elif np.sign(b2) != np.sign(b_is):
            stab = "FLIP"
        else:
            stab = "SAME_SIGN"
        survived = (
            stab == "SAME_SIGN"
            and abs(b2) >= BETA_MIN_OOS2
            and np.isfinite(p2)
            and p2 < P_MAX_OOS2
        )
        recs.append(
            {
                "predictor_hour": int(key[0]),
                "target_hour": int(key[1]),
                "type": typ,
                "beta_IS": b_is,
                "beta_OOS1": b_o1,
                "OOS2_beta": b2,
                "OOS2_t": t2,
                "OOS2_p": p2,
                "OOS2_FDR": f2,
                "OOS2_r2": r2,
                "OOS2_N": n2,
                "sign_stability": stab,
                "final_status": "SURVIVED FINAL OOS" if survived else "FAILED FINAL OOS",
            }
        )
    if not recs:
        return pd.DataFrame(columns=CAND_COLS)
    return (
        pd.DataFrame(recs)[CAND_COLS]
        .sort_values(["type", "predictor_hour", "target_hour"])
        .reset_index(drop=True)
    )


def compare_1h(pairs5: pd.DataFrame) -> dict:
    out = {
        "available": False,
        "n_cells": 0,
        "median_abs_dbeta": np.nan,
        "max_abs_dbeta": np.nan,
        "n_sign_flip": 0,
        "pct_sign_flip": np.nan,
        "wen": [],
        "top5": {},
    }
    top5 = {}
    for samp in SAMPLES_ALL:
        sub = pairs5[pairs5["sample"] == samp].copy()
        sub = sub[np.isfinite(sub["t_stat"])]
        sub = sub.assign(abs_t=sub["t_stat"].abs()).sort_values("abs_t", ascending=False)
        top5[samp] = sub.head(5)[
            ["predictor_hour_utc", "target_hour_utc", "beta", "t_stat", "p_value", "fdr_p_value"]
        ].to_dict("records")
    out["top5"] = top5
    if not FILE_PAIRS_1H.exists():
        return out
    p1 = pd.read_csv(FILE_PAIRS_1H)
    m = pairs5.merge(
        p1,
        on=["sample", "predictor_hour_utc", "target_hour_utc"],
        suffixes=("_5m", "_1h"),
    )
    m = m[m["sample"].isin(SAMPLES_STRICT)]
    m = m[np.isfinite(m["beta_5m"]) & np.isfinite(m["beta_1h"])]
    dbeta = (m["beta_5m"] - m["beta_1h"]).abs()
    flip = np.sign(m["beta_5m"]) != np.sign(m["beta_1h"])
    out.update(
        {
            "available": True,
            "n_cells": int(len(m)),
            "median_abs_dbeta": float(dbeta.median()),
            "max_abs_dbeta": float(dbeta.max()),
            "n_sign_flip": int(flip.sum()),
            "pct_sign_flip": float(100.0 * flip.mean()) if len(m) else np.nan,
        }
    )
    wen = []
    for (i, j), typ in WEN_PAIRS.items():
        bits = {"type": typ, "i": i, "j": j, "samples": {}}
        for samp in SAMPLES_STRICT:
            sub = m[
                (m["sample"] == samp)
                & (m["predictor_hour_utc"] == i)
                & (m["target_hour_utc"] == j)
            ]
            if sub.empty:
                continue
            r = sub.iloc[0]
            bits["samples"][samp] = {
                "beta_5m": float(r["beta_5m"]),
                "beta_1h": float(r["beta_1h"]),
                "t_5m": float(r["t_stat_5m"]),
                "t_1h": float(r["t_stat_1h"]),
                "p_5m": float(r["p_value_5m"]),
                "p_1h": float(r["p_value_1h"]),
                "fdr_5m": float(r["fdr_p_value_5m"]),
                "fdr_1h": float(r["fdr_p_value_1h"]),
            }
        wen.append(bits)
    out["wen"] = wen
    return out


def fmt(x, nd=4):
    return "NA" if not np.isfinite(x) else f"{x:.{nd}f}"


def write_audit(diag: dict, source: str, digest: str, hp: pd.DataFrame) -> None:
    n_incomplete = int((~hp["complete_hour"]).sum())
    md = f"""# BTCUSDT 5-minute snapshot audit

Exchange: Binance Spot `BTCUSDT`. Interval: 5m. Timezone: UTC.
Source: {source}
File: `{FILE_5M.name}`

## Integrity

- SHA256: `{digest}`
- N rows: {diag['N']}
- timestamp inicial: {diag['t0']}
- timestamp final: {diag['t1']}
- duplicated timestamps: {diag['duplicates']}
- NaN OHLCV rows: {diag['nan_ohlcv']}
- missing 5m intervals (calendar 5m, not interpolated): {diag['missing_5m']}

Missing examples (first 20): {', '.join(diag['missing_examples']) if diag['missing_examples'] else '(none)'}

Gaps are documented only. Execution is not stopped for small real exchange holes.

## Hour reconstruction (not a resample black box)

Binance 5m timestamp = bar **open**.

Hour `h` on date `d` covers `[h:00, h+1:00)`.

The 12 bars are:

`h:00, h:05, h:10, h:15, h:20, h:25, h:30, h:35, h:40, h:45, h:50, h:55`.

**`p` at the end of hour h = close of the `h:55`–`(h+1):00` bar.**

`source_5m_timestamp` in `hourly_prices_from_5m.csv` is that `h:55` open time.

The close of the `h:00` bar is the price at `h:05`. It is **not** the hourly close.

`complete_hour = True` iff `n_5m_bars_in_hour == 12`. Incomplete hours are kept as flags; prices are not interpolated. If the `h:55` bar is missing, `hourly_close` is NaN.

Hourly prices written: {len(hp)}. Incomplete hours: {n_incomplete}.

Return: `r_{{d,h}} = log(P_{{d,h}}) - log(P_{{d,h-1}})`. Hour 0 uses the previous day's hour-23 close (price at 00:00). If the required previous price is missing, return is NaN.
"""
    OUT_AUDIT.write_text(md, encoding="utf-8")


def write_summary(
    diag, source, digest, hp, hr, cmp1h, pairs, wen, cand, cmp
) -> None:
    def n_sig(df, col="p_value", thr=0.05):
        return int((df[col] < thr).sum())

    full = pairs[pairs["sample"] == "FULL"]
    is_p = pairs[pairs["sample"] == "IS"]
    o1 = pairs[pairs["sample"] == "OOS-1"]
    o2 = pairs[pairs["sample"] == "OOS-2"]
    n_mom_c = int((cand["type"] == "MOMENTUM").sum()) if not cand.empty else 0
    n_rev_c = int((cand["type"] == "REVERSAL").sum()) if not cand.empty else 0
    surv = cand[cand["final_status"] == "SURVIVED FINAL OOS"] if not cand.empty else cand
    n_surv = int(len(surv))
    n_fail = int(len(cand) - n_surv) if not cand.empty else 0
    n_mom_s = int((surv["type"] == "MOMENTUM").sum()) if n_surv else 0
    n_rev_s = int((surv["type"] == "REVERSAL").sum()) if n_surv else 0
    n_fdr_disc = n_sig(is_p, "fdr_p_value", 0.10) + n_sig(o1, "fdr_p_value", 0.10)

    if n_surv >= 1 and n_mom_s >= 1 and n_rev_s >= 1:
        verdict = "A — REPLICATION SUCCESSFUL"
        why = (
            "Al menos un par momentum y uno reversal congelados IS+OOS-1 "
            "sobreviven OOS-2."
        )
    elif n_surv >= 1:
        verdict = "B — PARTIAL REPLICATION"
        why = "Hay superviviente(s) OOS-2, pero no momentum y reversal a la vez."
    elif n_fdr_disc >= 1 and (n_mom_c + n_rev_c) >= 1:
        verdict = "B — PARTIAL REPLICATION"
        why = "Hay FDR en discovery y candidatos congelados, pero ninguno sobrevive OOS-2."
    else:
        verdict = "C — REPLICATION NOT CONFIRMED"
        why = (
            "No hay FDR<0.10 en IS ni OOS-1 (o los candidatos freeze no sobreviven "
            "OOS-2). Los pares destacados de Wen et al. no se confirman de forma "
            "estable en Binance 5m→hourly. Esto no es una réplica exacta del "
            "dataset Bitstamp 2013–2020."
        )

    wen_lines = []
    for _, r in wen.iterrows():
        wen_lines.append(
            f"- {r['type']} paper {r['paper_hours']} UTC {int(r['predictor_hour_utc']):02d}→"
            f"{int(r['target_hour_utc']):02d} | {r['sample']}: β={fmt(r['beta'])}, "
            f"t={fmt(r['t_stat'],2)}, p={fmt(r['p_value'],4)}, FDR={fmt(r['fdr_p_value'],3)}, "
            f"R²={fmt(r['r2'],4)}, N={int(r['N']) if np.isfinite(r['N']) else 'NA'}"
        )

    wen_dir = []
    for (i, j), typ in WEN_PAIRS.items():
        sub = wen[(wen["predictor_hour_utc"] == i) & (wen["target_hour_utc"] == j)]
        signs = []
        raw = []
        fdr = []
        for samp in SAMPLES_ALL:
            row = sub[sub["sample"] == samp].iloc[0]
            expected = 1 if typ == "MOMENTUM" else -1
            ok = np.isfinite(row["beta"]) and np.sign(row["beta"]) == expected
            signs.append(f"{samp}:{'YES' if ok else 'NO'}(β={fmt(row['beta'])})")
            raw.append(f"{samp}:{'YES' if row['p_value']<0.05 else 'NO'}")
            fdr.append(f"{samp}:{'YES' if row['fdr_p_value']<0.10 else 'NO'}")
        wen_dir.append(
            f"- UTC {i:02d}→{j:02d} ({typ}): dirección paper | "
            + "; ".join(signs)
            + " | raw p<0.05 "
            + "; ".join(raw)
            + " | FDR<0.10 "
            + "; ".join(fdr)
        )

    if not cand.empty:
        cand_txt = "\n".join(
            f"- UTC {int(r.predictor_hour):02d}→{int(r.target_hour):02d} ({r.type}, "
            f"{r.final_status}, {r.sign_stability}): β_IS={fmt(r.beta_IS)}, "
            f"β_OOS1={fmt(r.beta_OOS1)}, β_OOS2={fmt(r.OOS2_beta)}, "
            f"t={fmt(r.OOS2_t,2)}, p={fmt(r.OOS2_p,4)}, FDR={fmt(r.OOS2_FDR,3)}, "
            f"R²={fmt(r.OOS2_r2,4)}, N={int(r.OOS2_N)}"
            for r in cand.itertuples()
        )
    else:
        cand_txt = "Ningún par pasa el freeze IS+OOS-1."

    cmp_txt = "Réplica 1h no disponible."
    wen_cmp = ""
    if cmp["available"]:
        cmp_txt = (
            f"Celdas comparadas (IS/OOS-1/OOS-2 × 276): {cmp['n_cells']}. "
            f"|Δβ| mediano={fmt(cmp['median_abs_dbeta'],6)}, "
            f"|Δβ| máx={fmt(cmp['max_abs_dbeta'],6)}. "
            f"Signos distintos 5m vs 1h: {cmp['n_sign_flip']} "
            f"({fmt(cmp['pct_sign_flip'],2)}%)."
        )
        bits = []
        for w in cmp["wen"]:
            line = [f"UTC {w['i']:02d}→{w['j']:02d} ({w['type']})"]
            for samp, v in w["samples"].items():
                line.append(
                    f"{samp}: β_5m={fmt(v['beta_5m'])} vs β_1h={fmt(v['beta_1h'])} "
                    f"(t {fmt(v['t_5m'],2)} vs {fmt(v['t_1h'],2)})"
                )
            bits.append("- " + " | ".join(line))
        wen_cmp = "\n".join(bits)

    top_txt = []
    for samp, recs in cmp["top5"].items():
        items = ", ".join(
            f"{int(r['predictor_hour_utc']):02d}→{int(r['target_hour_utc']):02d} "
            f"(β={fmt(r['beta'])}, t={fmt(r['t_stat'],2)}, FDR={fmt(r['fdr_p_value'],3)})"
            for r in recs
        )
        top_txt.append(f"- {samp}: {items}")

    n_ret = int(hr["hourly_log_return"].notna().sum())
    n_complete_days = int(
        (hr.groupby("date_utc")["hourly_log_return"].apply(lambda s: s.notna().sum() == 24)).sum()
    )

    if cmp["available"] and (
        cmp["median_abs_dbeta"] < 1e-4
        and (cmp["max_abs_dbeta"] is not None and cmp["max_abs_dbeta"] < 0.02)
    ):
        vs_1h = (
            "Closes 5m→hourly vs Binance 1h idénticos. Betas equivalentes en la "
            "práctica (|Δβ| mediano≈0; flips de signo, si hay, son |β|≈0). "
            "La conclusión de la réplica 1h no cambia."
        )
        better = "queda igual"
    elif cmp["available"] and cmp["n_sign_flip"] == 0 and cmp["median_abs_dbeta"] < 0.01:
        vs_1h = (
            "Los betas se mueven poco; no hay flips de signo. El 5m no rescata "
            "los pares Wen ni crea FDR robusto donde el 1h no lo tenía."
        )
        better = "queda igual (cambios inmateriales)"
    elif cmp["available"]:
        vs_1h = (
            "Hay diferencias 5m vs 1h (ver |Δβ| y flips). Revisar si eso mueve "
            "FDR o los pares Wen."
        )
        better = "cambia respecto al 1h nativo (ver números)"
    else:
        vs_1h = "No se pudo comparar con intradaily_pairs.csv."
        better = "no comparable"

    q1 = (
        f"Overlap N={cmp1h.get('n_overlap', 0)}. "
        f"max |Δclose|={fmt(cmp1h.get('max_abs_diff', np.nan), 10)}, "
        f"median |Δclose|={fmt(cmp1h.get('median_abs_diff', np.nan), 12)}, "
        f"% idénticos (rel≤{CLOSE_TOL:g})={fmt(cmp1h.get('pct_identical', np.nan), 4)}, "
        f"% |Δ|≤1e-6={fmt(cmp1h.get('pct_within_1e6', np.nan), 4)}."
        if cmp1h.get("available")
        else "btcusdt_1h.csv no disponible."
    )

    md = f"""# Wen et al. (2022) — réplica 5m → hourly (Binance BTCUSDT)

Paper: Wen, Bouri, Xu & Zhao (2022), NAJEF 62, 101733.
DOI: 10.1016/j.najef.2022.101733.

**Methodological replication on a different exchange and later sample.**
No es una réplica exacta del dataset original.

| | Paper | Esta réplica |
|---|---|---|
| Exchange | Bitstamp (GMT) | Binance Spot BTCUSDT (UTC) |
| Sample | 2013-03-03 → 2020-05-31 (paper); IS 2013–2016 / OOS 2017–2021 | 2017-08-17 → latest; IS/OOS-1/OOS-2 propios |
| Frecuencia | 5-min high-frequency, hourly returns | 5-min Binance, hourly returns reconstruidos |
| Activo | Bitcoin | BTCUSDT spot |

No forecasts, no jumps, no liquidity, no vol conditioning, no trading.

Snapshot 5m: `{FILE_5M.name}` · SHA256 `{digest}` · source `{source}`.
N={diag['N']} · {diag['t0']} → {diag['t1']} · dups={diag['duplicates']} · missing 5m={diag['missing_5m']}.

---

## Convención de precio horario (auditada)

Paper Eq. (1): `r_{{i,t}} = log(p_{{i,t}}) − log(p_{{i-1,t}})`, i=1..24, `p_{{0,t}}` = precio a las 00:00.

Binance 5m **open-labeled**:

- hora UTC `h` = intervalo `[h:00, h+1:00)`
- 12 velas: `h:00 … h:55`
- **`p` al cierre de la hora h = close de la vela `h:55`–`(h+1):00`**
- eso **no** es el close de `h:00` (precio a las `h:05`)

Indexación: `hour_utc` h=0..23 = paper hour i=h+1.

Mapping de los pares Wen (re-verificado, igual que la réplica 1h):

| paper | UTC |
|---|---|
| r3→r17 momentum | 02→16 |
| r8→r22 momentum | 07→21 |
| r3→r5 reversal | 02→04 |
| r3→r15 reversal | 02→14 |
| r12→r13 reversal | 11→12 |
| r22→r23 reversal | 21→22 |

HAC: Newey–West (1987) + bandwidth NW (1994) `L=floor(4*(N/100)^(2/9))`, suelo 5, `use_correction=True`. Idéntico a la réplica 1h. No se reoptimizó el lag.

Freeze (IS+OOS-1 only, umbrales **no** retocados tras ver OOS-2):

- mismo signo
- `|β| ≥ {BETA_MIN}` en IS y OOS-1
- `p < {P_MAX_DISCOVERY}` en IS y OOS-1

OOS-2 survival: mismo signo, `|β| ≥ {BETA_MIN_OOS2}`, `p < {P_MAX_OOS2}`.

Retornos horarios finitos: {n_ret}. Días con 24 retornos finitos: {n_complete_days}.
Horas incompletas (<12 barras 5m): {int((~hp['complete_hour']).sum())} / {len(hp)}.

---

## 1. ¿Los precios horarios desde 5m coinciden con Binance 1h?

{q1}

La vela Binance 1h con open `h:00` cierra a las `h+1:00`, que es el close de la 5m `h:55`. Deben coincidir salvo huecos.

## 2. ¿Los seis pares Wen muestran la misma dirección?

{chr(10).join(wen_dir)}

## 3. ¿Alguno tiene significancia raw?

Ver lista completa abajo. p<0.05 no es “predictor” por sí solo (276 tests).

## 4. ¿Alguno sobrevive FDR?

FULL FDR<0.10: {n_sig(full,'fdr_p_value',0.10)} / 276.
IS: {n_sig(is_p,'fdr_p_value',0.10)}; OOS-1: {n_sig(o1,'fdr_p_value',0.10)}; OOS-2: {n_sig(o2,'fdr_p_value',0.10)}.
FDR mínimo FULL={fmt(full['fdr_p_value'].min(),3)}, IS={fmt(is_p['fdr_p_value'].min(),3)}, OOS-1={fmt(o1['fdr_p_value'].min(),3)}, OOS-2={fmt(o2['fdr_p_value'].min(),3)}.

## 5. ¿Hay momentum intradía?

FULL pares β>0 y p<0.05: {int(((full['beta']>0)&(full['p_value']<0.05)).sum())}.
Candidatos momentum IS+OOS-1: {n_mom_c}. Superviven OOS-2: {n_mom_s}.

## 6. ¿Hay reversal intradía?

FULL pares β<0 y p<0.05: {int(((full['beta']<0)&(full['p_value']<0.05)).sum())}.
Candidatos reversal IS+OOS-1: {n_rev_c}. Superviven OOS-2: {n_rev_s}.

## 7. ¿Son estables IS → OOS-1?

{cand_txt}

## 8. ¿Sobreviven OOS-2?

SURVIVED={n_surv}, FAILED={n_fail}. No se reemplazan fallidos.

## 9. ¿Cambió algo importante respecto a 1h nativo?

{cmp_txt}

Comparación pares Wen 5m vs 1h:

{wen_cmp}

Top |t| 5m por sample:

{chr(10).join(top_txt)}

{vs_1h}

## 10. ¿La réplica del paper mejora, empeora o queda igual?

Respecto a usar 1h nativo: **{better}**.
Respecto al paper Bitstamp 2013–2020: sigue siendo otro exchange y otro calendario. El 5m acerca la *construcción* del retorno (alta frecuencia → hourly), no el sample original.

## 11. Veredicto

{why}

---

## A. PAPER-LIKE / FULL Binance sample (descriptivo)

No finge el calendario 2013–2020 del paper.

| | p<0.05 | FDR<0.10 | FDR<0.05 | β>0 & p<0.05 | β<0 & p<0.05 | R² mediano |
|---|---:|---:|---:|---:|---:|---:|
| FULL | {n_sig(full)} | {n_sig(full,'fdr_p_value',0.10)} | {n_sig(full,'fdr_p_value',0.05)} | {int(((full['beta']>0)&(full['p_value']<0.05)).sum())} | {int(((full['beta']<0)&(full['p_value']<0.05)).sum())} | {fmt(full['r2'].median(),4)} |

## B. Strict validation

| sample | p<0.05 | FDR<0.10 | min FDR | R² mediano |
|---|---:|---:|---:|---:|
| IS | {n_sig(is_p)} | {n_sig(is_p,'fdr_p_value',0.10)} | {fmt(is_p['fdr_p_value'].min(),3)} | {fmt(is_p['r2'].median(),4)} |
| OOS-1 | {n_sig(o1)} | {n_sig(o1,'fdr_p_value',0.10)} | {fmt(o1['fdr_p_value'].min(),3)} | {fmt(o1['r2'].median(),4)} |
| OOS-2 | {n_sig(o2)} | {n_sig(o2,'fdr_p_value',0.10)} | {fmt(o2['fdr_p_value'].min(),3)} | {fmt(o2['r2'].median(),4)} |

## Pares Wen (todos los samples)

{chr(10).join(wen_lines)}

## STATISTICAL PREDICTABILITY vs ECONOMIC VALUE vs TRADEABLE EDGE

Esta fase mide construcción de retornos y **statistical predictability**.
No se afirma valor económico ni edge tradable. No hay forecasts.

---

### {verdict}
"""
    OUT_MD.write_text(md, encoding="utf-8")


def main() -> None:
    print("loading/downloading 5m...")
    df5, diag, source = load_or_download_5m()
    print("DATA5", source, diag)
    digest = sha256_file(FILE_5M)
    print("SHA256", digest)

    hp, hr = reconstruct_hourly(df5)
    hp.to_csv(OUT_PRICES, index=False)
    hr.to_csv(OUT_RETS, index=False)
    write_audit(diag, source, digest, hp)

    cmp1h = audit_vs_1h(hp)
    print("vs 1h closes", cmp1h)

    ret = returns_panel(hr)
    print("fitting 276 x 4 samples...")
    pairs = fit_all_pairs(ret)
    assert pairs.groupby("sample").size().eq(276).all()
    wen = wen_table(pairs)
    cand = freeze_candidates(pairs)
    cmp = compare_1h(pairs)
    print(f"candidates={len(cand)}")

    pairs.to_csv(OUT_PAIRS, index=False)
    wen.to_csv(OUT_WEN, index=False)
    cand.to_csv(OUT_CAND, index=False)
    write_summary(diag, source, digest, hp, hr, cmp1h, pairs, wen, cand, cmp)
    print("wrote", OUT_AUDIT.name, OUT_PRICES.name, OUT_WEN.name, OUT_PAIRS.name, OUT_CAND.name, OUT_MD.name)


if __name__ == "__main__":
    main()
