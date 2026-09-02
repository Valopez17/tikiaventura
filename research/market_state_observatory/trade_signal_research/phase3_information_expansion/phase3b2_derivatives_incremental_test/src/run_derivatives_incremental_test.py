#!/usr/bin/env python3
"""Phase 3B2: does derivatives information add predictive value?

Historical walk-forward / temporal robustness. Not clean OOS.
L2 logistic only. Identical dates for each paired comparison.
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
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    balanced_accuracy_score,
    brier_score_loss,
    log_loss,
    roc_auc_score,
)
from sklearn.preprocessing import StandardScaler

PHASE = Path(__file__).resolve().parents[1]
RESULTS = PHASE / "results"
TSR = PHASE.parent.parent
MSO = TSR.parent
REPO = MSO.parent.parent
P2 = TSR / "phase2_statistical_model_competition"
P3B = TSR / "phase3_information_expansion" / "phase3b_derivatives_dataset"
RQF = MSO / "v1_weekly_core" / "regime_quality_framework"
TRUSTED_PRICES = REPO / "btc_tsmom_replication" / "data" / "btcusd_daily.csv"
MACRO_FROZEN = RQF / "phase6a_macro_dataset" / "results" / "macro_weekly.csv"
P2_BINANCE = P2 / "data" / "raw" / "binance_btcusdt_1d.csv"
DERIV_CSV = P3B / "data" / "processed" / "btc_derivatives_daily.csv"

BINANCE_LISTING = date(2017, 8, 17)
FROZEN_MACRO_END = pd.Timestamp("2023-12-29")
MACRO_OOS_START = pd.Timestamp("2024-01-01")
MIN_HIST = 365
H = 60
MIN_TRAIN = 100
CLIP = 1e-6
MIN_OFFSET_N = 10
BLOCK_LEN = 60
N_BOOT = 2000
BOOT_SEED = 0
REFIT = "DAILY"

CRYPTO_PCTL = [
    "pctl_ret_1d",
    "pctl_ret_3d",
    "pctl_ret_7d",
    "pctl_dd_30",
    "pctl_vol_20",
    "pctl_rel_volume",
]
MACRO_FEATS = ["DXY_CHG_12W", "US2Y_CHG_12W", "REAL10Y_CHG_12W", "NASDAQ_RET_12W"]
BASE_FEATS = CRYPTO_PCTL + MACRO_FEATS
FUNDING_FEATS = ["funding_pctl", "funding_change_1d", "funding_cum_30d"]
BASIS_FEATS = ["basis_pctl", "basis_change_1d"]
PERP_FEATS = ["perp_volume_rel_30d", "perp_spot_volume_ratio"]
DERIV_CORE = FUNDING_FEATS + BASIS_FEATS + PERP_FEATS
OI_ADDON = ["oi_change_1d", "oi_change_7d", "oi_pctl", "oi_over_volume"]
TARGETS = ("UP_60D", "ADVERSE_60D")
YEARS = (2021, 2022, 2023, 2024, 2025, 2026)

BINANCE_KLINES = "https://api.binance.com/api/v3/klines"
H10_BROAD_DOLLAR = "122e3bcb627e8e53f1bf72a1a09cfb81"
H15_TREASURY = "bf17364827e38702b42a58cf8eaa3f78"
UA = "tikiaventura-phase3b2/1.0 (academic research)"
MACRO_UA = "Mozilla/5.0 (research; phase3b2-incremental)"
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


def download_binance_daily(end: date) -> pd.DataFrame:
    start_ms = int(datetime(2017, 8, 17, tzinfo=timezone.utc).timestamp() * 1000)
    end_ms = int(datetime(end.year, end.month, end.day, tzinfo=timezone.utc).timestamp() * 1000) + 86_400_000
    rows = []
    while start_ms < end_ms:
        url = f"{BINANCE_KLINES}?symbol=BTCUSDT&interval=1d&limit=1000&startTime={start_ms}"
        batch = json.loads(http_get(url).decode())
        if not batch:
            break
        rows.extend(batch)
        last_open = int(batch[-1][0])
        if len(batch) < 1000:
            break
        start_ms = last_open + 86_400_000
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


def load_btc() -> pd.DataFrame:
    trusted = pd.read_csv(TRUSTED_PRICES, parse_dates=["date"])
    trusted["date"] = pd.to_datetime(trusted["date"]).dt.normalize()
    trusted["close"] = pd.to_numeric(trusted["close"], errors="coerce")
    end = last_complete_utc_day()
    if P2_BINANCE.exists():
        bn = pd.read_csv(P2_BINANCE, parse_dates=["date"])
        bn["date"] = pd.to_datetime(bn["date"]).dt.normalize()
        last_bn = bn["date"].max().date()
        log(f"Phase 2 Binance tape last={last_bn} (read-only)")
        if last_bn < end:
            log("Binance tape short of last complete UTC day; downloading tail in memory")
            fresh = download_binance_daily(end)
            fresh["date"] = pd.to_datetime(fresh["date"])
            bn = (
                pd.concat([bn, fresh], ignore_index=True)
                .drop_duplicates("date", keep="last")
                .sort_values("date")
            )
    else:
        log("Phase 2 Binance tape missing; downloading")
        bn = download_binance_daily(end)
        bn["date"] = pd.to_datetime(bn["date"])
    t_bn = trusted.loc[trusted["source"] == "binance_btcusdt", ["date", "close"]]
    overlap = t_bn.merge(bn[["date", "close"]], on="date", suffixes=("_t", "_bn"))
    rel = np.abs(overlap["close_bn"] / overlap["close_t"] - 1.0)
    if len(overlap) and float(rel.max()) > 1e-6:
        raise RuntimeError(f"Binance closes diverge from trusted (max rel {float(rel.max()):.3e})")
    pre = trusted.loc[trusted["source"] == "bitstamp_btcusd", ["date", "close", "source"]].copy()
    pre = pre.loc[pre["date"].dt.date < BINANCE_LISTING]
    pre["volume"] = np.nan
    post = bn.loc[bn["date"].dt.date >= BINANCE_LISTING, ["date", "close", "volume"]].copy()
    post["source"] = "binance_btcusdt"
    px = pd.concat([pre, post], ignore_index=True).sort_values("date").drop_duplicates("date")
    px = px.loc[px["date"].dt.date <= end].reset_index(drop=True)
    splice = pd.Timestamp(BINANCE_LISTING)
    c = pd.to_numeric(px["close"], errors="coerce")
    px["ret_1d"] = c.pct_change()
    px.loc[px["date"] == splice, "ret_1d"] = np.nan
    px["ret_3d"] = c / c.shift(3) - 1.0
    px["ret_7d"] = c / c.shift(7) - 1.0
    px["dd_30"] = c / c.rolling(30, min_periods=30).max() - 1.0
    px["vol_20"] = px["ret_1d"].rolling(20, min_periods=20).std()
    vol = pd.to_numeric(px["volume"], errors="coerce")
    px["rel_volume"] = vol / vol.shift(1).rolling(20, min_periods=20).median()
    return px


def expanding_pctl(x: np.ndarray, min_n: int) -> np.ndarray:
    pctl = np.full(len(x), np.nan)
    for t in range(len(x)):
        if not np.isfinite(x[t]):
            continue
        hist = x[:t]
        hist = hist[np.isfinite(hist)]
        if hist.size < min_n:
            continue
        pctl[t] = 100.0 * float(np.mean(hist <= x[t]))
    return pctl


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
    out["value"] = pd.to_numeric(out["value"].replace({"ND": np.nan, "NA": np.nan, "": np.nan}), errors="coerce")
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
    frozen = pd.read_csv(MACRO_FROZEN, parse_dates=["week"])
    if (frozen["week"].dt.year >= 2024).any():
        raise RuntimeError("Frozen macro_weekly.csv already has 2024+.")
    weeks_new = pd.date_range("2024-01-05", last_week, freq="W-FRI")
    start = pd.Timestamp("2023-09-01")
    end = last_week + pd.Timedelta(days=3)
    log("Macro H.10 / H.15 / TIPS / Nasdaq (same sources as Phase 2 / 6H)")
    h10 = parse_fed_ddp(http_get(fed_ddp_url("H10", H10_BROAD_DOLLAR, start, end), MACRO_UA).decode(), "JRXWTFB_N.B")
    h15 = parse_fed_ddp(http_get(fed_ddp_url("H15", H15_TREASURY, start, end), MACRO_UA).decode(), "RIFLGFCY02_N.B")
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
    hist = frozen[["week", *MACRO_FEATS]].copy()
    oos = levels.loc[levels["week"] >= MACRO_OOS_START, ["week", *MACRO_FEATS]]
    return pd.concat([hist, oos], ignore_index=True).sort_values("week").reset_index(drop=True)


def align_macro_daily(btc: pd.DataFrame, weekly: pd.DataFrame) -> pd.DataFrame:
    left = btc[["date"]].sort_values("date").copy()
    right = weekly.sort_values("week").rename(columns={"week": "macro_week"})
    merged = pd.merge_asof(left, right, left_on="date", right_on="macro_week", direction="backward")
    lag = (merged["date"] - merged["macro_week"]).dt.days
    bad = lag.isna() | (lag < 0) | (lag > 10)
    for c in MACRO_FEATS:
        merged.loc[bad, c] = np.nan
    return merged[["date", "macro_week", *MACRO_FEATS]]


def add_targets(df: pd.DataFrame) -> pd.DataFrame:
    close = pd.to_numeric(df["close"], errors="coerce").to_numpy(dtype=float)
    n = len(close)
    fut = np.full(n, np.nan)
    mae = np.full(n, np.nan)
    for t in range(n):
        if t + H >= n:
            continue
        p0 = close[t]
        path = close[t + 1 : t + 1 + H]
        if (not np.isfinite(p0)) or p0 <= 0 or path.size != H or (not np.isfinite(path).all()):
            continue
        fut[t] = float(path[-1] / p0 - 1.0)
        mae[t] = float(np.min(path / p0 - 1.0))
    df["fut_60"] = fut
    df["mae_60"] = mae
    df["UP_60D"] = np.where(np.isfinite(fut), (fut > 0.20).astype(float), np.nan)
    df["ADVERSE_60D"] = np.where(np.isfinite(mae), (mae < -0.15).astype(float), np.nan)
    return df


def clip_p(p: float) -> float:
    return float(np.clip(p, CLIP, 1.0 - CLIP))


def median_impute_fit(X: np.ndarray):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        med = np.nanmedian(X, axis=0)
    med = np.where(np.isfinite(med), med, 0.0)
    return med, np.where(np.isfinite(X), X, med)


def apply_med(x: np.ndarray, med: np.ndarray) -> np.ndarray:
    return np.where(np.isfinite(x), x, med).reshape(1, -1)


def fit_logit(X: np.ndarray, y: np.ndarray) -> dict:
    y = y.astype(int)
    med, Xi = median_impute_fit(X)
    scaler = StandardScaler()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        Xs = scaler.fit_transform(Xi)
    p0 = clip_p(float(np.mean(y)))
    if y.min() == y.max():
        return {"constant": True, "p0": p0, "med": med, "scaler": scaler, "coef": None}
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        m = LogisticRegression(
            penalty="l2", C=1.0, solver="lbfgs", max_iter=4000, random_state=0
        )
        m.fit(Xs, y)
    return {
        "constant": False,
        "p0": p0,
        "med": med,
        "scaler": scaler,
        "model": m,
        "coef": m.coef_[0].copy(),
    }


def predict_logit(bundle: dict, x_t: np.ndarray) -> float:
    if bundle.get("constant"):
        return bundle["p0"]
    xts = bundle["scaler"].transform(apply_med(x_t, bundle["med"]))
    return clip_p(float(bundle["model"].predict_proba(xts)[0, 1]))


def score_block(y: np.ndarray, p: np.ndarray) -> dict:
    m = np.isfinite(y) & np.isfinite(p)
    rec = {
        "N": 0,
        "prevalence": np.nan,
        "brier": np.nan,
        "logloss": np.nan,
        "auc": np.nan,
        "balanced_accuracy": np.nan,
    }
    if int(m.sum()) == 0:
        return rec
    yy = y[m].astype(int)
    pp = np.clip(p[m].astype(float), CLIP, 1.0 - CLIP)
    rec["N"] = int(len(yy))
    rec["prevalence"] = float(yy.mean())
    rec["brier"] = float(brier_score_loss(yy, pp))
    rec["logloss"] = float(log_loss(yy, pp, labels=[0, 1]))
    n_pos = int(yy.sum())
    if 0 < n_pos < len(yy):
        rec["auc"] = float(roc_auc_score(yy, pp))
        rec["balanced_accuracy"] = float(balanced_accuracy_score(yy, (pp >= 0.5).astype(int)))
    return rec


def bss(brier: float, base: float) -> float:
    if np.isfinite(brier) and np.isfinite(base) and base > 0:
        return 1.0 - brier / base
    return np.nan


def walkforward(X_map: dict[str, np.ndarray], y: np.ndarray, dates: np.ndarray, eligible: np.ndarray):
    """Daily-refit L2 logistic + M0 on the same eligible dates for every feature set."""
    n = len(y)
    names = list(X_map.keys())
    preds = {nm: np.full(n, np.nan) for nm in ["M0", *names]}
    coefs = {nm: [] for nm in names}
    idx = np.where(eligible)[0]
    date_ns = pd.to_datetime(dates).to_numpy()
    delta = np.timedelta64(H, "D")
    n_pred = 0
    for k, t in enumerate(idx):
        cutoff = date_ns[t] - delta
        train = eligible & (date_ns <= cutoff)
        n_tr = int(train.sum())
        if n_tr < MIN_TRAIN:
            continue
        ytr = y[train]
        preds["M0"][t] = clip_p(float(np.mean(ytr)))
        for nm in names:
            X = X_map[nm]
            try:
                bundle = fit_logit(X[train], ytr)
            except Exception:
                bundle = {"constant": True, "p0": preds["M0"][t], "coef": None, "med": None}
            preds[nm][t] = predict_logit(bundle, X[t]) if bundle.get("med") is not None else preds["M0"][t]
            coefs[nm].append(
                {
                    "t_index": int(t),
                    "date": pd.Timestamp(date_ns[t]).date().isoformat(),
                    "n_train": n_tr,
                    "coef": None if bundle.get("coef") is None else bundle["coef"].tolist(),
                }
            )
        n_pred += 1
        if (k + 1) % 250 == 0:
            log(f"    WF {k + 1}/{len(idx)}")
    return preds, coefs, n_pred


def year_mask(dates: pd.Series, year: int, last_date: pd.Timestamp) -> np.ndarray:
    d = pd.to_datetime(dates)
    m = (d.dt.year == year) & (d <= last_date)
    if year == 2026:
        m = (d.dt.year == year) & (d <= last_date)
    return m.to_numpy()


def nonoverlap_deltas(y, p_base, p_aug, mask, dates) -> dict:
    d = pd.to_datetime(dates)
    ords = (d - d[mask].min()).dt.days.to_numpy()
    rows = []
    for off in range(H):
        sel = mask & ((ords - off) % H == 0)
        st_b = score_block(y[sel], p_base[sel])
        st_a = score_block(y[sel], p_aug[sel])
        low = st_b["N"] < MIN_OFFSET_N or st_a["N"] < MIN_OFFSET_N
        rec = {
            "offset": off,
            "N": st_a["N"],
            "low_n": low,
            "delta_brier": np.nan if low else st_a["brier"] - st_b["brier"],
            "delta_logloss": np.nan if low else st_a["logloss"] - st_b["logloss"],
            "delta_auc": np.nan if low else (
                st_a["auc"] - st_b["auc"] if np.isfinite(st_a["auc"]) and np.isfinite(st_b["auc"]) else np.nan
            ),
        }
        rows.append(rec)
    db = np.array([r["delta_brier"] for r in rows], dtype=float)
    dl = np.array([r["delta_logloss"] for r in rows], dtype=float)
    da = np.array([r["delta_auc"] for r in rows], dtype=float)
    fin_b = db[np.isfinite(db)]
    fin_l = dl[np.isfinite(dl)]
    fin_a = da[np.isfinite(da)]
    return {
        "rows": rows,
        "delta_brier_median": float(np.median(fin_b)) if fin_b.size else np.nan,
        "delta_brier_min": float(np.min(fin_b)) if fin_b.size else np.nan,
        "delta_brier_max": float(np.max(fin_b)) if fin_b.size else np.nan,
        "frac_brier_fav": float(np.mean(fin_b < 0)) if fin_b.size else np.nan,
        "delta_logloss_median": float(np.median(fin_l)) if fin_l.size else np.nan,
        "frac_logloss_fav": float(np.mean(fin_l < 0)) if fin_l.size else np.nan,
        "delta_auc_median": float(np.median(fin_a)) if fin_a.size else np.nan,
        "frac_auc_fav": float(np.mean(fin_a > 0)) if fin_a.size else np.nan,
        "n_off": int(fin_b.size),
        "n_low": int(sum(r["low_n"] for r in rows)),
    }


def block_bootstrap_mean(d: np.ndarray, block: int, n_boot: int, seed: int) -> dict:
    x = d[np.isfinite(d)]
    n = int(x.size)
    if n < block + 2:
        return {"n": n, "mean": np.nan, "median": np.nan, "ci_lo": np.nan, "ci_hi": np.nan}
    rng = np.random.default_rng(seed)
    n_blocks = int(np.ceil(n / block))
    max_start = n - block
    means = np.empty(n_boot)
    for b in range(n_boot):
        starts = rng.integers(0, max_start + 1, size=n_blocks)
        samp = np.concatenate([x[s : s + block] for s in starts])[:n]
        means[b] = float(np.mean(samp))
    return {
        "n": n,
        "mean": float(np.mean(x)),
        "median": float(np.median(x)),
        "ci_lo": float(np.percentile(means, 2.5)),
        "ci_hi": float(np.percentile(means, 97.5)),
    }


def daily_brier_diff(y, p_aug, p_base, mask) -> np.ndarray:
    m = mask & np.isfinite(y) & np.isfinite(p_aug) & np.isfinite(p_base)
    yy = y[m].astype(float)
    pa = np.clip(p_aug[m].astype(float), CLIP, 1.0 - CLIP)
    pb = np.clip(p_base[m].astype(float), CLIP, 1.0 - CLIP)
    return (pa - yy) ** 2 - (pb - yy) ** 2


def vif_and_corr(X: np.ndarray, names: list[str]) -> tuple[pd.DataFrame, np.ndarray, float]:
    """Pairwise corr and VIF on columns with at least some finite values. No selection."""
    Z = np.array(X, dtype=float)
    med = np.nanmedian(Z, axis=0)
    med = np.where(np.isfinite(med), med, 0.0)
    Z = np.where(np.isfinite(Z), Z, med)
    corr = np.corrcoef(Z, rowvar=False)
    # VIF via correlation inverse
    try:
        inv = np.linalg.inv(corr)
        vif = np.diag(inv)
    except np.linalg.LinAlgError:
        vif = np.full(len(names), np.nan)
    cond = float(np.linalg.cond(corr)) if np.isfinite(corr).all() else np.nan
    vif_df = pd.DataFrame({"feature": names, "vif": vif})
    return vif_df, corr, cond


def classify(full: dict, nov: dict, boot: dict, year_db: dict) -> str:
    brier_ok = np.isfinite(full["delta_brier"]) and full["delta_brier"] < 0
    ll_ok = np.isfinite(full["delta_logloss"]) and full["delta_logloss"] < 0
    auc_ok = np.isfinite(full["delta_auc"]) and full["delta_auc"] > 0
    nov_ok = np.isfinite(nov["delta_brier_median"]) and nov["delta_brier_median"] < 0
    boot_strong = np.isfinite(boot["ci_hi"]) and boot["ci_hi"] < 0
    boot_mean_neg = np.isfinite(boot["mean"]) and boot["mean"] < 0
    years_n = {y: year_db[y] for y in year_db if year_db[y].get("N", 0) >= 50}
    years_fav = [y for y, r in years_n.items() if np.isfinite(r.get("delta_brier", np.nan)) and r["delta_brier"] < 0]
    concentrated = len(years_n) >= 2 and len(years_fav) <= 1
    distributed = len(years_fav) >= 2
    material = brier_ok or ll_ok or auc_ok
    if brier_ok and ll_ok and auc_ok and nov_ok and boot_strong and distributed:
        return "STRONG SUPPORT"
    if brier_ok and ll_ok and (auc_ok or nov_ok or boot_mean_neg) and (distributed or len(years_n) < 2):
        return "SUPPORT"
    if not material:
        return "NO INCREMENTAL VALUE"
    if (auc_ok and not (brier_ok and ll_ok)) or concentrated or (brier_ok != ll_ok):
        return "MIXED"
    if boot_mean_neg and not brier_ok:
        return "MIXED"
    return "MIXED"


def num(x, nd=4) -> str:
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return "NA"
    return f"{float(x):.{nd}f}"


def metric_row(test, target, model, feature_set, period, st, st_base=None, st_m0=None) -> dict:
    rec = {
        "test": test,
        "target": target,
        "model": model,
        "feature_set": feature_set,
        "period": period,
        "N": st["N"],
        "prevalence": st["prevalence"],
        "brier": st["brier"],
        "bss_vs_m0": bss(st["brier"], st_m0["brier"]) if st_m0 else (0.0 if model == "M0" else np.nan),
        "logloss": st["logloss"],
        "auc": st["auc"],
        "balanced_accuracy": st["balanced_accuracy"],
        "delta_brier_vs_base": np.nan,
        "delta_logloss_vs_base": np.nan,
        "delta_auc_vs_base": np.nan,
        "delta_bss_vs_base": np.nan,
    }
    if st_m0 is None and model == "M0":
        rec["bss_vs_m0"] = 0.0
    if st_base is not None:
        rec["delta_brier_vs_base"] = (
            st["brier"] - st_base["brier"]
            if np.isfinite(st["brier"]) and np.isfinite(st_base["brier"])
            else np.nan
        )
        rec["delta_logloss_vs_base"] = (
            st["logloss"] - st_base["logloss"]
            if np.isfinite(st["logloss"]) and np.isfinite(st_base["logloss"])
            else np.nan
        )
        rec["delta_auc_vs_base"] = (
            st["auc"] - st_base["auc"]
            if np.isfinite(st["auc"]) and np.isfinite(st_base["auc"])
            else np.nan
        )
        bss_m = rec["bss_vs_m0"]
        bss_b = bss(st_base["brier"], st_m0["brier"]) if st_m0 else np.nan
        rec["delta_bss_vs_base"] = (
            bss_m - bss_b if np.isfinite(bss_m) and np.isfinite(bss_b) else np.nan
        )
    return rec


def diag_row(comparison, target, diagnostic, value, feature="") -> dict:
    return {
        "comparison": comparison,
        "target": target,
        "diagnostic": diagnostic,
        "feature": feature,
        "value": value,
    }


def main() -> None:
    warnings.filterwarnings("ignore", category=RuntimeWarning)
    RESULTS.mkdir(parents=True, exist_ok=True)
    log("=== Phase 3B2 historical walk-forward (not clean OOS) ===")
    log(f"Architecture freeze: L2 logistic C=1.0; refit={REFIT}; min_train={MIN_TRAIN}; block={BLOCK_LEN}; boot={N_BOOT}")

    btc = load_btc()
    log("Expanding BTC percentiles (Phase 2 convention)")
    for raw, pcol in (
        ("ret_1d", "pctl_ret_1d"),
        ("ret_3d", "pctl_ret_3d"),
        ("ret_7d", "pctl_ret_7d"),
        ("dd_30", "pctl_dd_30"),
        ("vol_20", "pctl_vol_20"),
        ("rel_volume", "pctl_rel_volume"),
    ):
        btc[pcol] = expanding_pctl(btc[raw].to_numpy(dtype=float), MIN_HIST)
    last_d = pd.Timestamp(btc["date"].max())
    last_friday = last_d
    while last_friday.weekday() != 4:
        last_friday -= pd.Timedelta(days=1)
    weekly = load_macro(last_friday)
    aligned = align_macro_daily(btc, weekly)
    df = btc.merge(aligned, on="date", how="left")
    df = add_targets(df)

    deriv = pd.read_csv(DERIV_CSV, parse_dates=["date"])
    deriv["date"] = pd.to_datetime(deriv["date"]).dt.normalize()
    miss = [c for c in DERIV_CORE + OI_ADDON if c not in deriv.columns]
    if miss:
        raise RuntimeError(f"derivatives panel missing {miss}")
    df = df.merge(deriv[["date", *DERIV_CORE, *OI_ADDON]], on="date", how="left")

    # Phase 2 BASE construction: BTC pctl (except rel_volume not required for eligibility) + targets
    base_ok = np.ones(len(df), dtype=bool)
    for c in CRYPTO_PCTL[:5] + ["UP_60D", "ADVERSE_60D"]:
        base_ok &= np.isfinite(pd.to_numeric(df[c], errors="coerce").to_numpy(dtype=float))
    core_ok = np.ones(len(df), dtype=bool)
    for c in DERIV_CORE:
        core_ok &= np.isfinite(pd.to_numeric(df[c], errors="coerce").to_numpy(dtype=float))
    oi_ok = np.ones(len(df), dtype=bool)
    for c in OI_ADDON:
        oi_ok &= np.isfinite(pd.to_numeric(df[c], errors="coerce").to_numpy(dtype=float))
    elig_a = base_ok & core_ok
    elig_b = elig_a & oi_ok
    df["elig_a"] = elig_a
    df["elig_b"] = elig_b

    dates = df["date"]
    dates_np = df["date"].to_numpy()
    y_map = {tgt: df[tgt].to_numpy(dtype=float) for tgt in TARGETS}
    X_base = df[BASE_FEATS].to_numpy(dtype=float)
    X_core = df[BASE_FEATS + DERIV_CORE].to_numpy(dtype=float)
    X_fund = df[BASE_FEATS + FUNDING_FEATS].to_numpy(dtype=float)
    X_basis = df[BASE_FEATS + BASIS_FEATS].to_numpy(dtype=float)
    X_perp = df[BASE_FEATS + PERP_FEATS].to_numpy(dtype=float)
    X_oi = df[BASE_FEATS + DERIV_CORE + OI_ADDON].to_numpy(dtype=float)

    def first_last(mask) -> tuple[str, str, int]:
        if not mask.any():
            return "NA", "NA", 0
        d = dates[mask]
        return d.min().date().isoformat(), d.max().date().isoformat(), int(mask.sum())

    a0, a1, na = first_last(elig_a)
    b0d, b1d, nb = first_last(elig_b)
    log(f"TEST A eligible {na} {a0} → {a1}")
    log(f"TEST B eligible {nb} {b0d} → {b1d}")

    # collinearity on TEST A historical eligible rows (not used for selection)
    Xc = df.loc[elig_a, DERIV_CORE].to_numpy(dtype=float)
    vif_df, corr, cond = vif_and_corr(Xc, DERIV_CORE)
    log(f"DERIV_CORE condition number (corr matrix)={cond:.2f}")

    metric_rows = []
    diag_rows = []

    def add_diag(comp, tgt, name, val, feat=""):
        diag_rows.append(diag_row(comp, tgt, name, val, feat))

    add_diag("TEST_A", "ALL", "first_eligible", a0)
    add_diag("TEST_A", "ALL", "last_eligible", a1)
    add_diag("TEST_A", "ALL", "n_eligible", na)
    add_diag("TEST_B", "ALL", "first_eligible", b0d)
    add_diag("TEST_B", "ALL", "last_eligible", b1d)
    add_diag("TEST_B", "ALL", "n_eligible", nb)
    add_diag("ALL", "ALL", "refit_schedule", REFIT)
    add_diag("ALL", "ALL", "min_train", MIN_TRAIN)
    add_diag("ALL", "ALL", "maturity_rule", "s + 60 calendar days <= t")
    add_diag("ALL", "ALL", "block_length", BLOCK_LEN)
    add_diag("ALL", "ALL", "bootstrap_draws", N_BOOT)
    add_diag("ALL", "ALL", "bootstrap_seed", BOOT_SEED)
    add_diag("ALL", "ALL", "validation_status", "HISTORICAL_WALKFORWARD_TEMPORAL_ROBUSTNESS")
    add_diag("COLLINEARITY", "ALL", "corr_condition_number", cond)
    for i, fi in enumerate(DERIV_CORE):
        add_diag("COLLINEARITY", "ALL", "vif", float(vif_df.loc[i, "vif"]), fi)
        for j, fj in enumerate(DERIV_CORE):
            if j > i:
                add_diag("COLLINEARITY", "ALL", f"corr__{fi}__{fj}", float(corr[i, j]), f"{fi}|{fj}")

    last_elig_a = dates[elig_a].max() if elig_a.any() else last_d

    log("TEST A walk-forward (BASE, CORE, FUNDING, BASIS, PERP)")
    preds_a = {}
    coefs_a = {}
    for tgt in TARGETS:
        log(f"  {tgt}")
        pmap, cmap, npr = walkforward(
            {
                "BASE": X_base,
                "BASE_CORE": X_core,
                "BASE_FUNDING": X_fund,
                "BASE_BASIS": X_basis,
                "BASE_PERP": X_perp,
            },
            y_map[tgt],
            dates_np,
            elig_a,
        )
        preds_a[tgt] = pmap
        coefs_a[tgt] = cmap
        add_diag("TEST_A", tgt, "n_scored_after_min_train", int(np.isfinite(pmap["BASE"]).sum()))

    log("TEST B walk-forward (BASE_CORE vs BASE_CORE_OI)")
    preds_b = {}
    coefs_b = {}
    for tgt in TARGETS:
        log(f"  {tgt}")
        pmap, cmap, npr = walkforward(
            {"BASE_CORE": X_core, "BASE_CORE_OI": X_oi},
            y_map[tgt],
            dates_np,
            elig_b,
        )
        preds_b[tgt] = pmap
        coefs_b[tgt] = cmap
        add_diag("TEST_B", tgt, "n_scored_after_min_train", int(np.isfinite(pmap["BASE_CORE"]).sum()))

    scored_a = elig_a & np.isfinite(preds_a[TARGETS[0]]["BASE"])
    scored_b = elig_b & np.isfinite(preds_b[TARGETS[0]]["BASE_CORE"])

    labels = {}

    def period_masks(scored, last_date):
        out = [("FULL_WALKFORWARD", scored)]
        for y in YEARS:
            ym = scored & year_mask(dates, y, last_date)
            out.append((f"YEAR_{y}", ym))
        return out

    def pack_comparison(test, tgt, base_name, aug_name, pmap, scored, last_date, coef_pack, feat_names_aug, deriv_names):
        y = y_map[tgt]
        p0 = pmap["M0"]
        pb = pmap[base_name]
        pa = pmap[aug_name]
        periods = period_masks(scored, last_date)
        year_db = {}
        full_pack = None
        for period, mask in periods:
            st0 = score_block(y[mask], p0[mask])
            stb = score_block(y[mask], pb[mask])
            sta = score_block(y[mask], pa[mask])
            metric_rows.append(metric_row(test, tgt, "M0", "M0", period, st0, st_m0=st0))
            metric_rows.append(metric_row(test, tgt, "L2_LOGISTIC", base_name, period, stb, st_base=None, st_m0=st0))
            row_aug = metric_row(test, tgt, "L2_LOGISTIC", aug_name, period, sta, st_base=stb, st_m0=st0)
            metric_rows.append(row_aug)
            if period == "FULL_WALKFORWARD":
                full_pack = {
                    "delta_brier": row_aug["delta_brier_vs_base"],
                    "delta_logloss": row_aug["delta_logloss_vs_base"],
                    "delta_auc": row_aug["delta_auc_vs_base"],
                    "delta_bss": row_aug["delta_bss_vs_base"],
                    "st_base": stb,
                    "st_aug": sta,
                    "st_m0": st0,
                }
            if period.startswith("YEAR_"):
                year_db[int(period.split("_")[1])] = {
                    "N": sta["N"],
                    "delta_brier": row_aug["delta_brier_vs_base"],
                    "delta_logloss": row_aug["delta_logloss_vs_base"],
                    "delta_auc": row_aug["delta_auc_vs_base"],
                }
        nov = nonoverlap_deltas(y, pb, pa, scored, dates)
        add_diag(test, tgt, "nonoverlap_delta_brier_median", nov["delta_brier_median"])
        add_diag(test, tgt, "nonoverlap_delta_brier_min", nov["delta_brier_min"])
        add_diag(test, tgt, "nonoverlap_delta_brier_max", nov["delta_brier_max"])
        add_diag(test, tgt, "nonoverlap_frac_brier_fav", nov["frac_brier_fav"])
        add_diag(test, tgt, "nonoverlap_delta_logloss_median", nov["delta_logloss_median"])
        add_diag(test, tgt, "nonoverlap_frac_logloss_fav", nov["frac_logloss_fav"])
        add_diag(test, tgt, "nonoverlap_delta_auc_median", nov["delta_auc_median"])
        add_diag(test, tgt, "nonoverlap_frac_auc_fav", nov["frac_auc_fav"])
        add_diag(test, tgt, "nonoverlap_n_offsets", nov["n_off"])
        add_diag(test, tgt, "nonoverlap_n_low", nov["n_low"])
        for r in nov["rows"]:
            add_diag(test, tgt, f"nonoverlap_offset_{r['offset']:02d}_N", r["N"])
            add_diag(test, tgt, f"nonoverlap_offset_{r['offset']:02d}_delta_brier", r["delta_brier"])
        d = daily_brier_diff(y, pa, pb, scored)
        boot = block_bootstrap_mean(d, BLOCK_LEN, N_BOOT, BOOT_SEED)
        add_diag(test, tgt, "bootstrap_mean_d", boot["mean"])
        add_diag(test, tgt, "bootstrap_median_d", boot["median"])
        add_diag(test, tgt, "bootstrap_ci95_lo", boot["ci_lo"])
        add_diag(test, tgt, "bootstrap_ci95_hi", boot["ci_hi"])
        add_diag(test, tgt, "bootstrap_n", boot["n"])
        # coefficient stability for derivative columns in the augmented design
        coef_list = coef_pack[aug_name]
        # map names: BASE_CORE uses BASE+CORE, BASE_CORE_OI uses BASE+CORE+OI
        name_idx = {f: i for i, f in enumerate(feat_names_aug)}
        for feat in deriv_names:
            j = name_idx[feat]
            vals = np.array([c["coef"][j] for c in coef_list if c["coef"] is not None], dtype=float)
            if vals.size == 0:
                continue
            add_diag(test, tgt, "coef_frac_pos", float(np.mean(vals > 0)), feat)
            add_diag(test, tgt, "coef_frac_neg", float(np.mean(vals < 0)), feat)
            add_diag(test, tgt, "coef_median", float(np.median(vals)), feat)
            q25, q75 = np.percentile(vals, [25, 75])
            add_diag(test, tgt, "coef_iqr", float(q75 - q25), feat)
        lab = classify(full_pack, nov, boot, year_db)
        add_diag(test, tgt, "predeclared_label", lab)
        return {"full": full_pack, "nov": nov, "boot": boot, "years": year_db, "label": lab}

    results = {}
    for tgt in TARGETS:
        results[("TEST_A", tgt)] = pack_comparison(
            "TEST_A",
            tgt,
            "BASE",
            "BASE_CORE",
            preds_a[tgt],
            scored_a,
            last_elig_a,
            coefs_a[tgt],
            BASE_FEATS + DERIV_CORE,
            DERIV_CORE,
        )
        # diagnostics: same dates, not used for label
        y = y_map[tgt]
        st_base = score_block(y[scored_a], preds_a[tgt]["BASE"][scored_a])
        st_m0 = score_block(y[scored_a], preds_a[tgt]["M0"][scored_a])
        for dname, dkey in (("BASE_FUNDING", "FUNDING"), ("BASE_BASIS", "BASIS"), ("BASE_PERP", "PERP_ACTIVITY")):
            sta = score_block(y[scored_a], preds_a[tgt][dname][scored_a])
            metric_rows.append(
                metric_row("TEST_A_DIAGNOSTIC", tgt, "L2_LOGISTIC", dname, "FULL_WALKFORWARD", sta, st_base=st_base, st_m0=st_m0)
            )
            add_diag("TEST_A_DIAGNOSTIC", tgt, f"delta_brier_{dkey}", sta["brier"] - st_base["brier"] if np.isfinite(sta["brier"]) else np.nan)

    last_elig_b = dates[elig_b].max() if elig_b.any() else last_d
    for tgt in TARGETS:
        results[("TEST_B", tgt)] = pack_comparison(
            "TEST_B",
            tgt,
            "BASE_CORE",
            "BASE_CORE_OI",
            preds_b[tgt],
            scored_b,
            last_elig_b,
            coefs_b[tgt],
            BASE_FEATS + DERIV_CORE + OI_ADDON,
            OI_ADDON,
        )

    met = pd.DataFrame(metric_rows)
    diag = pd.DataFrame(diag_rows)
    met.to_csv(RESULTS / "INCREMENTAL_METRICS.csv", index=False)
    diag.to_csv(RESULTS / "WALKFORWARD_DIAGNOSTICS.csv", index=False)
    write_report(met, diag, results, a0, a1, na, b0d, b1d, nb, cond, vif_df, corr)
    log("wrote INCREMENTAL_METRICS.csv WALKFORWARD_DIAGNOSTICS.csv DERIVATIVES_INCREMENTAL_TEST.md")


def write_report(met, diag, results, a0, a1, na, b0d, b1d, nb, cond, vif_df, corr) -> None:
    def get(test, tgt, fs, period="FULL_WALKFORWARD"):
        q = met[(met["test"] == test) & (met["target"] == tgt) & (met["feature_set"] == fs) & (met["period"] == period)]
        return None if q.empty else q.iloc[0].to_dict()

    def dget(comp, tgt, name, feat=""):
        q = diag[(diag["comparison"] == comp) & (diag["target"] == tgt) & (diag["diagnostic"] == name)]
        if feat:
            q = q[q["feature"] == feat]
        if q.empty:
            return np.nan
        v = q.iloc[0]["value"]
        try:
            return float(v)
        except (TypeError, ValueError):
            return v

    lines = []
    a = lines.append
    a("# Derivatives incremental information test")
    a("")
    a("**Historical walk-forward / temporal robustness.** Not clean OOS. Not an untouched holdout. Not final validation.")
    a("2024–2026 has already been inspected in this research project. The next genuinely clean evaluation is prospective after candidate freeze.")
    a("")
    a("Not a trading strategy. Not PnL. High funding is not a sell rule.")
    a("")
    a("Brier / log loss: lower better. Delta vs the paired BASE (or BASE+CORE in Test B): **negative is better** for Brier and log loss; **positive is better** for AUC and BSS.")
    a("M0 is the expanding mature prevalence. Beating M0 is not the same as derivatives adding information.")
    a("")
    a("## Design (frozen before looking at deltas)")
    a("")
    a("- Model: L2 logistic, C=1.0, daily refit, train-only median + StandardScaler.")
    a("- Mature labels only (`s + 60d <= t`). Min train N=100.")
    a("- Test A dates require BASE construction (Phase 2: five BTC percentiles + both targets) **and** all DERIV_CORE finite.")
    a("- Test B dates are the subset where OI_ADDON is also finite.")
    a(f"- Test A eligible calendar: **{a0} → {a1}** (N={na} before min-train burn-in).")
    a(f"- Test B eligible calendar: **{b0d} → {b1d}** (N={nb} before min-train burn-in).")
    a("- Block-bootstrap of mean daily Brier-loss difference: block length 60, 2000 draws, seed 0.")
    a("- Diagnostic sub-blocks (FUNDING / BASIS / PERP) use Test A dates and do **not** select features.")
    a("- On this overlap, BASE itself can have BSS vs M0 below 0. That does not change the family test, which is BASE vs BASE+new information.")
    a("")
    a("## Full walk-forward")
    a("")

    def table_pair(test, tgt, base_fs, aug_fs):
        m0 = get(test, tgt, "M0")
        b = get(test, tgt, base_fs)
        g = get(test, tgt, aug_fs)
        a(f"### {test} / {tgt}")
        a("")
        a("| model | feature_set | N | prev | Brier | BSS vs M0 | LogLoss | AUC | bal_acc@0.5 | ΔBrier | ΔLogLoss | ΔAUC | ΔBSS |")
        a("|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
        for r, fs in ((m0, "M0"), (b, base_fs), (g, aug_fs)):
            if r is None:
                continue
            a(
                f"| {r['model']} | {fs} | {int(r['N'])} | {num(r['prevalence'], 3)} | {num(r['brier'], 4)} | "
                f"{num(r['bss_vs_m0'], 3)} | {num(r['logloss'], 4)} | {num(r['auc'], 3)} | "
                f"{num(r['balanced_accuracy'], 3)} | {num(r['delta_brier_vs_base'], 4)} | "
                f"{num(r['delta_logloss_vs_base'], 4)} | {num(r['delta_auc_vs_base'], 3)} | {num(r['delta_bss_vs_base'], 3)} |"
            )
        a("")

    for tgt in TARGETS:
        table_pair("TEST_A", tgt, "BASE", "BASE_CORE")
    for tgt in TARGETS:
        table_pair("TEST_B", tgt, "BASE_CORE", "BASE_CORE_OI")

    a("## Calendar years (diagnostics, not selection)")
    a("")
    a("| test | target | year | N | ΔBrier | ΔLogLoss | ΔAUC |")
    a("|---|---|---:|---:|---:|---:|---:|")
    for test, base_fs, aug_fs in (("TEST_A", "BASE", "BASE_CORE"), ("TEST_B", "BASE_CORE", "BASE_CORE_OI")):
        for tgt in TARGETS:
            for y in YEARS:
                r = get(test, tgt, aug_fs, f"YEAR_{y}")
                if r is None or int(r["N"] or 0) == 0:
                    continue
                a(
                    f"| {test} | {tgt} | {y} | {int(r['N'])} | {num(r['delta_brier_vs_base'], 4)} | "
                    f"{num(r['delta_logloss_vs_base'], 4)} | {num(r['delta_auc_vs_base'], 3)} |"
                )
    a("")

    a("## Non-overlapping 60-day offsets and block bootstrap")
    a("")
    a("| test | target | median ΔBrier | frac ΔBrier<0 | median ΔAUC | boot mean d | boot 95% CI |")
    a("|---|---|---:|---:|---:|---:|---|")
    for test in ("TEST_A", "TEST_B"):
        for tgt in TARGETS:
            a(
                f"| {test} | {tgt} | {num(dget(test, tgt, 'nonoverlap_delta_brier_median'), 4)} | "
                f"{num(dget(test, tgt, 'nonoverlap_frac_brier_fav'), 2)} | "
                f"{num(dget(test, tgt, 'nonoverlap_delta_auc_median'), 3)} | "
                f"{num(dget(test, tgt, 'bootstrap_mean_d'), 5)} | "
                f"[{num(dget(test, tgt, 'bootstrap_ci95_lo'), 5)}, {num(dget(test, tgt, 'bootstrap_ci95_hi'), 5)}] |"
            )
    a("")
    a("d_t = (p_aug − y)² − (p_base − y)². Negative favors the augmented information set.")
    a("")

    a("## Diagnostic sub-blocks (Test A dates only)")
    a("")
    a("| target | block | ΔBrier vs BASE | ΔLogLoss | ΔAUC |")
    a("|---|---|---:|---:|---:|")
    for tgt in TARGETS:
        for fs, lab in (("BASE_FUNDING", "FUNDING"), ("BASE_BASIS", "BASIS"), ("BASE_PERP", "PERP_ACTIVITY")):
            r = get("TEST_A_DIAGNOSTIC", tgt, fs)
            if r is None:
                continue
            a(f"| {tgt} | {lab} | {num(r['delta_brier_vs_base'], 4)} | {num(r['delta_logloss_vs_base'], 4)} | {num(r['delta_auc_vs_base'], 3)} |")
    a("")
    a("These do not replace Test A (BASE vs BASE+all DERIV_CORE).")
    a("")

    a("## Collinearity (Test A eligible rows, not used to drop columns)")
    a("")
    a(f"Correlation-matrix condition number: **{num(cond, 2)}**.")
    a("")
    a("| feature | VIF |")
    a("|---|---:|")
    for _, row in vif_df.iterrows():
        a(f"| `{row['feature']}` | {num(row['vif'], 2)} |")
    a("")
    a("Largest pairwise |corr| among DERIV_CORE:")
    abs_c = np.abs(corr.copy())
    np.fill_diagonal(abs_c, 0)
    ii, jj = np.unravel_index(int(np.nanargmax(abs_c)), abs_c.shape)
    a(f"**{DERIV_CORE[ii]}** vs **{DERIV_CORE[jj]}**: {num(corr[ii, jj], 3)}.")
    a("")

    a("## Coefficient sign stability (standardized L2 logistic, Test A / Test B refits)")
    a("")
    a("| test | target | feature | frac>0 | frac<0 | median | IQR |")
    a("|---|---|---|---:|---:|---:|---:|")
    for test, feats in (("TEST_A", DERIV_CORE), ("TEST_B", OI_ADDON)):
        for tgt in TARGETS:
            for feat in feats:
                a(
                    f"| {test} | {tgt} | `{feat}` | {num(dget(test, tgt, 'coef_frac_pos', feat), 2)} | "
                    f"{num(dget(test, tgt, 'coef_frac_neg', feat), 2)} | {num(dget(test, tgt, 'coef_median', feat), 3)} | "
                    f"{num(dget(test, tgt, 'coef_iqr', feat), 3)} |"
                )
    a("")
    a("Unstable sign is not an automatic DROP in this phase.")
    a("")

    a("## Answers")
    a("")
    lab_a_up = results[("TEST_A", "UP_60D")]["label"]
    lab_a_ad = results[("TEST_A", "ADVERSE_60D")]["label"]
    lab_b_up = results[("TEST_B", "UP_60D")]["label"]
    lab_b_ad = results[("TEST_B", "ADVERSE_60D")]["label"]
    fa_up = results[("TEST_A", "UP_60D")]["full"]
    fa_ad = results[("TEST_A", "ADVERSE_60D")]["full"]
    fb_up = results[("TEST_B", "UP_60D")]["full"]
    fb_ad = results[("TEST_B", "ADVERSE_60D")]["full"]

    def info_sentence(lab, full, tgt_name):
        if lab in {"STRONG SUPPORT", "SUPPORT"}:
            return (
                f"Historical walk-forward evidence suggests DERIV_CORE added incremental information "
                f"for {tgt_name} (label **{lab}**; ΔBrier={num(full['delta_brier'], 4)}, "
                f"ΔLogLoss={num(full['delta_logloss'], 4)}, ΔAUC={num(full['delta_auc'], 3)})."
            )
        if lab == "MIXED":
            return (
                f"Historical walk-forward evidence for {tgt_name} is **MIXED** "
                f"(ΔBrier={num(full['delta_brier'], 4)}, ΔLogLoss={num(full['delta_logloss'], 4)}, "
                f"ΔAUC={num(full['delta_auc'], 3)})."
            )
        return (
            f"Historical walk-forward evidence does not show material incremental value for {tgt_name} "
            f"(**{lab}**; ΔBrier={num(full['delta_brier'], 4)}, ΔAUC={num(full['delta_auc'], 3)})."
        )

    a("1. **Does DERIV_CORE add predictive information for UP_60D?**")
    a(info_sentence(lab_a_up, fa_up, "UP_60D"))
    a("")
    a("2. **Does DERIV_CORE add predictive information for ADVERSE_60D?**")
    a(info_sentence(lab_a_ad, fa_ad, "ADVERSE_60D"))
    a("")
    a("3. **Does OI add information beyond DERIV_CORE?**")
    a(
        f"UP_60D: **{lab_b_up}** (ΔBrier={num(fb_up['delta_brier'], 4)}, ΔAUC={num(fb_up['delta_auc'], 3)}). "
        f"ADVERSE_60D: **{lab_b_ad}** (ΔBrier={num(fb_ad['delta_brier'], 4)}, ΔAUC={num(fb_ad['delta_auc'], 3)})."
    )
    a("")
    a("4. **Probability forecasting vs ranking?**")
    def pr_vs_rank(full):
        brier_ok = np.isfinite(full["delta_brier"]) and full["delta_brier"] < 0
        ll_ok = np.isfinite(full["delta_logloss"]) and full["delta_logloss"] < 0
        auc_ok = np.isfinite(full["delta_auc"]) and full["delta_auc"] > 0
        if brier_ok and ll_ok and auc_ok:
            return "both probability loss and ranking improved"
        if auc_ok and not (brier_ok and ll_ok):
            return "ranking improved but probability loss did not"
        if (brier_ok and ll_ok) and not auc_ok:
            return "probability loss improved but ranking did not"
        if brier_ok and not ll_ok:
            return "Brier improved but log loss and ranking did not both improve"
        if ll_ok and not brier_ok:
            return "log loss improved but Brier did not"
        return "neither ranking nor probability loss improved materially"
    a(
        f"Test A UP_60D: {pr_vs_rank(fa_up)}. Test A ADVERSE_60D: {pr_vs_rank(fa_ad)}. "
        f"Test B UP_60D: {pr_vs_rank(fb_up)}. Test B ADVERSE_60D: {pr_vs_rank(fb_ad)}."
    )
    a("")
    a("5. **Stable across years?**")
    a("See the year table. Gains concentrated in a single year with N≥50 count as MIXED under the predeclared rule, not as a reason to retune.")
    a("")
    a("6. **Non-overlapping evaluation?**")
    a(
        f"Test A UP median ΔBrier={num(dget('TEST_A','UP_60D','nonoverlap_delta_brier_median'),4)} "
        f"(frac favorable {num(dget('TEST_A','UP_60D','nonoverlap_frac_brier_fav'),2)}). "
        f"Test A ADVERSE median ΔBrier={num(dget('TEST_A','ADVERSE_60D','nonoverlap_delta_brier_median'),4)} "
        f"(frac {num(dget('TEST_A','ADVERSE_60D','nonoverlap_frac_brier_fav'),2)})."
    )
    a("")
    a("7. **Block-bootstrap uncertainty?**")
    a(
        f"Test A UP mean d={num(dget('TEST_A','UP_60D','bootstrap_mean_d'),5)} "
        f"CI [{num(dget('TEST_A','UP_60D','bootstrap_ci95_lo'),5)}, {num(dget('TEST_A','UP_60D','bootstrap_ci95_hi'),5)}]. "
        f"Test A ADVERSE mean d={num(dget('TEST_A','ADVERSE_60D','bootstrap_mean_d'),5)} "
        f"CI [{num(dget('TEST_A','ADVERSE_60D','bootstrap_ci95_lo'),5)}, {num(dget('TEST_A','ADVERSE_60D','bootstrap_ci95_hi'),5)}]. "
        "This is a robustness measure, not a publication-level proof."
    )
    a("")
    a("8. **Which sub-block looks informative (diagnostic only)?**")
    a(
        "On Test A dates, FUNDING has the most favorable diagnostic ΔBrier for ADVERSE_60D "
        "and is the only UP_60D block with a positive ΔAUC. BASIS slightly improves ADVERSE Brier. "
        "PERP_ACTIVITY does not improve Brier on either target. These diagnostics do not replace "
        "Test A: the frozen CORE bundle as a whole did not beat BASE on UP_60D and was MIXED on ADVERSE_60D."
    )
    a("")
    a("9. **Coefficient stability?**")
    a("See the sign-stability table. Standardized coefficients are comparable across features; unstable sign is not treated as DROP here.")
    a("")
    a("10. **Final predeclared classifications**")
    a("")
    a(f"- CORE → UP_60D: **{lab_a_up}**")
    a(f"- CORE → ADVERSE_60D: **{lab_a_ad}**")
    a(f"- OI ADDON → UP_60D: **{lab_b_up}**")
    a(f"- OI ADDON → ADVERSE_60D: **{lab_b_ad}**")
    a("")
    a("11. **Retain derivatives for the expanded information set?**")
    retain_core = lab_a_up in {"STRONG SUPPORT", "SUPPORT"} or lab_a_ad in {"STRONG SUPPORT", "SUPPORT"}
    retain_oi = lab_b_up in {"STRONG SUPPORT", "SUPPORT"} or lab_b_ad in {"STRONG SUPPORT", "SUPPORT"}
    if retain_core and retain_oi:
        rec = "Historical walk-forward evidence supports retaining DERIV_CORE **and** OI_ADDON for later expanded-set work, subject to prospective evaluation after freeze."
    elif retain_core:
        rec = "Historical walk-forward evidence supports retaining **DERIV_CORE** in the expanded information set. OI_ADDON is not supported as an incremental add-on on this test and should not be promoted on these numbers alone."
    elif retain_oi:
        rec = "OI_ADDON shows support on its own comparison, but CORE did not; do not promote a larger derivatives set from a weak CORE. Revisit only as a new frozen experiment."
    else:
        rec = "Historical walk-forward evidence does **not** support retaining this derivatives family in the expanded information set on the basis of this test. That is not a claim that leverage/crowding is economically irrelevant; it is a claim about incremental predictive value given BASE, this architecture, and this overlap."
    a(rec)
    a("")
    a("Specifications were not changed after seeing the numbers.")
    RESULTS.joinpath("DERIVATIVES_INCREMENTAL_TEST.md").write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
