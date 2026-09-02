#!/usr/bin/env python3
"""Phase 1 strategy lab: three frozen simple BTC strategies, with costs.

Not a live system. Not clean OOS. 2024–2026 is historical / temporal robustness.
"""

from __future__ import annotations

import csv
import io
import json
import ssl
import time
import urllib.error
import urllib.request
import warnings
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

PHASE = Path(__file__).resolve().parents[1]
RESULTS = PHASE / "results"
PROCESSED = PHASE / "data" / "processed"
TSR = PHASE.parent.parent
MSO = TSR.parent
REPO = MSO.parent.parent
RQF = MSO / "v1_weekly_core" / "regime_quality_framework"

H1_PATH = REPO / "btc_tsmom_replication" / "btcusdt_1h.csv"
TRUSTED_PRICES = REPO / "btc_tsmom_replication" / "data" / "btcusd_daily.csv"
PHASE1_BN = TSR / "phase1_capitulation_entries" / "data" / "raw" / "binance_btcusdt_1d.csv"
DERIV_PATH = (
    TSR
    / "phase3_information_expansion"
    / "phase3b_derivatives_dataset"
    / "data"
    / "processed"
    / "btc_derivatives_daily.csv"
)
MACRO_FROZEN = RQF / "phase6a_macro_dataset" / "results" / "macro_weekly.csv"
MACRO_CACHE = PROCESSED / "macro_weekly_extended.csv"

BINANCE_LISTING = date(2017, 8, 17)
FROZEN_MACRO_END = pd.Timestamp("2023-12-29")
MACRO_OOS_START = pd.Timestamp("2024-01-01")
START_CAP = 10_000.0
FEE_PRIMARY = 0.0010
FEE_SET = (0.0, 0.0010, 0.0020)
WINDOWS = (
    (0, 4, "00:00-04:00"),
    (4, 8, "04:00-08:00"),
    (8, 12, "08:00-12:00"),
    (12, 16, "12:00-16:00"),
    (16, 20, "16:00-20:00"),
    (20, 24, "20:00-24:00"),
)
B_HORIZONS = (3, 7, 14, 30, 60)
MIN_HIST = 365
OI_DROP = -0.10
VOL_REL = 2.0
MACRO_FEATS = ["DXY_CHG_12W", "US2Y_CHG_12W", "REAL10Y_CHG_12W", "NASDAQ_RET_12W"]
H_MACRO = 12
MIN_TRAIN = 100
LOGIT_C = 1.0
CLIP = 1e-6
P_THR = 0.50
CRYPTO_DAYS = 365.0
H10_BROAD_DOLLAR = "122e3bcb627e8e53f1bf72a1a09cfb81"
H15_TREASURY = "bf17364827e38702b42a58cf8eaa3f78"
UA = "tikiaventura-strategy-lab-phase1/1.0 (academic research)"
MACRO_UA = "Mozilla/5.0 (research; strategy-lab-phase1)"
SSL_CTX = ssl.create_default_context()


def log(msg: str) -> None:
    print(msg, flush=True)


def last_complete_utc_day() -> date:
    return datetime.now(timezone.utc).date() - timedelta(days=1)


def http_get(url: str, ua: str = UA, timeout: int = 90, retries: int = 4) -> bytes:
    last_err: Exception | None = None
    for attempt in range(1, retries + 1):
        req = urllib.request.Request(url, headers={"User-Agent": ua})
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


def fmt_num(x, nd=4) -> str:
    if x is None or (isinstance(x, float) and not np.isfinite(x)) or pd.isna(x):
        return "NA"
    return f"{x:.{nd}f}"


def fmt_pct(x, nd=2) -> str:
    if x is None or (isinstance(x, float) and not np.isfinite(x)) or pd.isna(x):
        return "NA"
    return f"{100.0 * x:.{nd}f}%"


def fmt_usd(x) -> str:
    if x is None or (isinstance(x, float) and not np.isfinite(x)) or pd.isna(x):
        return "NA"
    return f"${x:,.0f}"


def expanding_extreme_1d(ret: np.ndarray, min_n: int = MIN_HIST) -> np.ndarray:
    n = len(ret)
    flag = np.zeros(n, dtype=bool)
    for t in range(n):
        xt = ret[t]
        if not np.isfinite(xt):
            continue
        hist = ret[:t]
        hist = hist[np.isfinite(hist)]
        if hist.size < min_n:
            continue
        thr = float(np.percentile(hist, 5.0))
        flag[t] = xt <= thr
    return flag


def max_drawdown(equity: np.ndarray) -> float:
    eq = np.asarray(equity, dtype=float)
    eq = eq[np.isfinite(eq)]
    if eq.size == 0:
        return np.nan
    peak = np.maximum.accumulate(eq)
    dd = eq / peak - 1.0
    return float(np.min(dd))


def cagr_from(start_cap: float, end_cap: float, days: float) -> float:
    if not np.isfinite(start_cap) or not np.isfinite(end_cap) or start_cap <= 0 or days <= 0:
        return np.nan
    if end_cap <= 0:
        return -1.0
    return float((end_cap / start_cap) ** (CRYPTO_DAYS / days) - 1.0)


def trade_stats(net: np.ndarray) -> dict:
    x = np.asarray(net, dtype=float)
    x = x[np.isfinite(x)]
    n = int(x.size)
    out = {
        "n_trades": n,
        "win_rate": np.nan,
        "avg_trade": np.nan,
        "median_trade": np.nan,
        "avg_winner": np.nan,
        "avg_loser": np.nan,
        "payoff_ratio": np.nan,
        "profit_factor": np.nan,
    }
    if n == 0:
        return out
    wins = x[x > 0]
    losses = x[x < 0]
    out["win_rate"] = float(np.mean(x > 0))
    out["avg_trade"] = float(np.mean(x))
    out["median_trade"] = float(np.median(x))
    out["avg_winner"] = float(np.mean(wins)) if wins.size else np.nan
    out["avg_loser"] = float(np.mean(losses)) if losses.size else np.nan
    if np.isfinite(out["avg_winner"]) and np.isfinite(out["avg_loser"]) and out["avg_loser"] != 0:
        out["payoff_ratio"] = float(out["avg_winner"] / abs(out["avg_loser"]))
    gp = float(np.sum(wins)) if wins.size else 0.0
    gl = float(np.sum(np.abs(losses))) if losses.size else 0.0
    if gl > 0:
        out["profit_factor"] = gp / gl
    elif gp > 0:
        out["profit_factor"] = np.inf
    return out


def equity_metrics(eq: pd.Series, start_cap: float = START_CAP) -> dict:
    s = eq.dropna().astype(float)
    rec = {
        "start_date": pd.NaT,
        "end_date": pd.NaT,
        "starting_capital": start_cap,
        "ending_capital": np.nan,
        "total_return": np.nan,
        "cagr": np.nan,
        "annualized_volatility": np.nan,
        "sharpe": np.nan,
        "max_drawdown": np.nan,
        "calmar": np.nan,
        "n_days": 0,
    }
    if s.empty:
        return rec
    rec["start_date"] = pd.Timestamp(s.index.min())
    rec["end_date"] = pd.Timestamp(s.index.max())
    rec["ending_capital"] = float(s.iloc[-1])
    rec["total_return"] = float(s.iloc[-1] / start_cap - 1.0)
    days = float((s.index.max() - s.index.min()).days)
    rec["n_days"] = int(len(s))
    rec["cagr"] = cagr_from(start_cap, rec["ending_capital"], days)
    r = s.pct_change()
    r = r.replace([np.inf, -np.inf], np.nan).dropna()
    if len(r) >= 2 and float(r.std(ddof=1)) > 0:
        rec["annualized_volatility"] = float(r.std(ddof=1) * np.sqrt(CRYPTO_DAYS))
        rec["sharpe"] = float(r.mean() / r.std(ddof=1) * np.sqrt(CRYPTO_DAYS))
    elif len(r) >= 1:
        rec["annualized_volatility"] = 0.0
        rec["sharpe"] = np.nan
    rec["max_drawdown"] = max_drawdown(s.to_numpy())
    if np.isfinite(rec["cagr"]) and np.isfinite(rec["max_drawdown"]) and rec["max_drawdown"] < 0:
        rec["calmar"] = float(rec["cagr"] / abs(rec["max_drawdown"]))
    return rec


