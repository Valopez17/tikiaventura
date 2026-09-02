#!/usr/bin/env python3
"""Phase 2: try to break frozen C_macro_long_cash.

No retune. No new features. Not clean OOS.
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
from pandas.tseries.holiday import USFederalHolidayCalendar
from pandas.tseries.offsets import CustomBusinessDay
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

PHASE = Path(__file__).resolve().parents[1]
RESULTS = PHASE / "results"
PHASE1 = PHASE.parent / "phase1_simple_strategy_discovery"
TSR = PHASE.parent.parent
MSO = TSR.parent
REPO = MSO.parent.parent
RQF = MSO / "v1_weekly_core" / "regime_quality_framework"

H1_PATH = REPO / "btc_tsmom_replication" / "btcusdt_1h.csv"
TRUSTED_PRICES = REPO / "btc_tsmom_replication" / "data" / "btcusd_daily.csv"
PHASE1_BN = TSR / "phase1_capitulation_entries" / "data" / "raw" / "binance_btcusdt_1d.csv"
MACRO_FROZEN = RQF / "phase6a_macro_dataset" / "results" / "macro_weekly.csv"
MACRO_CACHE = PHASE1 / "data" / "processed" / "macro_weekly_extended.csv"
PHASE1_WF = PHASE1 / "data" / "processed" / "macro_walkforward_btc12w.csv"
PHASE1_C_END_10BPS = 1_474_845.5740330585

BINANCE_LISTING = date(2017, 8, 17)
FROZEN_MACRO_END = pd.Timestamp("2023-12-29")
MACRO_OOS_START = pd.Timestamp("2024-01-01")
START_CAP = 10_000.0
FEE_SET = (0.0, 0.0010, 0.0020, 0.0050)
MACRO_FEATS = ["DXY_CHG_12W", "US2Y_CHG_12W", "REAL10Y_CHG_12W", "NASDAQ_RET_12W"]
H_MACRO = 12
MIN_TRAIN = 100
LOGIT_C = 1.0
CLIP = 1e-6
P_THR = 0.50
CRYPTO_DAYS = 365.0
H10_BROAD_DOLLAR = "122e3bcb627e8e53f1bf72a1a09cfb81"
H15_TREASURY = "bf17364827e38702b42a58cf8eaa3f78"
UA = "tikiaventura-strategy-lab-phase2/1.0 (academic research)"
MACRO_UA = "Mozilla/5.0 (research; strategy-lab-phase2)"
SSL_CTX = ssl.create_default_context()
US_BDAY = CustomBusinessDay(calendar=USFederalHolidayCalendar())
_HOLIDAYS = None


def us_holidays(start, end):
    global _HOLIDAYS
    if _HOLIDAYS is None:
        _HOLIDAYS = set(
            pd.DatetimeIndex(USFederalHolidayCalendar().holidays(start="2015-01-01", end="2027-01-01")).normalize()
        )
    return _HOLIDAYS

# V1 Saturday 00:00 UTC = Friday 23:59 UTC daily close on a 24/7 UTC bar.
# Delay is measured from that timestamp.
VARIANTS = {
    "V0": {"lag_days": 0, "label": "original_friday_close"},
    "V1": {"lag_days": 0, "label": "saturday_00utc_after_friday_info"},
    "V2": {"lag_days": 1, "label": "v1_plus_24h"},
    "V3": {"lag_days": 3, "label": "v1_plus_72h"},
    "V4": {"lag_days": 0, "label": "one_week_info_lag", "lag_features": True},
}


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


def max_drawdown(equity: np.ndarray) -> float:
    eq = np.asarray(equity, dtype=float)
    eq = eq[np.isfinite(eq)]
    if eq.size == 0:
        return np.nan
    peak = np.maximum.accumulate(eq)
    return float(np.min(eq / peak - 1.0))


def cagr_from(start_cap: float, end_cap: float, days: float) -> float:
    if not np.isfinite(start_cap) or not np.isfinite(end_cap) or start_cap <= 0 or days <= 0:
        return np.nan
    if end_cap <= 0:
        return -1.0
    return float((end_cap / start_cap) ** (CRYPTO_DAYS / days) - 1.0)


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
        "sortino": np.nan,
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
    r = s.pct_change().replace([np.inf, -np.inf], np.nan).dropna()
    if len(r) >= 2 and float(r.std(ddof=1)) > 0:
        rec["annualized_volatility"] = float(r.std(ddof=1) * np.sqrt(CRYPTO_DAYS))
        rec["sharpe"] = float(r.mean() / r.std(ddof=1) * np.sqrt(CRYPTO_DAYS))
        down = r[r < 0]
        if len(down) >= 2 and float(down.std(ddof=1)) > 0:
            rec["sortino"] = float(r.mean() / down.std(ddof=1) * np.sqrt(CRYPTO_DAYS))
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
    return pd.Series(START_CAP * (px / px[0]), index=pd.DatetimeIndex(d["date"]))


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------


def load_daily() -> pd.DataFrame:
    if not TRUSTED_PRICES.exists():
        raise RuntimeError(f"Trusted BTC daily file missing: {TRUSTED_PRICES}")
    if not PHASE1_BN.exists():
        raise RuntimeError(f"Phase 1 Binance daily missing: {PHASE1_BN}")
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
    post = bn.loc[bn["date"].dt.date >= BINANCE_LISTING, ["date", "close"]].copy()
    px = pd.concat([pre, post], ignore_index=True).sort_values("date").drop_duplicates("date")
    end = min(last_complete_utc_day(), px["date"].max().date())
    px = px.loc[px["date"].dt.date <= end].reset_index(drop=True)
    log(f"daily BTC {px['date'].min().date()} → {px['date'].max().date()} n={len(px)}")
    return px


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
    weeks_new = pd.date_range("2024-01-05", last_week, freq="W-FRI")
    start = pd.Timestamp("2023-09-01")
    end = last_week + pd.Timedelta(days=3)
    log("Macro extension H.10 / H.15 / TIPS / Nasdaq")
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
        part = pd.read_csv(io.StringIO(text))
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
    hist = frozen[["week", *MACRO_FEATS]].copy()
    oos = levels.loc[levels["week"] >= MACRO_OOS_START, ["week", *MACRO_FEATS]]
    return pd.concat([hist, oos], ignore_index=True).sort_values("week").reset_index(drop=True)


# ---------------------------------------------------------------------------
# Model (frozen)
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


def macro_walkforward(weekly: pd.DataFrame, lag_features: bool = False) -> pd.DataFrame:
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
    if lag_features:
        X = np.vstack([np.full((1, X.shape[1]), np.nan), X[:-1]])
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
        train &= y_ok & feat_ok
        nt = int(train.sum())
        ntr[t] = nt
        if nt < MIN_TRAIN:
            continue
        p[t] = logit_fit_predict(X[train], y[train], X[t])
    out = df.copy()
    out["fut_12w"] = fut
    out["y_pos_12w"] = y
    out["p_macro"] = p
    out["n_train"] = ntr
    out["long"] = np.where(np.isfinite(p), p >= P_THR, np.nan)
    log(
        f"WF lag_features={lag_features} finite P={int(np.isfinite(p).sum())} "
        f"long={(out['long']==1).sum()} cash={(out['long']==0).sum()}"
    )
    return out


# ---------------------------------------------------------------------------
# Timing
# ---------------------------------------------------------------------------


def ny_hour_utc(day: pd.Timestamp, hour: int) -> pd.Timestamp:
    local = pd.Timestamp(day.date()).tz_localize("America/New_York") + pd.Timedelta(hours=hour)
    return local.tz_convert("UTC").tz_localize(None)


def next_us_business_day(day: pd.Timestamp) -> pd.Timestamp:
    return pd.Timestamp(day + US_BDAY)


def friday_close_utc(friday: pd.Timestamp) -> pd.Timestamp:
    return pd.Timestamp(friday.date()) + pd.Timedelta(hours=23, minutes=59)


def saturday_00_utc(friday: pd.Timestamp) -> pd.Timestamp:
    return pd.Timestamp(friday.date()) + pd.Timedelta(days=1)


def feature_availability(friday: pd.Timestamp, feature: str) -> dict:
    """Conservative availability of the Friday-labeled print."""
    hol = us_holidays(friday - pd.Timedelta(days=10), friday)
    src = friday
    if friday.normalize() in hol or friday.weekday() >= 5:
        src = friday - US_BDAY
    if feature == "NASDAQ_RET_12W":
        avail = ny_hour_utc(src, 16)
        assumption = "Nasdaq Composite cash close 16:00 America/New_York on the source session."
        notes = (
            "Friday close is 20:00 UTC (EDT) or 21:00 UTC (EST). "
            "Known before Friday 23:59 UTC and before Saturday 00:00 UTC."
        )
    elif feature == "US2Y_CHG_12W":
        avail = ny_hour_utc(src, 16)
        assumption = "H.15 2Y CMT: same-business-day afternoon print; conservative 16:00 ET."
        notes = "Phase 6A: released same business day afternoon. Observation date used, not tick timestamp."
    elif feature == "REAL10Y_CHG_12W":
        avail = ny_hour_utc(src, 16)
        assumption = "Treasury TIPS 10Y real par yield: same-business-day; conservative 16:00 ET."
        notes = "Phase 6A: approximately contemporaneous on a business-day Friday. Not a locked vintage."
    elif feature == "DXY_CHG_12W":
        nxt = next_us_business_day(src)
        avail = ny_hour_utc(nxt, 16)
        assumption = (
            "H.10 Nominal Broad Dollar Index: typically same OR next business day. "
            "Availability NOT verified same-day. Conservative: next US business day 16:00 ET."
        )
        notes = (
            "This is Fed trade-weighted broad dollar, not ICE DXY. "
            "Using Friday's H.10 print at Friday 23:59 UTC or Saturday 00:00 UTC is a residual look-ahead risk."
        )
    else:
        raise ValueError(feature)
    return {"source_date": pd.Timestamp(src.date()), "available_ts": avail, "assumption": assumption, "notes": notes}


def build_timing_audit(weeks: pd.DatetimeIndex) -> pd.DataFrame:
    rows = []
    for fri in weeks:
        fri = pd.Timestamp(fri)
        v0_exec = friday_close_utc(fri)
        v1_exec = saturday_00_utc(fri)
        signal_ts = friday_close_utc(fri)
        for feat in MACRO_FEATS:
            info = feature_availability(fri, feat)
            for variant, exec_ts in (("V0", v0_exec), ("V1", v1_exec)):
                rows.append(
                    {
                        "decision_date": fri.date().isoformat(),
                        "variant": variant,
                        "feature": feat,
                        "source_date": info["source_date"].date().isoformat(),
                        "availability_assumption": info["assumption"],
                        "feature_available_ts": info["available_ts"].isoformat(),
                        "signal_timestamp": signal_ts.isoformat(),
                        "btc_execution_timestamp": exec_ts.isoformat(),
                        "safe_at_execution": bool(info["available_ts"] <= exec_ts),
                        "notes": info["notes"],
                    }
                )
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Backtest
# ---------------------------------------------------------------------------


def backtest(daily: pd.DataFrame, weekly: pd.DataFrame, fee: float, lag_days: int):
    """Rebalance at UTC close of (Friday + lag_days). lag_days=0 is Friday close = Sat 00:00 UTC."""
    w = weekly.loc[np.isfinite(weekly["p_macro"])].copy()
    if w.empty:
        return pd.Series(dtype=float), pd.DataFrame(), {}
    fills = {}
    for _, r in w.iterrows():
        fill_d = pd.Timestamp(r["week"]) + pd.Timedelta(days=int(lag_days))
        fills[fill_d.normalize()] = {
            "long": float(r["long"]),
            "p": float(r["p_macro"]),
            "decision": pd.Timestamp(r["week"]),
        }
    start = min(fills)
    d = daily.loc[daily["date"] >= start].copy().reset_index(drop=True)
    close = d["close"].to_numpy(dtype=float)
    dates = d["date"]
    n = len(d)
    half = fee / 2.0
    cap = START_CAP
    equity = np.full(n, np.nan)
    equity[0] = cap
    fees_paid = 0.0
    in_long = False
    entry_i = entry_px = entry_cap = None
    pos_eod = np.zeros(n, dtype=float)
    trades = []
    switches = []
    n_entries = n_exits = 0
    prev_want = None
    for i in range(n):
        if i > 0:
            if in_long and close[i - 1] > 0 and np.isfinite(close[i]) and np.isfinite(close[i - 1]):
                cap *= close[i] / close[i - 1]
            equity[i] = cap
        key = pd.Timestamp(dates.iloc[i]).normalize()
        if key not in fills:
            pos_eod[i] = 1.0 if in_long else 0.0
            continue
        want_long = fills[key]["long"] >= 0.5
        p = fills[key]["p"]
        dec = fills[key]["decision"]
        old_want = False if prev_want is None else prev_want
        if want_long != old_want:
            fut = {}
            px = float(close[i])
            for h, name in ((7, "ret_1w"), (28, "ret_4w"), (84, "ret_12w")):
                j = i + h
                fut[name] = float(close[j] / px - 1.0) if j < n and px > 0 and np.isfinite(close[j]) else np.nan
            exec_ts = friday_close_utc(dec) if lag_days == 0 else (saturday_00_utc(dec) + pd.Timedelta(days=lag_days))
            switches.append(
                {
                    "decision_date": dec.date().isoformat(),
                    "event": "CASH→LONG" if want_long else "LONG→CASH",
                    "probability": p,
                    "execution_timestamp": exec_ts.isoformat(),
                    "btc_execution_price": px,
                    "next_1w_btc_return": fut["ret_1w"],
                    "next_4w_btc_return": fut["ret_4w"],
                    "next_12w_btc_return": fut["ret_12w"],
                }
            )
        if want_long and not in_long:
            before = cap
            cap *= 1.0 - half
            fees_paid += before * half
            in_long = True
            n_entries += 1
            entry_i, entry_px, entry_cap = i, float(close[i]), before
            equity[i] = cap
        elif (not want_long) and in_long:
            before = cap
            cap *= 1.0 - half
            fees_paid += before * half
            in_long = False
            n_exits += 1
            equity[i] = cap
            if entry_i is not None:
                trades.append(
                    {
                        "entry_time": dates.iloc[entry_i],
                        "exit_time": dates.iloc[i],
                        "entry_price": entry_px,
                        "exit_price": float(close[i]),
                        "net_return": cap / entry_cap - 1.0,
                        "capital_before": entry_cap,
                        "capital_after": cap,
                    }
                )
            entry_i = entry_px = entry_cap = None
        prev_want = want_long
        pos_eod[i] = 1.0 if in_long else 0.0
    if in_long:
        before = cap
        cap *= 1.0 - half
        fees_paid += before * half
        n_exits += 1
        equity[-1] = cap
        if entry_i is not None:
            trades.append(
                {
                    "entry_time": dates.iloc[entry_i],
                    "exit_time": dates.iloc[n - 1],
                    "entry_price": entry_px,
                    "exit_price": float(close[-1]),
                    "net_return": cap / entry_cap - 1.0,
                    "capital_before": entry_cap,
                    "capital_after": cap,
                }
            )
        pos_eod[-1] = 0.0
    eq = pd.Series(equity, index=pd.DatetimeIndex(dates), dtype=float)
    extra = {
        "fees_paid": fees_paid,
        "exposure": float(np.mean(pos_eod)) if n else np.nan,
        "n_entries": n_entries,
        "n_exits": n_exits,
        "n_trades": len(trades),
        "switches": switches,
        "pos_eod": pos_eod,
        "dates": dates,
        "close": close,
    }
    return eq, pd.DataFrame(trades), extra


def summary_row(variant: str, fee: float, eq: pd.Series, extra: dict, bh: pd.Series, bh_m: dict) -> dict:
    em = equity_metrics(eq)
    years = np.nan
    if pd.notna(em["start_date"]) and pd.notna(em["end_date"]):
        years = max(float((em["end_date"] - em["start_date"]).days) / CRYPTO_DAYS, 1e-9)
    rec = {
        "variant": variant,
        "variant_label": VARIANTS[variant]["label"],
        "fee_bps_roundtrip": round(fee * 10_000.0, 1),
        "start_date": em["start_date"].date().isoformat() if pd.notna(em["start_date"]) else "",
        "end_date": em["end_date"].date().isoformat() if pd.notna(em["end_date"]) else "",
        "starting_capital": START_CAP,
        "ending_capital": em["ending_capital"],
        "total_return": em["total_return"],
        "cagr": em["cagr"],
        "annualized_volatility": em["annualized_volatility"],
        "sharpe": em["sharpe"],
        "sortino": em["sortino"],
        "max_drawdown": em["max_drawdown"],
        "calmar": em["calmar"],
        "exposure": extra.get("exposure", np.nan),
        "n_entries": extra.get("n_entries", np.nan),
        "n_exits": extra.get("n_exits", np.nan),
        "n_trades": extra.get("n_trades", np.nan),
        "turnover": float(extra.get("n_entries", 0) / years) if np.isfinite(years) else np.nan,
        "fees_paid": extra.get("fees_paid", np.nan),
        "benchmark_ending_capital": bh_m.get("ending_capital", np.nan),
        "benchmark_cagr": bh_m.get("cagr", np.nan),
        "benchmark_sharpe": bh_m.get("sharpe", np.nan),
        "benchmark_max_drawdown": bh_m.get("max_drawdown", np.nan),
        "cagr_minus_bh": (em["cagr"] - bh_m["cagr"]) if np.isfinite(em["cagr"]) and np.isfinite(bh_m.get("cagr", np.nan)) else np.nan,
        "sharpe_minus_bh": (em["sharpe"] - bh_m["sharpe"]) if np.isfinite(em["sharpe"]) and np.isfinite(bh_m.get("sharpe", np.nan)) else np.nan,
        "maxdd_minus_bh": (em["max_drawdown"] - bh_m["max_drawdown"])
        if np.isfinite(em["max_drawdown"]) and np.isfinite(bh_m.get("max_drawdown", np.nan))
        else np.nan,
    }
    return rec


def slice_equity(eq: pd.Series, daily: pd.DataFrame, start, end) -> tuple[pd.Series, pd.Series]:
    s = eq.loc[(eq.index >= start) & (eq.index <= end)].dropna()
    if s.empty:
        return s, pd.Series(dtype=float)
    scaled = START_CAP * (s / float(s.iloc[0]))
    bh = buy_hold_equity(daily, s.index.min(), s.index.max())
    return scaled, bh


def year_block(eq: pd.Series, daily: pd.DataFrame, extra_pos=None) -> list[dict]:
    rows = []
    s = eq.dropna()
    for y in sorted(set(s.index.year)):
        sy = s.loc[s.index.year == y]
        if len(sy) < 2:
            continue
        ret = float(sy.iloc[-1] / sy.iloc[0] - 1.0)
        dd = max_drawdown(sy.to_numpy())
        bh = buy_hold_equity(daily, sy.index.min(), sy.index.max())
        bh_ret = float(bh.iloc[-1] / bh.iloc[0] - 1.0) if len(bh) else np.nan
        exp = np.nan
        if extra_pos is not None:
            dates = extra_pos["dates"]
            pos = extra_pos["pos_eod"]
            mask = pd.to_datetime(dates).dt.year == y
            if mask.any():
                exp = float(np.mean(pos[mask.to_numpy()]))
        rows.append(
            {
                "test_type": "calendar_year",
                "period": str(y),
                "strategy_return": ret,
                "bh_return": bh_ret,
                "excess_return": ret - bh_ret if np.isfinite(bh_ret) else np.nan,
                "strategy_max_dd": dd,
                "exposure": exp,
                "n_days": int(len(sy)),
                "beats_bh": bool(np.isfinite(ret) and np.isfinite(bh_ret) and (ret - bh_ret) > 0.005),
                "strategy_lost_money": bool(ret < 0),
                "meaningful_cash": bool(np.isfinite(exp) and exp < 0.90),
            }
        )
    return rows


def signal_economics(weekly: pd.DataFrame) -> list[dict]:
    w = weekly.loc[np.isfinite(weekly["p_macro"])].copy().sort_values("week").reset_index(drop=True)
    c = pd.to_numeric(w["btc_close"], errors="coerce").to_numpy(dtype=float)
    nxt = np.full(len(w), np.nan)
    for i in range(len(w) - 1):
        if c[i] > 0 and np.isfinite(c[i]) and np.isfinite(c[i + 1]):
            nxt[i] = c[i + 1] / c[i] - 1.0
    w["week_ret"] = nxt
    rows = []
    for state, mask in (("LONG", w["long"] == 1), ("CASH", w["long"] == 0)):
        r = w.loc[mask, "week_ret"].to_numpy(dtype=float)
        r = r[np.isfinite(r)]
        if r.size == 0:
            rows.append({"test_type": "signal_economics", "state": state, "n_weeks": 0})
            continue
        rows.append(
            {
                "test_type": "signal_economics",
                "state": state,
                "n_weeks": int(r.size),
                "mean_weekly_btc_return": float(np.mean(r)),
                "median_weekly_btc_return": float(np.median(r)),
                "cumulative_btc_return": float(np.prod(1.0 + r) - 1.0),
                "weekly_volatility": float(np.std(r, ddof=1)) if r.size > 1 else np.nan,
                "fraction_positive": float(np.mean(r > 0)),
            }
        )
    return rows


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------


def pick(rows, **kw):
    for r in rows:
        if all(r.get(k) == v for k, v in kw.items()):
            return r
    return None


def classify(ctx: dict) -> str:
    """Frozen rules. Do not loosen after seeing results."""
    audit = ctx["audit"]
    v1 = ctx["v1_10"]
    v2 = ctx["v2_10"]
    v3 = ctx["v3_10"]
    v4 = ctx["v4_10"]
    years = ctx["years"]
    blocks = ctx["blocks"]
    ex_best = ctx["ex_best"]
    ex_2017 = ctx["ex_2017"]

    v1_audit = audit.loc[audit["variant"] == "V1"]
    no_lookahead_v1 = bool(v1_audit["safe_at_execution"].all()) if len(v1_audit) else False

    def beats_bh(row) -> bool:
        if row is None:
            return False
        cagr_ok = np.isfinite(row.get("cagr_minus_bh", np.nan)) and row["cagr_minus_bh"] > 0
        sh_ok = np.isfinite(row.get("sharpe_minus_bh", np.nan)) and row["sharpe_minus_bh"] > 0
        return cagr_ok or sh_ok

    v1_beats = beats_bh(v1)
    delay_ok = beats_bh(v2)
    delay_stress = beats_bh(v3)
    lag_ok = beats_bh(v4)
    n_year_beats = sum(1 for y in years if y.get("beats_bh"))
    one_year = False
    if ex_best is not None:
        one_year = not beats_bh(ex_best) and not beats_bh(ex_2017)
    n_block_ok = sum(1 for b in blocks if b.get("beats_bh"))

    if (
        no_lookahead_v1
        and v1_beats
        and delay_ok
        and (not one_year)
        and n_block_ok >= 2
        and n_year_beats >= 3
    ):
        return "PASS"
    if v1_beats and (delay_ok or lag_ok) and n_block_ok >= 1 and not (
        not v1_beats
    ):
        # interesting but timing/delay/year weaken it
        if (not no_lookahead_v1) or (not delay_ok) or (not delay_stress) or one_year or n_block_ok < 2 or (not lag_ok):
            return "PASS WITH LIMITATIONS"
        return "PASS WITH LIMITATIONS"
    return "FAIL"


def write_report(ctx: dict) -> None:
    v0, v1, v2, v3, v4 = ctx["v0_10"], ctx["v1_10"], ctx["v2_10"], ctx["v3_10"], ctx["v4_10"]
    v1_0, v1_20, v1_50 = ctx["v1_0"], ctx["v1_20"], ctx["v1_50"]
    years = ctx["years"]
    blocks = ctx["blocks"]
    econ = ctx["econ"]
    verdict = ctx["verdict"]
    audit = ctx["audit"]
    switches = ctx["switches"]
    best_year = ctx["best_year"]
    ex_best, ex_2017 = ctx["ex_best"], ctx["ex_2017"]
    v1_safe_frac = float(audit.loc[audit["variant"] == "V1", "safe_at_execution"].mean())
    dxy_safe_v1 = bool(
        audit.loc[(audit["variant"] == "V1") & (audit["feature"] == "DXY_CHG_12W"), "safe_at_execution"].all()
    )
    ndq_safe_v1 = bool(
        audit.loc[(audit["variant"] == "V1") & (audit["feature"] == "NASDAQ_RET_12W"), "safe_at_execution"].all()
    )

    def line_result(title, row):
        if row is None:
            return f"{title}: NA"
        return (
            f"{title}: $10,000 → {fmt_usd(row['ending_capital'])}; "
            f"Sharpe {fmt_num(row['sharpe'], 2)}; CAGR {fmt_pct(row['cagr'])}; "
            f"maxDD {fmt_pct(row['max_drawdown'])}; vs BH {fmt_usd(row['benchmark_ending_capital'])} "
            f"(CAGR {fmt_pct(row['benchmark_cagr'])}, Sharpe {fmt_num(row['benchmark_sharpe'], 2)}, "
            f"maxDD {fmt_pct(row['benchmark_max_drawdown'])})"
        )

    long_e = next((e for e in econ if e.get("state") == "LONG"), {})
    cash_e = next((e for e in econ if e.get("state") == "CASH"), {})
    n_beats = sum(1 for y in years if y.get("beats_bh"))
    n_lose = sum(1 for y in years if y.get("strategy_lost_money"))
    n_cash = sum(1 for y in years if y.get("meaningful_cash"))

    lines = []
    a = lines.append
    a("# Macro strategy validation")
    a("")
    a("Frozen Phase 1 candidate `C_macro_long_cash`. **Try to break it.** Historical validation / robustness. **Not clean OOS.** 2024–2026 has already been inspected.")
    a("")
    a("Primary cost shown below: **10 bps round trip**. Start `$10,000`. Long only. Cash = 0.")
    a("")
    a("## ORIGINAL RESULT")
    a("")
    a(line_result("V0 Phase 1 reconstruction (Friday UTC close)", v0))
    a("")
    a("## REALISTIC RESULT")
    a("")
    a(line_result("V1 timing-safe Saturday 00:00 UTC", v1))
    a(line_result("V2 24h delay", v2))
    a(line_result("V3 72h delay", v3))
    a(line_result("V4 one-week information lag", v4))
    a("")
    a("V3/V4 can print *higher* ending wealth than V1. That is not a reason to prefer delay or lagged features. V2–V4 have different start dates (Buy & Hold is restated on each row). V4 also uses a different information set. Full-sample ranking stays with the frozen V1 rule.")
    a("")
    a("## Answers")
    a("")
    a("### 1. Was there any timestamp look-ahead in the original backtest?")
    a("")
    a("Phase 1 executed at **Friday UTC daily close** (23:59 UTC). Nasdaq Friday cash close is 16:00 America/New_York (20:00 or 21:00 UTC), so **NASDAQ_RET_12W is available before that fill**. H.15 2Y and Treasury TIPS 10Y real are same-business-day afternoon prints; conservative 16:00 ET is also before Friday 23:59 UTC.")
    a("")
    a("**DXY_CHG_12W is the residual look-ahead.** It is the Fed H.10 Nominal Broad Dollar Index, typically published the same **or next** business day. Same-day availability was never verified. Using Friday's H.10 print at Friday 23:59 UTC can be look-ahead. Revised (not vintage) history remains for all four series.")
    a("")
    a(f"V1 `safe_at_execution` share across decision×feature rows: {fmt_pct(v1_safe_frac)}. Nasdaq V1 safe={ndq_safe_v1}. DXY V1 safe={dxy_safe_v1}.")
    a("")
    a("### 2. What is the earliest genuinely executable weekly timestamp?")
    a("")
    a("**Saturday 00:00 UTC** after the Friday US cash close, for Nasdaq / US2Y / REAL10Y. That is V1.")
    a("")
    a("For an **unquestionable** information set including H.10, wait until the next US business day's H.10 print (often Monday), or drop current-Friday macro entirely (V4). This file treats V1 as the primary realistic implementation and V4 as the conservative information-set stress.")
    a("")
    a("### 3. Does the strategy still beat Buy & Hold using that timestamp?")
    a("")
    if v1:
        beat = v1["ending_capital"] > v1["benchmark_ending_capital"]
        a(
            f"V1 10 bps: {fmt_usd(START_CAP)} → {fmt_usd(v1['ending_capital'])} vs BH {fmt_usd(v1['benchmark_ending_capital'])}. "
            f"CAGR gap {fmt_pct(v1['cagr_minus_bh'])}; Sharpe gap {fmt_num(v1['sharpe_minus_bh'], 2)}. "
            f"{'Yes, higher ending wealth.' if beat else 'No, Buy & Hold ended higher.'}"
        )
    a("")
    a("### 4. Does it survive a 24h delay?")
    a("")
    if v2:
        a(
            f"V2: {fmt_usd(v2['ending_capital'])} vs BH {fmt_usd(v2['benchmark_ending_capital'])}; "
            f"CAGR gap {fmt_pct(v2['cagr_minus_bh'])}; Sharpe gap {fmt_num(v2['sharpe_minus_bh'], 2)}."
        )
        a("Survives 24h" if (v2["cagr_minus_bh"] > 0 or v2["sharpe_minus_bh"] > 0) else "Does **not** survive 24h as an edge vs Buy & Hold.")
    a("")
    a("### 5. Does it survive a 72h delay?")
    a("")
    if v3:
        a(
            f"V3: {fmt_usd(v3['ending_capital'])} vs BH {fmt_usd(v3['benchmark_ending_capital'])}; "
            f"CAGR gap {fmt_pct(v3['cagr_minus_bh'])}; Sharpe gap {fmt_num(v3['sharpe_minus_bh'], 2)}."
        )
        a("Survives 72h" if (v3["cagr_minus_bh"] > 0 or v3["sharpe_minus_bh"] > 0) else "Does **not** survive 72h as an edge vs Buy & Hold.")
    a("")
    a("### 6. What happens with a full one-week information lag?")
    a("")
    if v4:
        a(
            f"V4 uses only macro dated on or before the previous Friday, same model class, execute at Saturday 00:00 UTC. "
            f"{fmt_usd(START_CAP)} → {fmt_usd(v4['ending_capital'])} vs BH {fmt_usd(v4['benchmark_ending_capital'])}; "
            f"CAGR gap {fmt_pct(v4['cagr_minus_bh'])}; Sharpe gap {fmt_num(v4['sharpe_minus_bh'], 2)}."
        )
        if v4["cagr_minus_bh"] > 0 or v4["sharpe_minus_bh"] > 0:
            a("The edge is **not** solely current-Friday prints.")
        else:
            a("The edge **disappears** (or reverses) without current-Friday macro. That is evidence the original result used information that is not conservative.")
    a("")
    a("### 7. Does it survive 10/20/50 bps costs?")
    a("")
    for lab, row in (("0 bps", v1_0), ("10 bps", v1), ("20 bps", v1_20), ("50 bps", v1_50)):
        if row:
            a(
                f"- V1 {lab}: end {fmt_usd(row['ending_capital'])} vs BH {fmt_usd(row['benchmark_ending_capital'])}; "
                f"CAGR gap {fmt_pct(row['cagr_minus_bh'])}; Sharpe gap {fmt_num(row['sharpe_minus_bh'], 2)}; fees {fmt_usd(row['fees_paid'])}."
            )
    a("")
    a("### 8. How many calendar years beat Buy & Hold?")
    a("")
    a(f"V1 10 bps: **{n_beats} / {len(years)}** years beat BH. Strategy lost money in **{n_lose}** years. Exposure < 90% (meaningful cash) in **{n_cash}** years.")
    a("")
    a("| year | strategy | BH | excess | max DD | exposure | beats BH | lost money |")
    a("|---|---:|---:|---:|---:|---:|---|---|")
    for y in years:
        a(
            f"| {y['period']} | {fmt_pct(y['strategy_return'])} | {fmt_pct(y['bh_return'])} | "
            f"{fmt_pct(y['excess_return'])} | {fmt_pct(y['strategy_max_dd'])} | {fmt_pct(y['exposure'])} | "
            f"{'yes' if y['beats_bh'] else 'no'} | {'yes' if y['strategy_lost_money'] else 'no'} |"
        )
    a("")
    a("### 9. Does the result depend heavily on 2017 or another single year?")
    a("")
    a(f"Largest calendar-year strategy return: **{best_year}**.")
    if ex_best:
        a(
            f"Excluding {best_year} (restart $10k on remaining days, same dates for BH): "
            f"end {fmt_usd(ex_best['ending_capital'])} vs BH {fmt_usd(ex_best['benchmark_ending_capital'])}; "
            f"CAGR gap {fmt_pct(ex_best['cagr_minus_bh'])}; Sharpe gap {fmt_num(ex_best['sharpe_minus_bh'], 2)}."
        )
    if ex_2017:
        a(
            f"Excluding 2017: end {fmt_usd(ex_2017['ending_capital'])} vs BH {fmt_usd(ex_2017['benchmark_ending_capital'])}; "
            f"CAGR gap {fmt_pct(ex_2017['cagr_minus_bh'])}; Sharpe gap {fmt_num(ex_2017['sharpe_minus_bh'], 2)}."
        )
    a("")
    a("### 10. Does LONG genuinely contain better BTC weeks than CASH?")
    a("")
    a("| state | N weeks | mean weekly BTC | median | cumulative BTC | vol | frac positive |")
    a("|---|---:|---:|---:|---:|---:|---:|")
    for e in econ:
        a(
            f"| {e.get('state')} | {e.get('n_weeks')} | {fmt_pct(e.get('mean_weekly_btc_return'))} | "
            f"{fmt_pct(e.get('median_weekly_btc_return'))} | {fmt_pct(e.get('cumulative_btc_return'))} | "
            f"{fmt_num(e.get('weekly_volatility'), 3)} | {fmt_pct(e.get('fraction_positive'))} |"
        )
    if long_e and cash_e:
        if (long_e.get("mean_weekly_btc_return") or -9) > (cash_e.get("mean_weekly_btc_return") or 9):
            a("Yes: mean/cumulative BTC while LONG exceeded CASH. The classifier separates environments on this tape.")
        else:
            a("No: LONG weeks were not clearly better than CASH weeks.")
    a("")
    a("This uses the frozen weekly signal vs Friday-to-Friday BTC, not delayed fills.")
    a("")
    a("### 11. What happens to Sharpe relative to Buy & Hold?")
    a("")
    if v1:
        a(f"V1 10 bps Sharpe {fmt_num(v1['sharpe'], 2)} vs BH {fmt_num(v1['benchmark_sharpe'], 2)} (gap {fmt_num(v1['sharpe_minus_bh'], 2)}).")
    if v2:
        a(f"V2 Sharpe gap {fmt_num(v2['sharpe_minus_bh'], 2)}; V3 {fmt_num(v3['sharpe_minus_bh'], 2) if v3 else 'NA'}; V4 {fmt_num(v4['sharpe_minus_bh'], 2) if v4 else 'NA'}.")
    a("")
    a("### 12. What happens to maximum drawdown?")
    a("")
    if v1:
        a(
            f"V1 max DD {fmt_pct(v1['max_drawdown'])} vs BH {fmt_pct(v1['benchmark_max_drawdown'])} "
            f"(difference {fmt_pct(v1['maxdd_minus_bh'])}; more negative = worse)."
        )
    a("")
    a("Subperiods (restart $10k in each block, V1 10 bps):")
    a("")
    a("| block | CAGR | Sharpe | max DD | end $ | BH $ | beats BH |")
    a("|---|---:|---:|---:|---:|---:|---|")
    for b in blocks:
        a(
            f"| {b['period']} | {fmt_pct(b['cagr'])} | {fmt_num(b['sharpe'], 2)} | {fmt_pct(b['max_drawdown'])} | "
            f"{fmt_usd(b['ending_capital'])} | {fmt_usd(b['benchmark_ending_capital'])} | "
            f"{'yes' if b.get('beats_bh') else 'no'} |"
        )
    a("")
    a("Only **2020–2022** beats Buy & Hold on ending wealth. 2017–2019 is a partial start (first signal 2017-02-17) and finishes slightly behind BH. **2023–2026 loses to BH**. A large part of the full-sample gap is 2022, when exposure was ~8% during the bear.")
    a("")
    a("### 13. Final classification")
    a("")
    a(f"**{verdict}**")
    a("")
    a("Rules (frozen before inspecting outputs): PASS requires no V1 look-ahead on **all** features, V1 10 bps superior to BH on CAGR and/or Sharpe, 24h delay still superior, not a single-year artefact, and at least two subperiods with evidence. PASS WITH LIMITATIONS if still economically interesting but timing, delay, lag, costs, or years weaken it. FAIL if the edge needs illegal timing, unrealistically immediate execution, one exceptional year, costs, or has no robust subperiod support.")
    a("")
    a("### 14. Executable strategy")
    a("")
    if verdict in ("PASS", "PASS WITH LIMITATIONS"):
        a("Each Friday after US cash close, compute frozen 12w changes of Fed H.10 broad dollar, H.15 2Y, Treasury 10Y real, Nasdaq Composite.")
        a("Fit expanding L2 logistic (C=1.0, train-only median+scaler, min N=100) on mature BTC 12w sign labels only (`s ≤ t−12`).")
        a("If P(BTC 12w > 0) ≥ 0.50, be long BTC from Saturday 00:00 UTC; else hold cash (0).")
        a("No short, no leverage, no intraweek switching. Budget at least 10 bps round trip per completed entry/exit.")
        a("Do not treat H.10 Friday prints as known before the next business day unless a vintage tape says so.")
    else:
        a("No executable rule. The candidate did not survive validation.")
    a("")
    a("## Switch events (V1, 10 bps)")
    a("")
    a("| decision | event | P | execution | BTC px | next 1w | next 4w | next 12w |")
    a("|---|---|---:|---|---:|---:|---:|---:|")
    for s in switches:
        a(
            f"| {s['decision_date']} | {s['event']} | {fmt_num(s['probability'], 3)} | {s['execution_timestamp']} | "
            f"{fmt_num(s['btc_execution_price'], 2)} | {fmt_pct(s['next_1w_btc_return'])} | "
            f"{fmt_pct(s['next_4w_btc_return'])} | {fmt_pct(s['next_12w_btc_return'])} |"
        )
    a("")
    a("Descriptive only. Threshold stays 0.50.")
    a("")
    a("## Method")
    a("")
    a("- V0 copies Phase 1: Friday UTC close fill, walk-forward contemporaneous Friday features.")
    a("- V1 fill is Saturday 00:00 UTC = that same Friday UTC close on daily bars.")
    a("- V2/V3 delay the **same** V0/V1 signal; no recalculation. Fill at Saturday close / Monday close (Sunday 00:00 / Tuesday 00:00 UTC).")
    a("- V4 refits the same model class on features dated ≤ previous Friday.")
    a("- Buy & Hold uses the exact same start/end as each row.")
    a("- Excluding a calendar year restarts $10k on the remaining dates only.")
    a("- 2017–2019 is partial: first probability week is when min train N=100 is met.")
    a("- Years with ~0% excess vs BH are 100% invested years, not timing skill. `beats_bh` requires >50 bps excess.")
    a("")
    RESULTS.joinpath("MACRO_STRATEGY_VALIDATION.md").write_text("\n".join(lines) + "\n")
    log(f"wrote {RESULTS / 'MACRO_STRATEGY_VALIDATION.md'}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def pack_block(period, eq, bh) -> dict:
    em = equity_metrics(eq)
    bm = equity_metrics(bh)
    return {
        "test_type": "subperiod",
        "period": period,
        "cagr": em["cagr"],
        "sharpe": em["sharpe"],
        "max_drawdown": em["max_drawdown"],
        "ending_capital": em["ending_capital"],
        "benchmark_ending_capital": bm["ending_capital"],
        "benchmark_cagr": bm["cagr"],
        "cagr_minus_bh": em["cagr"] - bm["cagr"] if np.isfinite(em["cagr"]) and np.isfinite(bm["cagr"]) else np.nan,
        "sharpe_minus_bh": em["sharpe"] - bm["sharpe"] if np.isfinite(em["sharpe"]) and np.isfinite(bm["sharpe"]) else np.nan,
        "beats_bh": bool(np.isfinite(em["ending_capital"]) and np.isfinite(bm["ending_capital"]) and em["ending_capital"] > bm["ending_capital"]),
    }


def exclude_year(eq: pd.Series, daily: pd.DataFrame, year: int, fee: float, extra_template: dict) -> dict:
    keep = eq.dropna()
    keep = keep.loc[keep.index.year != year]
    if keep.empty:
        return {}
    scaled = START_CAP * (keep / float(keep.iloc[0]))
    # flatten jumps at year boundaries: use returns within remaining segments
    r = keep.pct_change()
    r = r.loc[keep.index.year != year]
    # year boundary leftover: first day after gap is a jump spanning the excluded year — drop it
    yrs = pd.Series(keep.index.year, index=keep.index)
    gap = yrs != yrs.shift(1)
    r.loc[gap] = 0.0
    eq2 = START_CAP * (1.0 + r.fillna(0.0)).cumprod()
    bh = buy_hold_equity(daily, eq2.index.min(), eq2.index.max())
    # BH must also exclude that year the same way
    bh_s = daily.loc[(daily["date"] >= eq.index.min()) & (daily["date"] <= eq.index.max())].copy()
    bh_s = bh_s.loc[bh_s["date"].dt.year != year]
    if bh_s.empty:
        bh_eq = pd.Series(dtype=float)
    else:
        px = bh_s["close"].to_numpy(dtype=float)
        dts = pd.DatetimeIndex(bh_s["date"])
        br = pd.Series(px, index=dts).pct_change()
        gy = pd.Series(dts.year, index=dts)
        br.loc[gy != gy.shift(1)] = 0.0
        bh_eq = START_CAP * (1.0 + br.fillna(0.0)).cumprod()
    extra = {
        "fees_paid": np.nan,
        "exposure": np.nan,
        "n_entries": np.nan,
        "n_exits": np.nan,
        "n_trades": np.nan,
    }
    bm = equity_metrics(bh_eq)
    rec = summary_row("V1", fee, eq2, extra, bh_eq, bm)
    rec["variant"] = f"V1_ex_{year}"
    rec["variant_label"] = f"exclude_{year}"
    return rec


def main() -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    daily = load_daily()
    last_fri = pd.Timestamp(daily["date"].max())
    while last_fri.weekday() != 4:
        last_fri -= pd.Timedelta(days=1)
    macro = load_macro(last_fri)
    fri = daily.loc[daily["date"].dt.weekday == 4, ["date", "close"]].rename(
        columns={"date": "week", "close": "btc_close"}
    )
    weekly = macro.merge(fri, on="week", how="inner").sort_values("week").reset_index(drop=True)

    wf = macro_walkforward(weekly, lag_features=False)
    wf4 = macro_walkforward(weekly, lag_features=True)

    # Reproduce V0 vs Phase 1
    eq0, _, ex0 = backtest(daily, wf, 0.0010, lag_days=0)
    if np.isfinite(eq0.iloc[-1]):
        err = abs(float(eq0.iloc[-1]) - PHASE1_C_END_10BPS) / PHASE1_C_END_10BPS
        log(f"V0 vs Phase 1 10bps ending rel err={err:.3e} V0={eq0.iloc[-1]:.4f}")
        if err > 1e-6:
            log("WARNING: V0 did not match Phase 1 ending capital to 1e-6 relative.")

    audit_weeks = pd.DatetimeIndex(wf.loc[np.isfinite(wf["p_macro"]), "week"])
    audit = build_timing_audit(audit_weeks)
    audit.to_csv(RESULTS / "TIMING_AUDIT.csv", index=False)
    log(f"wrote {RESULTS / 'TIMING_AUDIT.csv'} rows={len(audit)}")

    summary = []
    robustness = []
    runs = {}
    for name, spec in VARIANTS.items():
        wuse = wf4 if spec.get("lag_features") else wf
        for fee in FEE_SET:
            log(f"{name} fee={fee}")
            eq, tr, extra = backtest(daily, wuse, fee, lag_days=spec["lag_days"])
            if eq.empty:
                continue
            bh = buy_hold_equity(daily, eq.index.min(), eq.index.max())
            bm = equity_metrics(bh)
            rec = summary_row(name, fee, eq, extra, bh, bm)
            summary.append(rec)
            runs[(name, fee)] = {"eq": eq, "extra": extra, "bh": bh, "row": rec, "tr": tr}

    sum_df = pd.DataFrame(summary)
    sum_df.to_csv(RESULTS / "VALIDATION_SUMMARY.csv", index=False)
    log(f"wrote {RESULTS / 'VALIDATION_SUMMARY.csv'} rows={len(sum_df)}")

    v1_10 = runs[("V1", 0.0010)]
    years = year_block(v1_10["eq"], daily, v1_10["extra"])
    for y in years:
        y["variant"] = "V1"
        y["fee_bps_roundtrip"] = 10.0
        robustness.append(y)

    n_beats = sum(1 for y in years if y["beats_bh"])
    n_lose = sum(1 for y in years if y["strategy_lost_money"])
    n_cash = sum(1 for y in years if y["meaningful_cash"])
    robustness.append(
        {
            "test_type": "year_counts",
            "variant": "V1",
            "fee_bps_roundtrip": 10.0,
            "n_years": len(years),
            "n_years_beat_bh": n_beats,
            "n_years_lost_money": n_lose,
            "n_years_meaningful_cash": n_cash,
        }
    )

    blocks = []
    first = v1_10["eq"].dropna().index.min()
    for period, a, b in (
        ("2017-2019", pd.Timestamp("2017-01-01"), pd.Timestamp("2019-12-31")),
        ("2020-2022", pd.Timestamp("2020-01-01"), pd.Timestamp("2022-12-31")),
        ("2023-2026", pd.Timestamp("2023-01-01"), pd.Timestamp("2026-12-31")),
    ):
        eqb, bhb = slice_equity(v1_10["eq"], daily, a, b)
        if eqb.empty:
            continue
        rec = pack_block(period, eqb, bhb)
        rec["note"] = "partial_start" if period == "2017-2019" and first.year == 2017 else ""
        rec["variant"] = "V1"
        rec["fee_bps_roundtrip"] = 10.0
        rec["sample_start"] = eqb.index.min().date().isoformat()
        blocks.append(rec)
        robustness.append(rec)

    # best year by strategy return
    best_year = max(years, key=lambda r: r["strategy_return"])["period"] if years else "2017"
    best_year_i = int(best_year)
    ex_best = exclude_year(v1_10["eq"], daily, best_year_i, 0.0010, v1_10["extra"])
    ex_2017 = exclude_year(v1_10["eq"], daily, 2017, 0.0010, v1_10["extra"])
    if ex_best:
        robustness.append({**ex_best, "test_type": "exclude_year", "period": f"ex_{best_year}"})
    if ex_2017:
        robustness.append({**ex_2017, "test_type": "exclude_year", "period": "ex_2017"})

    econ = signal_economics(wf)
    for e in econ:
        robustness.append(e)

    switches = v1_10["extra"].get("switches") or []
    for s in switches:
        robustness.append({**s, "test_type": "switch_event", "variant": "V1"})

    # delay comparison rows
    for name in ("V0", "V1", "V2", "V3", "V4"):
        if (name, 0.0010) in runs:
            r = runs[(name, 0.0010)]["row"]
            robustness.append({**r, "test_type": "execution_variant_10bps"})

    rob_df = pd.DataFrame(robustness)
    rob_df.to_csv(RESULTS / "ROBUSTNESS_TESTS.csv", index=False)
    log(f"wrote {RESULTS / 'ROBUSTNESS_TESTS.csv'} rows={len(rob_df)}")

    def row(name, fee):
        return runs.get((name, fee), {}).get("row")

    ctx = {
        "audit": audit,
        "v0_10": row("V0", 0.0010),
        "v1_10": row("V1", 0.0010),
        "v2_10": row("V2", 0.0010),
        "v3_10": row("V3", 0.0010),
        "v4_10": row("V4", 0.0010),
        "v1_0": row("V1", 0.0),
        "v1_20": row("V1", 0.0020),
        "v1_50": row("V1", 0.0050),
        "years": years,
        "blocks": blocks,
        "econ": econ,
        "switches": switches,
        "best_year": best_year,
        "ex_best": ex_best,
        "ex_2017": ex_2017,
    }
    ctx["verdict"] = classify(ctx)
    write_report(ctx)


if __name__ == "__main__":
    main()