def buy_hold_equity(daily: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> pd.Series:
    d = daily.loc[(daily["date"] >= start) & (daily["date"] <= end), ["date", "close"]].copy()
    d = d.dropna(subset=["close"]).sort_values("date")
    if d.empty:
        return pd.Series(dtype=float)
    px = d["close"].to_numpy(dtype=float)
    eq = START_CAP * (px / px[0])
    return pd.Series(eq, index=pd.DatetimeIndex(d["date"]), name="buy_hold")


def year_rows(strategy: str, variant: str, fee: float, eq: pd.Series, trades: pd.DataFrame) -> list[dict]:
    rows = []
    if eq is None or eq.dropna().empty:
        return rows
    s = eq.dropna().astype(float)
    years = sorted(set(s.index.year))
    tr = trades.copy() if trades is not None and len(trades) else pd.DataFrame()
    if len(tr) and "entry_time" in tr.columns:
        tr["entry_year"] = pd.to_datetime(tr["entry_time"]).dt.year
    for y in years:
        sy = s.loc[s.index.year == y]
        if sy.empty:
            continue
        start_y = float(sy.iloc[0])
        end_y = float(sy.iloc[-1])
        ret = end_y / start_y - 1.0 if start_y > 0 else np.nan
        dd = max_drawdown(sy.to_numpy())
        n_tr = 0
        wr = np.nan
        if len(tr) and "entry_year" in tr.columns:
            yt = tr.loc[tr["entry_year"] == y]
            n_tr = int(len(yt))
            if n_tr:
                wr = float((yt["net_return"] > 0).mean())
        rows.append(
            {
                "strategy": strategy,
                "variant": variant,
                "period": f"year_{y}",
                "fee_bps_roundtrip": round(fee * 10_000.0, 1),
                "start_date": sy.index.min().date().isoformat(),
                "end_date": sy.index.max().date().isoformat(),
                "annual_return": ret,
                "n_trades": n_tr,
                "win_rate": wr,
                "max_drawdown": dd,
                "starting_capital": start_y,
                "ending_capital": end_y,
            }
        )
    return rows


def summary_row(
    strategy: str,
    variant: str,
    period: str,
    fee: float,
    eq: pd.Series,
    trades: pd.DataFrame,
    bh: pd.Series,
    exposure: float,
    fees_paid: float,
    extra: dict | None = None,
) -> dict:
    em = equity_metrics(eq)
    ts = trade_stats(trades["net_return"].to_numpy() if len(trades) else np.array([]))
    bh_m = equity_metrics(bh) if bh is not None and len(bh.dropna()) else {}
    years = np.nan
    if pd.notna(em["start_date"]) and pd.notna(em["end_date"]):
        years = max(float((em["end_date"] - em["start_date"]).days) / CRYPTO_DAYS, 1e-9)
    turnover = float(ts["n_trades"] / years) if np.isfinite(years) else np.nan
    rec = {
        "strategy": strategy,
        "variant": variant,
        "period": period,
        "start_date": em["start_date"].date().isoformat() if pd.notna(em["start_date"]) else "",
        "end_date": em["end_date"].date().isoformat() if pd.notna(em["end_date"]) else "",
        "fee_bps_roundtrip": round(fee * 10_000.0, 1),
        "starting_capital": START_CAP,
        "ending_capital": em["ending_capital"],
        "total_return": em["total_return"],
        "cagr": em["cagr"],
        "annualized_volatility": em["annualized_volatility"],
        "sharpe": em["sharpe"],
        "max_drawdown": em["max_drawdown"],
        "calmar": em["calmar"],
        "n_trades": ts["n_trades"],
        "win_rate": ts["win_rate"],
        "avg_trade": ts["avg_trade"],
        "median_trade": ts["median_trade"],
        "avg_winner": ts["avg_winner"],
        "avg_loser": ts["avg_loser"],
        "payoff_ratio": ts["payoff_ratio"],
        "profit_factor": ts["profit_factor"],
        "exposure": exposure,
        "turnover": turnover,
        "fees_paid": fees_paid,
        "benchmark_ending_capital": bh_m.get("ending_capital", np.nan),
        "benchmark_cagr": bh_m.get("cagr", np.nan),
        "benchmark_max_drawdown": bh_m.get("max_drawdown", np.nan),
    }
    if extra:
        rec.update(extra)
    return rec


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------


def load_hourly() -> pd.DataFrame:
    if not H1_PATH.exists():
        raise RuntimeError(
            f"No local 1h BTCUSDT file at {H1_PATH}. "
            "This phase prefers that file and will not silently switch coins or intervals."
        )
    df = pd.read_csv(H1_PATH)
    if "timestamp_utc" not in df.columns:
        raise RuntimeError("1h file missing timestamp_utc")
    df["ts"] = pd.to_datetime(df["timestamp_utc"], utc=True).dt.tz_convert(None)
    for c in ("open", "high", "low", "close"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.dropna(subset=["ts", "open", "close"]).sort_values("ts")
    df = df.drop_duplicates("ts")
    df["hour"] = df["ts"].dt.hour
    df["date"] = df["ts"].dt.normalize()
    last_day = df["date"].max()
    hours_last = set(df.loc[df["date"] == last_day, "hour"])
    if len(hours_last) < 24:
        df = df.loc[df["date"] < last_day].copy()
        log(f"dropped incomplete last 1h day {last_day.date()} hours={sorted(hours_last)[:8]}...")
    log(f"1h BTCUSDT {df['date'].min().date()} → {df['date'].max().date()} bars={len(df)}")
    return df.reset_index(drop=True)


def load_daily() -> pd.DataFrame:
    if not TRUSTED_PRICES.exists():
        raise RuntimeError(f"Trusted BTC daily file missing: {TRUSTED_PRICES}")
    if not PHASE1_BN.exists():
        raise RuntimeError(f"Phase 1 Binance daily missing: {PHASE1_BN}. Do not substitute.")
    trusted = pd.read_csv(TRUSTED_PRICES, parse_dates=["date"])
    trusted["date"] = pd.to_datetime(trusted["date"]).dt.normalize()
    trusted["close"] = pd.to_numeric(trusted["close"], errors="coerce")
    bn = pd.read_csv(PHASE1_BN, parse_dates=["date"])
    bn["date"] = pd.to_datetime(bn["date"]).dt.normalize()
    bn["close"] = pd.to_numeric(bn["close"], errors="coerce")
    t_bn = trusted.loc[trusted["source"] == "binance_btcusdt", ["date", "close"]]
    overlap = t_bn.merge(bn[["date", "close"]], on="date", suffixes=("_trusted", "_bn"))
    if overlap.empty:
        raise RuntimeError("No overlapping Binance dates vs trusted file.")
    rel = np.abs(overlap["close_bn"] / overlap["close_trusted"] - 1.0)
    if float(rel.max()) > 1e-6:
        raise RuntimeError(f"Binance daily diverges from trusted (max rel {float(rel.max()):.3e}). STOP.")
    pre = trusted.loc[trusted["source"] == "bitstamp_btcusd", ["date", "close"]].copy()
    pre = pre.loc[pre["date"].dt.date < BINANCE_LISTING]
    pre["source"] = "bitstamp_btcusd"
    post = bn.loc[bn["date"].dt.date >= BINANCE_LISTING, ["date", "close"]].copy()
    post["source"] = "binance_btcusdt"
    px = pd.concat([pre, post], ignore_index=True).sort_values("date").drop_duplicates("date")
    end = min(last_complete_utc_day(), px["date"].max().date())
    px = px.loc[px["date"].dt.date <= end].reset_index(drop=True)
    c = pd.to_numeric(px["close"], errors="coerce")
    px["ret_1d"] = c.pct_change()
    splice = pd.Timestamp(BINANCE_LISTING)
    px.loc[px["date"] == splice, "ret_1d"] = np.nan
    log(f"daily BTC {px['date'].min().date()} → {px['date'].max().date()} n={len(px)}")
    return px


def daily_ohlc_from_hourly(h1: pd.DataFrame) -> pd.DataFrame:
    g = h1.groupby("date", sort=True)
    out = pd.DataFrame(
        {
            "date": g.size().index,
            "high": g["high"].max().to_numpy(),
            "low": g["low"].min().to_numpy(),
        }
    )
    return out


def load_derivatives() -> pd.DataFrame:
    if not DERIV_PATH.exists():
        raise RuntimeError(f"Derivatives panel missing: {DERIV_PATH}")
    d = pd.read_csv(DERIV_PATH, parse_dates=["date"])
    d["date"] = pd.to_datetime(d["date"]).dt.normalize()
    need = ["oi_change_1d", "perp_volume_rel_30d"]
    miss = [c for c in need if c not in d.columns]
    if miss:
        raise RuntimeError(f"derivatives missing {miss}")
    log(f"derivatives {d['date'].min().date()} → {d['date'].max().date()} n={len(d)}")
    return d


def parse_fed_ddp(text: str, value_col: str) -> pd.DataFrame:
    rows = list(csv.reader(io.StringIO(text)))
    header_idx = None
    for i, row in enumerate(rows):
        if row and row[0].strip() == "Time Period":
            header_idx = i
            break
    if header_idx is None:
        raise RuntimeError("Fed DDP: Time Period row not found")
    header = rows[header_idx]
    if value_col not in header:
        raise RuntimeError(f"Fed DDP: column {value_col} not in {header[:12]}")
    j = header.index(value_col)
    dates, vals = [], []
    for row in rows[header_idx + 1 :]:
        if not row or not row[0].strip():
            continue
        dates.append(row[0].strip())
        cell = row[j].strip() if j < len(row) else ""
        vals.append(cell)
    out = pd.DataFrame({"date": pd.to_datetime(dates), "value": vals})
    out["value"] = pd.to_numeric(
        out["value"].replace({"ND": np.nan, "NA": np.nan, "": np.nan}), errors="coerce"
    )
    return out.dropna(subset=["date"]).sort_values("date").reset_index(drop=True)


def fed_ddp_url(rel: str, series: str, start: pd.Timestamp, end: pd.Timestamp) -> str:
    frm = start.strftime("%m/%d/%Y")
    to = end.strftime("%m/%d/%Y")
    return (
        "https://www.federalreserve.gov/datadownload/Output.aspx"
        f"?rel={rel}&series={series}&lastObs=&from={frm}&to={to}"
        "&filetype=csv&label=include&layout=seriescolumn"
    )


def asof_friday(daily: pd.DataFrame, weeks: pd.DatetimeIndex, value_col: str = "value") -> pd.Series:
    src = daily.dropna(subset=[value_col]).copy()
    src["date"] = pd.to_datetime(src["date"])
    src = src.sort_values("date")
    left = pd.DataFrame({"week": weeks})
    merged = pd.merge_asof(left, src[["date", value_col]], left_on="week", right_on="date", direction="backward")
    lag = (merged["week"] - merged["date"]).dt.days
    merged.loc[lag > 7, value_col] = np.nan
    return merged.set_index("week")[value_col]


def download_yahoo_ixic(end: pd.Timestamp) -> pd.DataFrame:
    start = datetime(2023, 9, 1, tzinfo=timezone.utc)
    end_dt = datetime(end.year, end.month, end.day, 23, 59, tzinfo=timezone.utc)
    url = (
        "https://query1.finance.yahoo.com/v8/finance/chart/%5EIXIC"
        f"?period1={int(start.timestamp())}&period2={int(end_dt.timestamp())}"
        "&interval=1d&events=div%2Csplit"
    )
    blob = json.loads(http_get(url, MACRO_UA).decode())
    result = blob.get("chart", {}).get("result")
    if not result:
        raise RuntimeError(f"Yahoo ^IXIC empty: {blob.get('chart', {}).get('error')}")
    res = result[0]
    ts = res.get("timestamp") or []
    close = (res.get("indicators") or {}).get("quote", [{}])[0].get("close") or []
    utc_dates = pd.to_datetime(ts, unit="s", utc=True)
    try:
        dates = utc_dates.tz_convert("America/New_York").normalize().tz_localize(None)
    except Exception:
        dates = utc_dates.tz_localize(None).normalize()
    df = pd.DataFrame({"date": dates, "value": pd.to_numeric(close, errors="coerce")})
    return df.dropna(subset=["date"]).drop_duplicates("date").sort_values("date")


def load_macro(last_week: pd.Timestamp) -> pd.DataFrame:
    if MACRO_CACHE.exists():
        cached = pd.read_csv(MACRO_CACHE, parse_dates=["week"])
        if cached["week"].max() >= last_week - pd.Timedelta(days=10):
            log(f"macro cache {cached['week'].min().date()} → {cached['week'].max().date()}")
            return cached.sort_values("week").reset_index(drop=True)
    frozen = pd.read_csv(MACRO_FROZEN, parse_dates=["week"])
    if (frozen["week"].dt.year >= 2024).any():
        raise RuntimeError("Frozen macro_weekly.csv already has 2024+.")
    miss = [c for c in ["DXY_LEVEL", "US2Y", "REAL10Y", "NASDAQ", *MACRO_FEATS] if c not in frozen.columns]
    if miss:
        raise RuntimeError(f"frozen macro missing {miss}")
    weeks_new = pd.date_range("2024-01-05", last_week, freq="W-FRI")
    start = pd.Timestamp("2023-09-01")
    end = last_week + pd.Timedelta(days=3)
    log("Macro extension H.10 / H.15 / TIPS / Nasdaq (same sources as Phase 6H)")
    h10 = parse_fed_ddp(
        http_get(fed_ddp_url("H10", H10_BROAD_DOLLAR, start, end), MACRO_UA).decode(),
        "JRXWTFB_N.B",
    )
    h15 = parse_fed_ddp(
        http_get(fed_ddp_url("H15", H15_TREASURY, start, end), MACRO_UA).decode(),
        "RIFLGFCY02_N.B",
    )
    tips_parts = []
    for year in range(2023, end.year + 1):
        url = (
            "https://home.treasury.gov/resource-center/data-chart-center/"
            f"interest-rates/daily-treasury-rates.csv/{year}/all"
            "?type=daily_treasury_real_yield_curve"
            f"&field_tdr_date_value={year}&page&_format=csv"
        )
        text = http_get(url, MACRO_UA).decode("utf-8")
        if "date" not in text.lstrip()[:80].lower():
            raise RuntimeError(f"Treasury TIPS {year}: unexpected payload.")
        part = pd.read_csv(io.StringIO(text))
        if "10 YR" not in part.columns:
            raise RuntimeError(f"Treasury TIPS {year}: no 10 YR column.")
        part["date"] = pd.to_datetime(part["Date"])
        part["value"] = pd.to_numeric(part["10 YR"], errors="coerce")
        tips_parts.append(part[["date", "value"]])
    tips = pd.concat(tips_parts, ignore_index=True).drop_duplicates("date")
    ixic = download_yahoo_ixic(end)
    new = pd.DataFrame({"week": weeks_new})
    new["DXY_LEVEL"] = asof_friday(h10, weeks_new).values
    new["US2Y"] = asof_friday(h15, weeks_new).values
    new["REAL10Y"] = asof_friday(tips, weeks_new).values
    new["NASDAQ"] = asof_friday(ixic, weeks_new).values
    levels = pd.concat(
        [frozen[["week", "DXY_LEVEL", "US2Y", "REAL10Y", "NASDAQ"]], new],
        ignore_index=True,
    ).sort_values("week").reset_index(drop=True)
    dxy, us2, real, ndq = levels["DXY_LEVEL"], levels["US2Y"], levels["REAL10Y"], levels["NASDAQ"]
    levels["DXY_CHG_12W"] = dxy / dxy.shift(12) - 1.0
    levels["US2Y_CHG_12W"] = us2 - us2.shift(12)
    levels["REAL10Y_CHG_12W"] = real - real.shift(12)
    levels["NASDAQ_RET_12W"] = ndq / ndq.shift(12) - 1.0
    hist_chk = levels.merge(
        frozen[["week", *MACRO_FEATS]].rename(columns={c: f"fr_{c}" for c in MACRO_FEATS}),
        on="week",
        how="inner",
    )
    hist_chk = hist_chk.loc[hist_chk["week"] <= FROZEN_MACRO_END]
    for c in MACRO_FEATS:
        both = hist_chk[c].notna() & hist_chk[f"fr_{c}"].notna()
        err = float(np.nanmax(np.abs(hist_chk.loc[both, c] - hist_chk.loc[both, f"fr_{c}"])))
        if err > 1e-10:
            raise RuntimeError(f"Spliced {c} mismatches frozen 2015–2023 (max abs {err}). STOP.")
    log("macro 2015–2023 splice exact match")
    hist = frozen[["week", *MACRO_FEATS]].copy()
    oos = levels.loc[levels["week"] >= MACRO_OOS_START, ["week", *MACRO_FEATS]]
    out = pd.concat([hist, oos], ignore_index=True).sort_values("week").reset_index(drop=True)
    PROCESSED.mkdir(parents=True, exist_ok=True)
    out.to_csv(MACRO_CACHE, index=False)
    return out


# ---------------------------------------------------------------------------
# Strategy A
# ---------------------------------------------------------------------------


def session_panel(h1: pd.DataFrame) -> pd.DataFrame:
    idx = h1.set_index("ts")
    rows = []
    dates = pd.DatetimeIndex(sorted(h1["date"].unique()))
    for d in dates:
        rec = {"date": d}
        complete = True
        for h0, h1h, name in WINDOWS:
            start = d + pd.Timedelta(hours=h0)
            end = d + pd.Timedelta(hours=h1h - 1)
            if start not in idx.index or end not in idx.index:
                rec[name] = np.nan
                rec[f"{name}_open"] = np.nan
                rec[f"{name}_close"] = np.nan
                complete = False
                continue
            o = float(idx.loc[start, "open"])
            c = float(idx.loc[end, "close"])
            rec[name] = c / o - 1.0 if o > 0 else np.nan
            rec[f"{name}_open"] = o
            rec[f"{name}_close"] = c
            rec[f"{name}_entry"] = start
            rec[f"{name}_exit"] = end + pd.Timedelta(hours=1)
        rec["all_six"] = complete and all(np.isfinite(rec.get(n, np.nan)) for *_, n in WINDOWS)
        rows.append(rec)
    panel = pd.DataFrame(rows)
    n_all = int(panel["all_six"].sum())
    log(f"session panel dates={len(panel)} complete_all_six={n_all}")
    return panel


def backtest_session(panel: pd.DataFrame, window: str, dates: pd.DatetimeIndex, fee: float):
    sub = panel.loc[panel["date"].isin(dates)].copy()
    sub = sub.sort_values("date")
    cap = START_CAP
    equity = []
    trades = []
    fees_paid = 0.0
    n_possible = 0
    n_done = 0
    for _, r in sub.iterrows():
        n_possible += 1
        g = r.get(window)
        if not np.isfinite(g):
            equity.append((r["date"], cap))
            continue
        n_done += 1
        px0 = float(r[f"{window}_open"])
        px1 = float(r[f"{window}_close"])
        before = cap
        after = before * (px1 / px0) * (1.0 - fee)
        fee_amt = before * (px1 / px0) * fee
        fees_paid += fee_amt
        net = after / before - 1.0
        trades.append(
            {
                "strategy": "A_session",
                "variant": window,
                "entry_time": r.get(f"{window}_entry"),
                "entry_price": px0,
                "exit_time": r.get(f"{window}_exit"),
                "exit_price": px1,
                "holding_period": "4h",
                "gross_return": float(g),
                "fee": fee,
                "net_return": net,
                "capital_before": before,
                "capital_after": after,
                "entry_reason": f"UTC window {window}",
                "mae": np.nan,
                "mfe": np.nan,
            }
        )
        cap = after
        equity.append((r["date"], cap))
    eq = pd.Series({d: v for d, v in equity}, dtype=float).sort_index()
    tr = pd.DataFrame(trades)
    exposure = (4.0 / 24.0) * (n_done / n_possible) if n_possible else np.nan
    return eq, tr, fees_paid, exposure


# ---------------------------------------------------------------------------
# Strategy B
# ---------------------------------------------------------------------------


def build_b_signals(daily: pd.DataFrame, deriv: pd.DataFrame) -> pd.DataFrame:
    df = daily.merge(deriv[["date", "oi_change_1d", "perp_volume_rel_30d"]], on="date", how="left")
    df = df.sort_values("date").reset_index(drop=True)
    extreme = expanding_extreme_1d(df["ret_1d"].to_numpy(dtype=float))
    oi = pd.to_numeric(df["oi_change_1d"], errors="coerce")
    volr = pd.to_numeric(df["perp_volume_rel_30d"], errors="coerce")
    raw = extreme & (oi <= OI_DROP) & (volr >= VOL_REL) & np.isfinite(oi) & np.isfinite(volr)
    df["extreme_1d"] = extreme
    df["raw_signal"] = raw
    first = df.loc[oi.notna() & volr.notna() & df["ret_1d"].notna(), "date"].min()
    log(
        f"B raw signals={int(raw.sum())} first_eligible={None if pd.isna(first) else first.date()} "
        f"oi_finite={int(oi.notna().sum())} volrel_finite={int(volr.notna().sum())}"
    )
    return df


def backtest_b(df: pd.DataFrame, ohlc: pd.DataFrame, horizon: int, fee: float):
    eligible = df.dropna(subset=["oi_change_1d", "perp_volume_rel_30d"]).copy()
    if eligible.empty:
        return pd.Series(dtype=float), pd.DataFrame(), 0.0, np.nan, pd.DataFrame()
    start = eligible["date"].min()
    end = df["date"].max()
    work = df.loc[(df["date"] >= start) & (df["date"] <= end)].copy().reset_index(drop=True)
    close = work["close"].to_numpy(dtype=float)
    dates = work["date"]
    raw = work["raw_signal"].to_numpy(dtype=bool)
    oh = ohlc.set_index("date") if len(ohlc) else None
    n = len(work)
    taken = np.zeros(n, dtype=bool)
    ignored = np.zeros(n, dtype=bool)
    in_trade = False
    exit_i = -1
    pos = np.zeros(n, dtype=bool)
    trades = []
    fees_paid = 0.0
    half = fee / 2.0
    cap = START_CAP
    equity = np.full(n, np.nan)
    equity[0] = cap
    for i in range(n):
        if i > 0:
            if in_trade:
                if close[i - 1] > 0 and np.isfinite(close[i]) and np.isfinite(close[i - 1]):
                    cap *= close[i] / close[i - 1]
            equity[i] = cap
        if in_trade and i == exit_i:
            before_fee = cap
            cap *= 1.0 - half
            fees_paid += before_fee * half
            in_trade = False
            if trades:
                trades[-1]["exit_price"] = float(close[i])
                trades[-1]["exit_time"] = dates.iloc[i]
                trades[-1]["capital_after"] = cap
                trades[-1]["net_return"] = cap / trades[-1]["capital_before"] - 1.0
                trades[-1]["gross_return"] = float(close[i] / trades[-1]["entry_price"] - 1.0)
            equity[i] = cap
        if (not in_trade) and raw[i] and (i + horizon) < n:
            taken[i] = True
            before = cap
            cap *= 1.0 - half
            fees_paid += before * half
            in_trade = True
            exit_i = i + horizon
            equity[i] = cap
            mae = mfe = np.nan
            entry_px = float(close[i])
            if oh is not None and entry_px > 0:
                path_dates = dates.iloc[i + 1 : i + 1 + horizon]
                highs, lows = [], []
                for dt in path_dates:
                    if dt in oh.index:
                        highs.append(float(oh.loc[dt, "high"]))
                        lows.append(float(oh.loc[dt, "low"]))
                    else:
                        j = int(np.where(dates == dt)[0][0])
                        highs.append(float(close[j]))
                        lows.append(float(close[j]))
                if highs:
                    mfe = max(highs) / entry_px - 1.0
                    mae = min(lows) / entry_px - 1.0
            trades.append(
                {
                    "strategy": "B_capitulation_deleveraging",
                    "variant": f"hold_{horizon}d",
                    "entry_time": dates.iloc[i],
                    "entry_price": entry_px,
                    "exit_time": dates.iloc[i + horizon],
                    "exit_price": np.nan,
                    "holding_period": f"{horizon}d",
                    "gross_return": np.nan,
                    "fee": fee,
                    "net_return": np.nan,
                    "capital_before": before,
                    "capital_after": np.nan,
                    "entry_reason": (
                        f"extreme_1d & oi_change_1d={float(work.iloc[i]['oi_change_1d']):.4f} "
                        f"& perp_volume_rel_30d={float(work.iloc[i]['perp_volume_rel_30d']):.3f}"
                    ),
                    "mae": mae,
                    "mfe": mfe,
                }
            )
        elif in_trade and raw[i]:
            ignored[i] = True
        if in_trade:
            pos[i] = True
    eq = pd.Series(equity, index=pd.DatetimeIndex(dates), dtype=float)
    tr = pd.DataFrame(trades)
    exposure = float(np.mean(pos)) if n else np.nan
    sig = work[["date", "close", "ret_1d", "oi_change_1d", "perp_volume_rel_30d", "raw_signal"]].copy()
    sig["taken"] = taken
    sig["ignored_overlap"] = ignored
    return eq, tr, fees_paid, exposure, sig


# ---------------------------------------------------------------------------
# Strategy C
# ---------------------------------------------------------------------------


def logit_fit_predict(X_train: np.ndarray, y_train: np.ndarray, x_t: np.ndarray) -> float:
    y = y_train.astype(int)
    if y.min() == y.max():
        return float(np.clip(float(y[0]), CLIP, 1.0 - CLIP))
    med = np.nanmedian(X_train, axis=0)
    med = np.where(np.isfinite(med), med, 0.0)
    X = np.where(np.isfinite(X_train), X_train, med)
    xt = np.where(np.isfinite(x_t), x_t, med).reshape(1, -1)
    scaler = StandardScaler()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        Xs = scaler.fit_transform(X)
        xts = scaler.transform(xt)
    clf = LogisticRegression(penalty="l2", C=LOGIT_C, solver="lbfgs", max_iter=2000, random_state=0)
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=ConvergenceWarning)
        warnings.filterwarnings("ignore", category=UserWarning)
        clf.fit(Xs, y)
    classes = list(clf.classes_)
    proba = clf.predict_proba(xts)[0]
    p = float(proba[classes.index(1)]) if 1 in classes else 0.0
    return float(np.clip(p, CLIP, 1.0 - CLIP))


def macro_walkforward(weekly: pd.DataFrame) -> pd.DataFrame:
    df = weekly.sort_values("week").reset_index(drop=True)
    c = pd.to_numeric(df["btc_close"], errors="coerce").to_numpy(dtype=float)
    n = len(df)
    fut = np.full(n, np.nan)
    for i in range(n):
        if i + H_MACRO >= n:
            continue
        if c[i] > 0 and np.isfinite(c[i]) and np.isfinite(c[i + H_MACRO]):
            fut[i] = c[i + H_MACRO] / c[i] - 1.0
    y = np.where(np.isfinite(fut), (fut > 0).astype(float), np.nan)
    X = df[MACRO_FEATS].to_numpy(dtype=float)
    feat_ok = np.all(np.isfinite(X), axis=1)
    y_ok = np.isfinite(y)
    p = np.full(n, np.nan)
    ntr = np.full(n, np.nan)
    for t in range(n):
        if not feat_ok[t]:
            continue
        end = t - H_MACRO
        if end < 0:
            continue
        train = np.zeros(n, dtype=bool)
        train[: end + 1] = True
        train &= y_ok
        nt = int(train.sum())
        ntr[t] = nt
        if nt < MIN_TRAIN:
            continue
        p[t] = logit_fit_predict(X[train], y[train], X[t])
    df["fut_12w"] = fut
    df["y_pos_12w"] = y
    df["p_macro"] = p
    df["n_train"] = ntr
    df["long"] = np.where(np.isfinite(p), p >= P_THR, np.nan)
    log(f"macro WF finite P={int(np.isfinite(p).sum())} long={(df['long']==1).sum()} cash={(df['long']==0).sum()}")
    return df


def backtest_c(daily: pd.DataFrame, weekly: pd.DataFrame, fee: float):
    w = weekly.loc[np.isfinite(weekly["p_macro"])].copy()
    if w.empty:
        return pd.Series(dtype=float), pd.DataFrame(), 0.0, np.nan, {}
    start = w["week"].min()
    d = daily.loc[daily["date"] >= start].copy().reset_index(drop=True)
    close = d["close"].to_numpy(dtype=float)
    dates = d["date"]
    n = len(d)
    decision = w.set_index("week")["long"].astype(float)
    pmap = w.set_index("week")["p_macro"]
    pos_ret = np.zeros(n, dtype=float)
    p_used = np.full(n, np.nan)
    for i in range(n):
        dt = dates.iloc[i]
        prior = decision.loc[decision.index < dt]
        if prior.empty:
            pos_ret[i] = 0.0
            continue
        pos_ret[i] = float(prior.iloc[-1])
        p_used[i] = float(pmap.loc[pmap.index < dt].iloc[-1])
    half = fee / 2.0
    cap = START_CAP
    equity = np.full(n, np.nan)
    equity[0] = cap
    fees_paid = 0.0
    trades = []
    in_long = False
    entry_i = None
    entry_px = None
    entry_cap = None
    pos_eod = np.zeros(n, dtype=float)
    for i in range(n):
        if i > 0:
            if in_long and close[i - 1] > 0 and np.isfinite(close[i]) and np.isfinite(close[i - 1]):
                cap *= close[i] / close[i - 1]
            equity[i] = cap
        is_friday = int(dates.iloc[i].weekday()) == 4
        target = None
        if is_friday and dates.iloc[i] in decision.index:
            target = float(decision.loc[dates.iloc[i]])
        if target is None:
            pos_eod[i] = 1.0 if in_long else 0.0
            continue
        want_long = target >= 0.5
        if want_long and not in_long:
            before = cap
            cap *= 1.0 - half
            fees_paid += before * half
            in_long = True
            entry_i = i
            entry_px = float(close[i])
            entry_cap = before
            equity[i] = cap
        elif (not want_long) and in_long:
            before = cap
            cap *= 1.0 - half
            fees_paid += before * half
            in_long = False
            equity[i] = cap
            if entry_i is not None:
                trades.append(
                    {
                        "strategy": "C_macro_long_cash",
                        "variant": "p_ge_0.50",
                        "entry_time": dates.iloc[entry_i],
                        "entry_price": entry_px,
                        "exit_time": dates.iloc[i],
                        "exit_price": float(close[i]),
                        "holding_period": f"{int((dates.iloc[i] - dates.iloc[entry_i]).days)}d",
                        "gross_return": float(close[i] / entry_px - 1.0) if entry_px else np.nan,
                        "fee": fee,
                        "net_return": cap / entry_cap - 1.0,
                        "capital_before": entry_cap,
                        "capital_after": cap,
                        "entry_reason": f"P_macro>={P_THR:.2f} (BTC 12w > 0)",
                        "mae": np.nan,
                        "mfe": np.nan,
                    }
                )
            entry_i = entry_px = entry_cap = None
        pos_eod[i] = 1.0 if in_long else 0.0
    if in_long:
        before = cap
        cap *= 1.0 - half
        fees_paid += before * half
        equity[-1] = cap
        if entry_i is not None:
            trades.append(
                {
                    "strategy": "C_macro_long_cash",
                    "variant": "p_ge_0.50",
                    "entry_time": dates.iloc[entry_i],
                    "entry_price": entry_px,
                    "exit_time": dates.iloc[n - 1],
                    "exit_price": float(close[-1]),
                    "holding_period": f"{int((dates.iloc[n - 1] - dates.iloc[entry_i]).days)}d",
                    "gross_return": float(close[-1] / entry_px - 1.0) if entry_px else np.nan,
                    "fee": fee,
                    "net_return": cap / entry_cap - 1.0,
                    "capital_before": entry_cap,
                    "capital_after": cap,
                    "entry_reason": f"P_macro>={P_THR:.2f} (BTC 12w > 0); end-of-sample exit",
                    "mae": np.nan,
                    "mfe": np.nan,
                }
            )
        in_long = False
        pos_eod[-1] = 0.0
    eq = pd.Series(equity, index=pd.DatetimeIndex(dates), dtype=float)
    tr = pd.DataFrame(trades)
    exposure = float(np.mean(pos_eod))
    r = pd.Series(close, index=dates).pct_change()
    long_mask = pos_ret >= 0.5
    cash_mask = pos_ret < 0.5
    def compound(mask):
        rr = r.loc[mask]
        rr = rr.replace([np.inf, -np.inf], np.nan).dropna()
        if rr.empty:
            return np.nan
        return float(np.prod(1.0 + rr.to_numpy()) - 1.0)
    extra = {
        "time_invested": float(np.mean(long_mask)) if n else np.nan,
        "time_in_cash": float(np.mean(cash_mask)) if n else np.nan,
        "btc_return_while_long": compound(long_mask),
        "btc_return_while_cash": compound(cash_mask),
    }
    return eq, tr, fees_paid, exposure, extra


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------


def pick(rows: list[dict], **kwargs) -> dict | None:
    for r in rows:
        if all(r.get(k) == v for k, v in kwargs.items()):
            return r
    return None


def classify(row: dict | None, extra: dict | None = None) -> str:
    extra = extra or {}
    if row is None or not np.isfinite(row.get("ending_capital", np.nan)):
        return "NOT TRADEABLE"
    end_s = float(row["ending_capital"])
    end_b = row.get("benchmark_ending_capital")
    n = int(row.get("n_trades") or 0)
    avg = row.get("avg_trade")
    sharpe = row.get("sharpe")
    temporal_ok = extra.get("temporal_ok")
    n_pos_years = extra.get("n_pos_years")
    beat_bh = np.isfinite(end_s) and np.isfinite(end_b) and end_s > end_b
    pos_exp = np.isfinite(avg) and avg > 0 and n > 0
    pos_wealth = end_s > START_CAP
    robust_years = n_pos_years is None or n_pos_years >= 2

    if extra.get("force_small_n") and n < 5:
        return "INTERESTING BUT WEAK" if pos_exp else "NOT TRADEABLE"
    if temporal_ok is False:
        return "INTERESTING BUT WEAK" if pos_exp else "NOT TRADEABLE"
    # Cash-heavy rules can show milder DD without an economic edge vs Buy & Hold.
    if pos_exp and pos_wealth and beat_bh and robust_years and n >= 5 and np.isfinite(sharpe) and sharpe > 0:
        return "TRADEABLE CANDIDATE"
    if not pos_wealth:
        return "NOT TRADEABLE"
    if pos_exp:
        return "INTERESTING BUT WEAK"
    return "NOT TRADEABLE"


def md_table(headers, rows) -> str:
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join(["---"] * len(headers)) + "|"]
    for r in rows:
        lines.append("| " + " | ".join(str(x) for x in r) + " |")
    return "\n".join(lines)


def write_report(ctx: dict) -> None:
    rows = ctx["summary"]
    years = ctx["years"]
    a_sel = ctx["a_selected"]
    b_sig = ctx["b_signals"]
    c_extra = ctx["c_extra"]
    a_disc = ctx["a_discovery"]

    def rget(strategy, variant, period, fee_bps=10.0):
        return pick(rows, strategy=strategy, variant=variant, period=period, fee_bps_roundtrip=fee_bps)

    a_full = rget("A_session", a_sel, "full")
    a_disco = rget("A_session", a_sel, "discovery")
    a_temp = rget("A_session", a_sel, "temporal_robustness")
    a_full_0 = rget("A_session", a_sel, "full", 0.0)
    a_full_20 = rget("A_session", a_sel, "full", 20.0)
    c_full = rget("C_macro_long_cash", "p_ge_0.50", "full")
    c_0 = rget("C_macro_long_cash", "p_ge_0.50", "full", 0.0)
    c_20 = rget("C_macro_long_cash", "p_ge_0.50", "full", 20.0)

    b_rows = [rget("B_capitulation_deleveraging", f"hold_{h}d", "full") for h in B_HORIZONS]
    b_best = None
    for br in b_rows:
        if br is None:
            continue
        if b_best is None:
            b_best = br
            continue
        s0, s1 = b_best.get("sharpe"), br.get("sharpe")
        if np.isfinite(s1) and (not np.isfinite(s0) or s1 > s0):
            b_best = br
        elif (not np.isfinite(s1) or not np.isfinite(s0)) and (br.get("ending_capital") or -1) > (
            b_best.get("ending_capital") or -1
        ):
            b_best = br

    a_years = [y for y in years if y["strategy"] == "A_session" and y["variant"] == a_sel and y["fee_bps_roundtrip"] == 10.0]
    n_pos_a = sum(1 for y in a_years if np.isfinite(y.get("annual_return")) and y["annual_return"] > 0)
    temporal_ok = bool(a_temp and np.isfinite(a_temp.get("avg_trade")) and a_temp["avg_trade"] > 0)
    v_a = classify(a_full, {"temporal_ok": temporal_ok, "n_pos_years": n_pos_a})
    v_c = classify(
        c_full,
        {
            "n_pos_years": sum(
                1
                for y in years
                if y["strategy"] == "C_macro_long_cash" and y["fee_bps_roundtrip"] == 10.0 and y.get("annual_return", 0) > 0
            )
        },
    )
    v_b = {}
    for br in b_rows:
        if br is None:
            continue
        v_b[br["variant"]] = classify(br, {"force_small_n": True, "n_pos_years": None})

    lead = []
    if a_full:
        lead.append(
            [
                f"A {a_sel}",
                fmt_usd(a_full["ending_capital"]),
                fmt_usd(a_full["benchmark_ending_capital"]),
                fmt_pct(a_full["cagr"]),
                fmt_pct(a_full["max_drawdown"]),
                fmt_num(a_full["sharpe"], 2),
                a_full["n_trades"],
                v_a,
            ]
        )
    for br in b_rows:
        if br is None:
            continue
        lead.append(
            [
                f"B {br['variant']}",
                fmt_usd(br["ending_capital"]),
                fmt_usd(br["benchmark_ending_capital"]),
                fmt_pct(br["cagr"]),
                fmt_pct(br["max_drawdown"]),
                fmt_num(br["sharpe"], 2),
                br["n_trades"],
                v_b.get(br["variant"], ""),
            ]
        )
    if c_full:
        lead.append(
            [
                "C macro LONG/CASH",
                fmt_usd(c_full["ending_capital"]),
                fmt_usd(c_full["benchmark_ending_capital"]),
                fmt_pct(c_full["cagr"]),
                fmt_pct(c_full["max_drawdown"]),
                fmt_num(c_full["sharpe"], 2),
                c_full["n_trades"],
                v_c,
            ]
        )

    primaries = [x for x in [a_full, c_full, *(b_rows or [])] if x]
    best_sharpe = max(
        (r for r in primaries if np.isfinite(r.get("sharpe", np.nan))),
        key=lambda r: r["sharpe"],
        default=None,
    )
    best_wealth = max(
        (r for r in primaries if np.isfinite(r.get("ending_capital", np.nan))),
        key=lambda r: r["ending_capital"],
        default=None,
    )

    def fee_killed(row0, row10) -> bool:
        if row0 is None or row10 is None:
            return False
        return (row0.get("avg_trade") or 0) > 0 and (row10.get("avg_trade") or 0) <= 0

    lines = []
    a = lines.append
    a("# Simple strategy discovery")
    a("")
    a("Executable test of three frozen BTC ideas. Historical backtest / temporal robustness.")
    a("**Not clean OOS.** 2024–2026 has already been inspected in this project. Not a live system.")
    a("")
    a("Primary cost: **10 bps round trip** per completed trade. Start `$10,000`. Long only. Cash earns 0.")
    a("")
    a("## Lead table (10 bps round trip)")
    a("")
    a(
        md_table(
            ["STRATEGY", "ENDING $ FROM $10K", "BUY&HOLD $", "CAGR", "MAX DD", "SHARPE", "TRADES", "VERDICT"],
            lead,
        )
    )
    a("")
    a("Buy & Hold is computed over the **same dates** as that row. Do not compare ending wealth across rows with different date ranges.")
    a("")
    a("## Answers")
    a("")
    a("### 1. Did any session anomaly produce economically meaningful returns?")
    a("")
    if a_full:
        a(
            f"Selected window `{a_sel}` on the full available 1h sample: "
            f"{fmt_usd(START_CAP)} → {fmt_usd(a_full['ending_capital'])} "
            f"(CAGR {fmt_pct(a_full['cagr'])}, Sharpe {fmt_num(a_full['sharpe'], 2)}, "
            f"avg trade {fmt_pct(a_full['avg_trade'], 3)}, n={a_full['n_trades']}) vs "
            f"Buy & Hold {fmt_usd(a_full['benchmark_ending_capital'])}. "
        )
        if a_full["ending_capital"] > a_full.get("benchmark_ending_capital", 0) and (a_full.get("avg_trade") or 0) > 0:
            a("After 10 bps it still compounded, but compare exposure (4h/day) and the temporal split below before calling it meaningful.")
        elif (a_full.get("avg_trade") or 0) > 0:
            a("Average trade was positive after 10 bps, but ending wealth did not beat fully invested Buy & Hold on the same dates.")
        else:
            a("After 10 bps round trip the selected session did **not** produce a positive average trade. A 4-hour window cannot absorb 10 bps/day unless the raw move is large.")
    a("")
    a("### 2. Did it survive the later temporal period?")
    a("")
    if a_disco and a_temp:
        a(
            f"Discovery (first 70% of complete-window dates): ending {fmt_usd(a_disco['ending_capital'])}, "
            f"Sharpe {fmt_num(a_disco['sharpe'], 2)}, avg trade {fmt_pct(a_disco['avg_trade'], 3)}."
        )
        a(
            f"Temporal robustness (last 30%): ending {fmt_usd(a_temp['ending_capital'])}, "
            f"Sharpe {fmt_num(a_temp['sharpe'], 2)}, avg trade {fmt_pct(a_temp['avg_trade'], 3)}, "
            f"vs Buy & Hold {fmt_usd(a_temp['benchmark_ending_capital'])}."
        )
        if temporal_ok:
            a("The frozen window still had positive expectancy on later dates. This is temporal robustness, not clean OOS.")
        else:
            a("The frozen window did **not** keep a positive average trade on later dates. The discovery ranking did not survive.")
    a("")
    a("### 3. Which fixed UTC window was selected in discovery?")
    a("")
    a(f"**`{a_sel}`**")
    a("")
    a("Ranking rule, frozen before looking at the last 30%: highest Sharpe at 10 bps on discovery dates that have all six windows. Tie-break: total return, then average trade. No hour-grid search.")
    a("")
    a("Discovery (10 bps), all six windows:")
    a("")
    disc_tbl = []
    for w in a_disc:
        mark = " ← SELECTED" if w["variant"] == a_sel else ""
        disc_tbl.append(
            [
                w["variant"] + mark,
                fmt_usd(w["ending_capital"]),
                fmt_pct(w["cagr"]),
                fmt_num(w["sharpe"], 2),
                fmt_pct(w["avg_trade"], 3),
                w["n_trades"],
            ]
        )
    a(md_table(["WINDOW", "ENDING $", "CAGR", "SHARPE", "AVG TRADE", "N"], disc_tbl))
    a("")
    a("The selected window was **not** changed after seeing the later period.")
    a("")
    a("### 4. Did capitulation + deleveraging produce profitable trades?")
    a("")
    taken = b_sig.loc[b_sig["taken"]] if len(b_sig) else pd.DataFrame()
    raw_n = int(b_sig["raw_signal"].sum()) if len(b_sig) else 0
    ign_n = int(b_sig["ignored_overlap"].sum()) if len(b_sig) else 0
    a(f"Raw signals (all three filters): **{raw_n}**. Taken under no-overlap (3d variant may differ by horizon): ignored overlapping prints: {ign_n}.")
    a("")
    if raw_n == 0:
        a("No historical dates satisfied the frozen triple filter. Small N is a result. Thresholds were not loosened.")
    else:
        a("Signal dates (raw):")
        a("")
        a("| date | ret_1d | oi_change_1d | perp_volume_rel_30d | taken_any_horizon |")
        a("|---|---:|---:|---:|---|")
        show = b_sig.loc[b_sig["raw_signal"]].copy()
        for _, r in show.iterrows():
            a(
                f"| {pd.Timestamp(r['date']).date()} | {fmt_pct(r['ret_1d'])} | "
                f"{fmt_pct(r['oi_change_1d'])} | {fmt_num(r['perp_volume_rel_30d'], 2)} | "
                f"{'yes' if r['taken'] or r['ignored_overlap'] else 'no'} |"
            )
        a("")
        a("Independent holding-period results at 10 bps (no silent selection):")
        a("")
        bt = []
        for br in b_rows:
            if br is None:
                continue
            bt.append(
                [
                    br["variant"],
                    fmt_usd(br["ending_capital"]),
                    fmt_usd(br["benchmark_ending_capital"]),
                    fmt_pct(br["cagr"]),
                    fmt_pct(br["avg_trade"]),
                    fmt_pct(br.get("avg_mae", np.nan)),
                    fmt_pct(br.get("avg_mfe", np.nan)),
                    br["n_trades"],
                    v_b.get(br["variant"], ""),
                ]
            )
        a(md_table(["HOLD", "END $", "BH $", "CAGR", "AVG TRADE", "AVG MAE", "AVG MFE", "N", "VERDICT"], bt))
        a("")
        a("None of the B variants beat Buy & Hold ending wealth. Milder max DD is mostly non-participation (low exposure), not a superior invested path.")
    a("")
    a("### 5. Which predefined holding horizon looked strongest?")
    a("")
    if b_best:
        a(
            f"Among the five frozen horizons, **{b_best['variant']}** had the highest Sharpe "
            f"({fmt_num(b_best['sharpe'], 2)}; ending {fmt_usd(b_best['ending_capital'])}; "
            f"n={b_best['n_trades']}). This is a diagnostic ranking, not an optimized holding period."
        )
    else:
        a("No completed B trades.")
    a("")
    a("### 6. Was that result supported by enough trades to be credible?")
    a("")
    if b_best:
        n = int(b_best["n_trades"])
        if n < 5:
            a(f"No. N={n} is too small for a trading rule. Small N is the result; the filter was not loosened.")
        elif n < 20:
            a(f"Weakly. N={n} is still a small event sample. Treat expectancy as fragile.")
        else:
            a(f"N={n} is large enough for a first-pass historical claim, still not a prospective proof.")
    a("")
    a("### 7. Did macro LONG/CASH beat BTC Buy & Hold?")
    a("")
    if c_full:
        beat = c_full["ending_capital"] > c_full.get("benchmark_ending_capital", np.inf)
        a(
            f"{fmt_usd(START_CAP)} → {fmt_usd(c_full['ending_capital'])} strategy vs "
            f"{fmt_usd(c_full['benchmark_ending_capital'])} Buy & Hold on the same dates "
            f"(CAGR {fmt_pct(c_full['cagr'])} vs {fmt_pct(c_full['benchmark_cagr'])}). "
            f"{'Yes, higher ending wealth.' if beat else 'No, Buy & Hold ended higher.'}"
        )
    a("")
    a("### 8. Did macro timing materially reduce drawdown?")
    a("")
    if c_full:
        ds, db = c_full.get("max_drawdown"), c_full.get("benchmark_max_drawdown")
        a(f"Strategy max DD {fmt_pct(ds)} vs Buy & Hold {fmt_pct(db)}.")
        if np.isfinite(ds) and np.isfinite(db) and ds > db + 0.05:
            a("Yes: peak-to-trough loss was materially smaller (less negative).")
        elif np.isfinite(ds) and np.isfinite(db) and ds > db:
            a("Slightly smaller drawdown, not a large economic change.")
        else:
            a("No material drawdown reduction.")
    if c_extra:
        a("")
        a(
            f"Time invested {fmt_pct(c_extra.get('time_invested'))}; time in cash {fmt_pct(c_extra.get('time_in_cash'))}. "
            f"BTC return while strategy LONG {fmt_pct(c_extra.get('btc_return_while_long'))}; "
            f"BTC return while strategy CASH {fmt_pct(c_extra.get('btc_return_while_cash'))}."
        )
        bl, bc = c_extra.get("btc_return_while_long"), c_extra.get("btc_return_while_cash")
        if np.isfinite(bl) and np.isfinite(bc) and bl > bc:
            a("Macro state separated environments in the intended direction (BTC did better while LONG than while CASH).")
        elif np.isfinite(bl) and np.isfinite(bc):
            a("Separation is weak or backwards: BTC was not clearly better in the LONG state than in CASH.")
    a("")
    a("### 9. Which strategy had the best risk-adjusted return?")
    a("")
    if best_sharpe:
        a(
            f"**{best_sharpe['strategy']} / {best_sharpe['variant']}** "
            f"(Sharpe {fmt_num(best_sharpe['sharpe'], 2)}, 10 bps, full comparable row)."
        )
    a("")
    a("### 10. Which strategy produced the highest ending wealth from $10,000?")
    a("")
    if best_wealth:
        a(
            f"**{best_wealth['strategy']} / {best_wealth['variant']}** "
            f"ended at {fmt_usd(best_wealth['ending_capital'])} on its own date range. "
            "This is not a cross-range ranking; Buy & Hold on that same range is the fair comparator."
        )
    a("")
    a("### 11. Which effects disappeared after fees?")
    a("")
    killed = []
    if fee_killed(a_full_0, a_full):
        killed.append(f"A `{a_sel}` (positive at 0 bps, non-positive average trade at 10 bps)")
    for h in B_HORIZONS:
        r0 = rget("B_capitulation_deleveraging", f"hold_{h}d", "full", 0.0)
        r10 = rget("B_capitulation_deleveraging", f"hold_{h}d", "full", 10.0)
        if fee_killed(r0, r10):
            killed.append(f"B hold_{h}d")
    if fee_killed(c_0, c_full):
        killed.append("C macro LONG/CASH")
    if killed:
        a("Edge flipped from positive expectancy to non-positive after 10 bps: " + "; ".join(killed) + ".")
    else:
        a("No primary variant flipped from positive average trade at 0 bps to non-positive at 10 bps.")
    if a_full_0 and a_full:
        a(
            f"A `{a_sel}` full sample: 0 bps ending {fmt_usd(a_full_0['ending_capital'])} "
            f"(avg trade {fmt_pct(a_full_0['avg_trade'], 3)}) vs 10 bps {fmt_usd(a_full['ending_capital'])} "
            f"(avg {fmt_pct(a_full['avg_trade'], 3)}) vs 20 bps {fmt_usd(a_full_20['ending_capital']) if a_full_20 else 'NA'}."
        )
    a("Daily session trading pays the round-trip every day; that is the economically relevant stress.")
    a("")
    a("### 12. Classification")
    a("")
    a("| strategy | verdict |")
    a("|---|---|")
    a(f"| A session `{a_sel}` | {v_a} |")
    for br in b_rows:
        if br:
            a(f"| B {br['variant']} | {v_b.get(br['variant'])} |")
    a(f"| C macro LONG/CASH | {v_c} |")
    a("")
    a("Rules used here (not tuned on the fly): TRADEABLE CANDIDATE requires positive average trade after 10 bps, ending wealth above $10,000, Sharpe > 0, at least 5 trades, and ending wealth above Buy & Hold on the same dates. Milder drawdown from sitting in cash is not enough. B with N<5 cannot be TRADEABLE CANDIDATE. Win rate alone is ignored. Focus is expectancy, compounding, drawdown, robustness, fees.")
    a("")
    a("### 13. Which ONE strategy deserves the next validation phase?")
    a("")
    cand = [(v_a, "A_session", a_sel, a_full)]
    if b_best:
        cand.append((v_b.get(b_best["variant"], "NOT TRADEABLE"), "B_capitulation_deleveraging", b_best["variant"], b_best))
    cand.append((v_c, "C_macro_long_cash", "p_ge_0.50", c_full))
    rank = {"TRADEABLE CANDIDATE": 2, "INTERESTING BUT WEAK": 1, "NOT TRADEABLE": 0}
    cand = [c for c in cand if c[3] is not None]
    cand.sort(key=lambda x: (rank.get(x[0], 0), x[3].get("sharpe") or -999), reverse=True)
    if cand and rank.get(cand[0][0], 0) > 0:
        a(f"**{cand[0][1]} / {cand[0][2]}** ({cand[0][0]}). Next phase should freeze this rule and stress it (costs, year splits, implementation delays) — still not a clean OOS claim for 2024–2026.")
    else:
        a("**None.** All three failed the economic bar after costs or lacked enough trades. Do not promote a weak rule. The next useful step is a new frozen hypothesis, not a retune of these thresholds.")
    a("")
    a("## Method notes")
    a("")
    a("- Strategy A: Binance BTCUSDT spot 1h. Return = close of last hour in the UTC window / open of first hour − 1. Buy window open, sell window end, cash otherwise. Incomplete last UTC day dropped.")
    a("- Discovery = first 70% of dates with all six windows complete. Temporal robustness = remaining 30%. Full-history numbers for the selected window are descriptive.")
    a("- Strategy B: expanding 5th percentile of BTC 1d return uses s < t, min 365, same splice as Phase 1. `oi_change_1d` and `perp_volume_rel_30d` from the Phase 3B daily panel. Entry at close t; exit at close t+H. Ignore new signals until exit. MAE/MFE from UTC daily high/low after entry (1h aggregation).")
    a("- Strategy C: features `DXY_CHG_12W`, `US2Y_CHG_12W`, `REAL10Y_CHG_12W`, `NASDAQ_RET_12W` unchanged. Expanding walk-forward logistic L2 C=1.0, train-only median + scaler, min train 100, mature labels s ≤ t−12. Target = BTC Friday-to-Friday 12-week return > 0. Threshold 0.50 is frozen. Rebalance Fridays only. Same model class as `MACRO_BASE_CANDIDATE_V1`; the original observatory scored crypto-market return, this lab applies the model to the BTC vehicle.")
    a("- Fees: 10 bps round trip = 5 bps at entry and 5 bps at exit for multi-day trades; all 10 bps on same-day session round trips. Sensitivity at 0 and 20 bps. No slippage beyond that.")
    a("- Sharpe / vol use daily equity returns × √365. Cash days are zeros.")
    a("- Overlapping B signals: ignored until the current hold ends. Documented in `data/processed/strategy_b_signals.csv`.")
    a("")
    a("## Calendar years (10 bps; partial years kept)")
    a("")
    ytbl = []
    for y in years:
        if y["fee_bps_roundtrip"] != 10.0:
            continue
        ytbl.append(
            [
                y["strategy"],
                y["variant"],
                y["period"],
                fmt_pct(y.get("annual_return")),
                y.get("n_trades"),
                fmt_pct(y.get("win_rate")),
                fmt_pct(y.get("max_drawdown")),
            ]
        )
    a(md_table(["STRATEGY", "VARIANT", "PERIOD", "RETURN", "TRADES", "WIN RATE", "MAX DD"], ytbl))
    a("")
    a("Win rate in the year table is by **entry year**. A multi-week hold can lose inside a calendar year and still be a winning completed trade, or the reverse.")
    a("")
    a("Bad years are not removed.")
    a("")
    RESULTS.joinpath("SIMPLE_STRATEGY_DISCOVERY.md").write_text("\n".join(lines) + "\n")
    log(f"wrote {RESULTS / 'SIMPLE_STRATEGY_DISCOVERY.md'}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    PROCESSED.mkdir(parents=True, exist_ok=True)

    h1 = load_hourly()
    daily = load_daily()
    ohlc = daily_ohlc_from_hourly(h1)
    deriv = load_derivatives()
    last_fri = pd.Timestamp(daily["date"].max())
    while last_fri.weekday() != 4:
        last_fri -= pd.Timedelta(days=1)
    macro = load_macro(last_fri)

    log("Strategy A session panel")
    panel = session_panel(h1)
    panel.to_csv(PROCESSED / "session_window_returns.csv", index=False)
    complete = panel.loc[panel["all_six"]].sort_values("date")
    dates_all = pd.DatetimeIndex(complete["date"])
    cut = int(len(dates_all) * 0.70)
    disc_dates = dates_all[:cut]
    temp_dates = dates_all[cut:]
    log(f"A split discovery {disc_dates.min().date()}→{disc_dates.max().date()} n={len(disc_dates)}")
    log(f"A split temporal  {temp_dates.min().date()}→{temp_dates.max().date()} n={len(temp_dates)}")

    a_disc_rows = []
    disc_sharpes = []
    for *_, name in WINDOWS:
        eq, tr, fees, exp = backtest_session(panel, name, disc_dates, FEE_PRIMARY)
        bh = buy_hold_equity(daily, eq.index.min(), eq.index.max())
        rec = summary_row("A_session", name, "discovery", FEE_PRIMARY, eq, tr, bh, exp, fees)
        a_disc_rows.append(rec)
        sh = rec["sharpe"] if np.isfinite(rec["sharpe"]) else -1e9
        tot = rec["total_return"] if np.isfinite(rec.get("total_return", np.nan)) else -1e9
        avg = rec["avg_trade"] if np.isfinite(rec.get("avg_trade", np.nan)) else -1e9
        disc_sharpes.append((sh, tot, avg, name))
    disc_sharpes.sort(reverse=True)
    a_selected = disc_sharpes[0][3]
    log(f"A SELECTED window (discovery Sharpe @ 10bps): {a_selected}")

    summary = []
    trades_all = []
    years = []
    equity_map = {}

    summary.extend(a_disc_rows)
    periods_a = [("discovery", disc_dates), ("temporal_robustness", temp_dates), ("full", dates_all)]
    for fee in FEE_SET:
        for period, dts in periods_a:
            if fee == FEE_PRIMARY and period == "discovery":
                continue
            eq, tr, fees, exp = backtest_session(panel, a_selected, dts, fee)
            bh = buy_hold_equity(daily, eq.index.min(), eq.index.max())
            rec = summary_row("A_session", a_selected, period, fee, eq, tr, bh, exp, fees)
            summary.append(rec)
            if period == "full" and fee == FEE_PRIMARY:
                years.extend(year_rows("A_session", a_selected, fee, eq, tr))
                trades_all.append(tr)
                equity_map["strategy_a"] = eq
                equity_map["buy_hold_a"] = bh

    log("Strategy B")
    bdf = build_b_signals(daily, deriv)
    raw_sig = bdf.loc[bdf["raw_signal"], ["date", "close", "ret_1d", "oi_change_1d", "perp_volume_rel_30d"]].copy()
    raw_sig["raw_signal"] = True
    sig_store = bdf[["date", "close", "ret_1d", "oi_change_1d", "perp_volume_rel_30d", "raw_signal"]].copy()
    sig_store["taken"] = False
    sig_store["ignored_overlap"] = False
    for h in B_HORIZONS:
        for fee in FEE_SET:
            eq, tr, fees, exp, sig = backtest_b(bdf, ohlc, h, fee)
            if eq.empty:
                continue
            if fee == FEE_PRIMARY and h == B_HORIZONS[0]:
                sig_store = sig
            bh = buy_hold_equity(daily, eq.index.min(), eq.index.max())
            extra = {}
            if len(tr):
                extra["avg_mae"] = float(pd.to_numeric(tr["mae"], errors="coerce").mean())
                extra["avg_mfe"] = float(pd.to_numeric(tr["mfe"], errors="coerce").mean())
                extra["holding_period"] = f"{h}d"
            rec = summary_row("B_capitulation_deleveraging", f"hold_{h}d", "full", fee, eq, tr, bh, exp, fees, extra)
            summary.append(rec)
            if fee == FEE_PRIMARY:
                years.extend(year_rows("B_capitulation_deleveraging", f"hold_{h}d", fee, eq, tr))
                trades_all.append(tr)
                equity_map[f"strategy_b_{h}d"] = eq
                if h == B_HORIZONS[0]:
                    equity_map["buy_hold_b"] = bh
    sig_store.to_csv(PROCESSED / "strategy_b_signals.csv", index=False)
    if len(raw_sig):
        log("B raw signal dates: " + ", ".join(pd.to_datetime(raw_sig["date"]).dt.date.astype(str)))

    log("Strategy C")
    fri = daily.loc[daily["date"].dt.weekday == 4, ["date", "close"]].rename(
        columns={"date": "week", "close": "btc_close"}
    )
    weekly = macro.merge(fri, on="week", how="inner").sort_values("week").reset_index(drop=True)
    wf = macro_walkforward(weekly)
    wf.to_csv(PROCESSED / "macro_walkforward_btc12w.csv", index=False)
    c_extra = {}
    for fee in FEE_SET:
        eq, tr, fees, exp, extra = backtest_c(daily, wf, fee)
        if eq.empty:
            continue
        bh = buy_hold_equity(daily, eq.index.min(), eq.index.max())
        rec = summary_row("C_macro_long_cash", "p_ge_0.50", "full", fee, eq, tr, bh, exp, fees, extra)
        summary.append(rec)
        if fee == FEE_PRIMARY:
            years.extend(year_rows("C_macro_long_cash", "p_ge_0.50", fee, eq, tr))
            trades_all.append(tr)
            equity_map["strategy_c"] = eq
            equity_map["buy_hold_c"] = bh
            c_extra = extra

    # Equity curves
    all_dates = pd.DatetimeIndex(sorted(daily["date"].unique()))
    eq_df = pd.DataFrame({"date": all_dates})
    colmap = {
        "buy_hold_a": "buy_hold_a",
        "strategy_a": "strategy_a",
        "buy_hold_b": "buy_hold_b",
        "strategy_b_3d": "strategy_b_3d",
        "strategy_b_7d": "strategy_b_7d",
        "strategy_b_14d": "strategy_b_14d",
        "strategy_b_30d": "strategy_b_30d",
        "strategy_b_60d": "strategy_b_60d",
        "buy_hold_c": "buy_hold_c",
        "strategy_c": "strategy_c",
    }
    for src, col in colmap.items():
        if src in equity_map:
            s = equity_map[src]
            eq_df[col] = eq_df["date"].map(s)
        else:
            eq_df[col] = np.nan
    eq_df.to_csv(RESULTS / "EQUITY_CURVES.csv", index=False)

    tlog = pd.concat([t for t in trades_all if t is not None and len(t)], ignore_index=True) if trades_all else pd.DataFrame()
    if len(tlog):
        cols = [
            "strategy",
            "variant",
            "entry_time",
            "entry_price",
            "exit_time",
            "exit_price",
            "holding_period",
            "gross_return",
            "fee",
            "net_return",
            "capital_before",
            "capital_after",
            "entry_reason",
            "mae",
            "mfe",
        ]
        for c in cols:
            if c not in tlog.columns:
                tlog[c] = np.nan
        tlog = tlog[cols]
    tlog.to_csv(RESULTS / "TRADE_LOG.csv", index=False)

    sum_df = pd.DataFrame(summary)
    pref = [
        "strategy",
        "variant",
        "period",
        "start_date",
        "end_date",
        "fee_bps_roundtrip",
        "starting_capital",
        "ending_capital",
        "total_return",
        "cagr",
        "annualized_volatility",
        "sharpe",
        "max_drawdown",
        "calmar",
        "n_trades",
        "win_rate",
        "avg_trade",
        "median_trade",
        "avg_winner",
        "avg_loser",
        "payoff_ratio",
        "profit_factor",
        "exposure",
        "turnover",
        "fees_paid",
        "benchmark_ending_capital",
        "benchmark_cagr",
        "benchmark_max_drawdown",
        "avg_mae",
        "avg_mfe",
        "holding_period",
        "time_invested",
        "time_in_cash",
        "btc_return_while_long",
        "btc_return_while_cash",
    ]
    for c in pref:
        if c not in sum_df.columns:
            sum_df[c] = np.nan
    sum_df = sum_df[pref]
    sum_df.to_csv(RESULTS / "STRATEGY_SUMMARY.csv", index=False)
    pd.DataFrame(years).to_csv(PROCESSED / "yearly_stats.csv", index=False)

    log(f"wrote {RESULTS / 'STRATEGY_SUMMARY.csv'} rows={len(sum_df)}")
    log(f"wrote {RESULTS / 'TRADE_LOG.csv'} rows={len(tlog)}")
    log(f"wrote {RESULTS / 'EQUITY_CURVES.csv'} rows={len(eq_df)}")

    write_report(
        {
            "summary": summary,
            "years": years,
            "a_selected": a_selected,
            "a_discovery": a_disc_rows,
            "b_signals": sig_store if sig_store is not None else pd.DataFrame(),
            "c_extra": c_extra,
        }
    )


if __name__ == "__main__":
    main()
