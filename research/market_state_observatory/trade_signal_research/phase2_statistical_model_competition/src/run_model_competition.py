#!/usr/bin/env python3
"""Phase 2: frozen statistical model competition, chronological 80/20 holdout.

Not a strategy. Holdout is not used for selection, features, or thresholds.
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
import statsmodels.api as sm
from patsy import build_design_matrices, dmatrix
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    balanced_accuracy_score,
    brier_score_loss,
    log_loss,
    roc_auc_score,
)
from sklearn.preprocessing import StandardScaler
from statsmodels.discrete.discrete_model import Logit, Probit
from statsmodels.genmod.families import Binomial
from statsmodels.genmod.generalized_linear_model import GLM

PHASE = Path(__file__).resolve().parents[1]
RESULTS = PHASE / "results"
RAW = PHASE / "data" / "raw"
TSR = PHASE.parent
MSO = TSR.parent
REPO = MSO.parent.parent
RQF = MSO / "v1_weekly_core" / "regime_quality_framework"
TRUSTED_PRICES = REPO / "btc_tsmom_replication" / "data" / "btcusd_daily.csv"
MACRO_FROZEN = RQF / "phase6a_macro_dataset" / "results" / "macro_weekly.csv"

BINANCE_LISTING = date(2017, 8, 17)
FROZEN_MACRO_END = pd.Timestamp("2023-12-29")
MACRO_OOS_START = pd.Timestamp("2024-01-01")
MIN_HIST = 365
H = 60
MIN_TRAIN = 100
CLIP = 1e-6
MIN_OFFSET_N = 10
CRYPTO_PCTL = [
    "pctl_ret_1d",
    "pctl_ret_3d",
    "pctl_ret_7d",
    "pctl_dd_30",
    "pctl_vol_20",
    "pctl_rel_volume",
]
MACRO_FEATS = ["DXY_CHG_12W", "US2Y_CHG_12W", "REAL10Y_CHG_12W", "NASDAQ_RET_12W"]
FEATURES = CRYPTO_PCTL + MACRO_FEATS
TARGETS = ("UP_60D", "ADVERSE_60D")
MODELS = ("M0", "M1", "M2", "M3", "M4", "M5")
BINANCE_KLINES = "https://api.binance.com/api/v3/klines"
H10_BROAD_DOLLAR = "122e3bcb627e8e53f1bf72a1a09cfb81"
H15_TREASURY = "bf17364827e38702b42a58cf8eaa3f78"
UA = "tikiaventura-phase2-model-competition/1.0 (academic research)"
MACRO_UA = "Mozilla/5.0 (research; phase2-model-competition)"
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


def load_btc() -> pd.DataFrame:
    if not TRUSTED_PRICES.exists():
        raise RuntimeError(f"Trusted BTC file missing: {TRUSTED_PRICES}")
    trusted = pd.read_csv(TRUSTED_PRICES, parse_dates=["date"])
    trusted["date"] = pd.to_datetime(trusted["date"]).dt.normalize()
    trusted["close"] = pd.to_numeric(trusted["close"], errors="coerce")
    end = last_complete_utc_day()
    RAW.mkdir(parents=True, exist_ok=True)
    log("Binance BTCUSDT 1d")
    bn = download_binance_daily(end)
    bn["date"] = pd.to_datetime(bn["date"])
    bn.to_csv(RAW / "binance_btcusdt_1d.csv", index=False)
    t_bn = trusted.loc[trusted["source"] == "binance_btcusdt", ["date", "close"]]
    overlap = t_bn.merge(bn[["date", "close"]], on="date", suffixes=("_t", "_bn"))
    rel = np.abs(overlap["close_bn"] / overlap["close_t"] - 1.0)
    if float(rel.max()) > 1e-6:
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
    miss = [c for c in ["DXY_LEVEL", "US2Y", "REAL10Y", "NASDAQ", *MACRO_FEATS] if c not in frozen.columns]
    if miss:
        raise RuntimeError(f"frozen macro missing {miss}")
    weeks_new = pd.date_range("2024-01-05", last_week, freq="W-FRI")
    start = pd.Timestamp("2023-09-01")
    end = last_week + pd.Timedelta(days=3)
    log("Macro H.10 / H.15 / TIPS / Nasdaq (same sources as Phase 6H)")
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
    log("macro 2015–2023 splice exact match")
    hist = frozen[["week", *MACRO_FEATS]].copy()
    oos = levels.loc[levels["week"] >= MACRO_OOS_START, ["week", *MACRO_FEATS]]
    return pd.concat([hist, oos], ignore_index=True).sort_values("week").reset_index(drop=True)


def align_macro_daily(btc: pd.DataFrame, weekly: pd.DataFrame) -> pd.DataFrame:
    left = btc[["date"]].sort_values("date").copy()
    right = weekly.sort_values("week").rename(columns={"week": "macro_week"})
    merged = pd.merge_asof(
        left,
        right,
        left_on="date",
        right_on="macro_week",
        direction="backward",
    )
    lag = (merged["date"] - merged["macro_week"]).dt.days
    # Latest Friday <= t. Saturday–Thursday lag is 1–6. Never a future Friday.
    bad = lag.isna() | (lag < 0) | (lag > 10)
    for c in MACRO_FEATS:
        merged.loc[bad, c] = np.nan
    merged["macro_lag_days"] = lag
    return merged[["date", "macro_week", "macro_lag_days", *MACRO_FEATS]]


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


REFIT_EVERY = 7  # heavier models; M0 still updates every t. Train rows remain mature.


def _median_impute_fit(X_train: np.ndarray):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        med = np.nanmedian(X_train, axis=0)
    med = np.where(np.isfinite(med), med, 0.0)
    return med, np.where(np.isfinite(X_train), X_train, med)


def _apply_med(x_t: np.ndarray, med: np.ndarray) -> np.ndarray:
    return np.where(np.isfinite(x_t), x_t, med).reshape(1, -1)


def fit_bundle(X, y) -> dict:
    """Fit M1–M5 once on a mature training fold."""
    y = y.astype(int)
    med, Xi = _median_impute_fit(X)
    scaler = StandardScaler()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        Xs = scaler.fit_transform(Xi)
    bundle = {"med": med, "scaler": scaler, "p0": clip_p(float(np.mean(y)))}
    if y.min() == y.max():
        bundle["constant"] = True
        return bundle
    bundle["constant"] = False
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        m1 = LogisticRegression(penalty="l2", C=1.0, solver="lbfgs", max_iter=2000, random_state=0)
        m1.fit(Xs, y)
        bundle["M1"] = m1
        Xs_c = sm.add_constant(Xs, has_constant="add")
        try:
            bundle["M2"] = Probit(y, Xs_c).fit(disp=False, maxiter=200)
        except Exception:
            bundle["M2"] = None
        m3 = LogisticRegression(
            penalty="elasticnet", solver="saga", l1_ratio=0.5, C=1.0, max_iter=4000, random_state=0
        )
        m3.fit(Xs, y)
        bundle["M3"] = m3
        data = {f"f{i}": Xi[:, i] for i in range(Xi.shape[1])}
        form = " + ".join(f"cr(f{i}, df=4)" for i in range(Xi.shape[1]))
        design = dmatrix(form, data, return_type="dataframe")
        bundle["M4_info"] = design.design_info
        try:
            bundle["M4"] = GLM(y, design, family=Binomial()).fit(disp=0, maxiter=200)
        except Exception:
            bundle["M4"] = None
        m5 = GradientBoostingClassifier(
            n_estimators=100, max_depth=2, learning_rate=0.05, random_state=0
        )
        m5.fit(Xi, y)
        bundle["M5"] = m5
    return bundle


def predict_bundle(bundle: dict, x_t: np.ndarray) -> dict:
    p0 = bundle["p0"]
    if bundle.get("constant"):
        return {m: p0 for m in PREDICTORS}
    med = bundle["med"]
    xti = _apply_med(x_t, med)
    xts = bundle["scaler"].transform(xti)
    out = {}
    try:
        out["M1"] = clip_p(float(bundle["M1"].predict_proba(xts)[0, 1]))
    except Exception:
        out["M1"] = p0
    try:
        xt_c = sm.add_constant(xts, has_constant="add")
        out["M2"] = clip_p(float(bundle["M2"].predict(xt_c)[0])) if bundle.get("M2") is not None else p0
    except Exception:
        out["M2"] = p0
    try:
        out["M3"] = clip_p(float(bundle["M3"].predict_proba(xts)[0, 1]))
    except Exception:
        out["M3"] = p0
    try:
        if bundle.get("M4") is None:
            out["M4"] = p0
        else:
            data_t = {f"f{i}": xti[:, i] for i in range(xti.shape[1])}
            design_t = build_design_matrices([bundle["M4_info"]], data_t, return_type="dataframe")[0]
            out["M4"] = clip_p(float(bundle["M4"].predict(design_t).iloc[0]))
    except Exception:
        out["M4"] = p0
    try:
        out["M5"] = clip_p(float(bundle["M5"].predict_proba(xti)[0, 1]))
    except Exception:
        out["M5"] = p0
    return out


PREDICTORS = ("M1", "M2", "M3", "M4", "M5")


def score_block(y: np.ndarray, p: np.ndarray) -> dict:
    m = np.isfinite(y) & np.isfinite(p)
    rec = {
        "N": 0,
        "prevalence": np.nan,
        "brier": np.nan,
        "log_loss": np.nan,
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
    rec["log_loss"] = float(log_loss(yy, pp, labels=[0, 1]))
    n_pos = int(yy.sum())
    if 0 < n_pos < len(yy):
        rec["auc"] = float(roc_auc_score(yy, pp))
        rec["balanced_accuracy"] = float(balanced_accuracy_score(yy, (pp >= 0.5).astype(int)))
    return rec


def bss(brier: float, base: float) -> float:
    if np.isfinite(brier) and np.isfinite(base) and base > 0:
        return 1.0 - brier / base
    return np.nan


def nonoverlap(y, p_m, p0, mask, step: int = H) -> dict:
    idx = np.arange(len(y))
    skills, offsets, n_low = [], [], 0
    for off in range(step):
        sel = mask & ((idx - off) % step == 0)
        n_sel = int((np.isfinite(y) & np.isfinite(p_m) & sel).sum())
        if n_sel < MIN_OFFSET_N:
            n_low += 1
            offsets.append({"offset": off, "N": n_sel, "bss": np.nan, "low_n": True})
            continue
        st_m = score_block(y[sel], p_m[sel])
        st_0 = score_block(y[sel], p0[sel])
        skill = bss(st_m["brier"], st_0["brier"])
        skills.append(skill)
        offsets.append({"offset": off, "N": st_m["N"], "bss": skill, "low_n": False})
    arr = np.asarray(skills, dtype=float)
    finite = arr[np.isfinite(arr)]
    if finite.size == 0:
        return {
            "bss_median": np.nan,
            "bss_min": np.nan,
            "bss_max": np.nan,
            "n_pos": 0,
            "n_off": 0,
            "n_low": n_low,
            "offsets": offsets,
        }
    return {
        "bss_median": float(np.median(finite)),
        "bss_min": float(np.min(finite)),
        "bss_max": float(np.max(finite)),
        "n_pos": int(np.sum(finite > 0)),
        "n_off": int(finite.size),
        "n_low": n_low,
        "offsets": offsets,
    }


def select_candidate(dev_rows: dict) -> str | None:
    """dev_rows maps model -> score dict including M0."""
    m0 = dev_rows["M0"]
    qualified = []
    for name in ("M1", "M2", "M3", "M4", "M5"):
        r = dev_rows[name]
        skill = bss(r["brier"], m0["brier"])
        ok = (
            np.isfinite(skill)
            and skill > 0
            and np.isfinite(r["log_loss"])
            and np.isfinite(m0["log_loss"])
            and r["log_loss"] < m0["log_loss"]
            and np.isfinite(r["auc"])
            and r["auc"] > 0.55
        )
        if ok:
            qualified.append((skill, name))
    if not qualified:
        return None
    qualified.sort(reverse=True)
    return qualified[0][1]


def classify_holdout(hold: dict, m0: dict, nov: dict) -> str:
    skill = bss(hold["brier"], m0["brier"])
    ll_ok = np.isfinite(hold["log_loss"]) and np.isfinite(m0["log_loss"]) and hold["log_loss"] < m0["log_loss"]
    auc_ok = np.isfinite(hold["auc"]) and hold["auc"] > 0.55
    bss_ok = np.isfinite(skill) and skill > 0
    med = nov.get("bss_median")
    robust = bool(np.isfinite(med) and med > 0 and int(nov.get("n_off") or 0) > 0)
    if bss_ok and ll_ok and auc_ok and robust:
        return "VALIDATED"
    if bss_ok or auc_ok:
        return "MIXED"
    return "FAIL"


def reliability_table(y: np.ndarray, p: np.ndarray, n_bins: int = 10) -> list[dict]:
    m = np.isfinite(y) & np.isfinite(p)
    yy, pp = y[m], np.clip(p[m], CLIP, 1.0 - CLIP)
    if len(yy) == 0:
        return []
    bins = np.linspace(0.0, 1.0, n_bins + 1)
    out = []
    for i in range(n_bins):
        lo, hi = bins[i], bins[i + 1]
        sel = (pp >= lo) & (pp < hi if i < n_bins - 1 else pp <= hi)
        if int(sel.sum()) == 0:
            continue
        out.append(
            {
                "bin": f"[{lo:.1f},{hi:.1f}{')' if i < n_bins - 1 else ']'}",
                "N": int(sel.sum()),
                "mean_p": float(pp[sel].mean()),
                "mean_y": float(yy[sel].mean()),
            }
        )
    return out


def logit_calibration(y: np.ndarray, p: np.ndarray) -> dict:
    m = np.isfinite(y) & np.isfinite(p)
    yy = y[m].astype(int)
    pp = np.clip(p[m].astype(float), CLIP, 1.0 - CLIP)
    rec = {"intercept": np.nan, "slope": np.nan, "N": int(len(yy))}
    if len(yy) < 30 or yy.min() == yy.max():
        return rec
    lp = np.log(pp / (1.0 - pp))
    X = sm.add_constant(lp, has_constant="add")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        res = Logit(yy, X).fit(disp=False, maxiter=200)
    rec["intercept"] = float(res.params[0])
    rec["slope"] = float(res.params[1])
    return rec


def pct(x, nd=3) -> str:
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return "NA"
    return f"{float(x):.{nd}f}"


def walkforward_both(X, y_map, dates, eligible) -> dict:
    """Expanding WF. M0 every t. M1–M5 refit every REFIT_EVERY eligible dates."""
    n = len(eligible)
    out = {tgt: {m: np.full(n, np.nan) for m in MODELS} for tgt in TARGETS}
    idx = np.where(eligible)[0]
    date_ns = pd.to_datetime(dates).to_numpy()
    delta = np.timedelta64(H, "D")
    cache = {tgt: None for tgt in TARGETS}
    last_fit = {tgt: -REFIT_EVERY for tgt in TARGETS}
    for k, t in enumerate(idx):
        cutoff = date_ns[t] - delta
        train = eligible & (date_ns <= cutoff)
        n_tr = int(train.sum())
        if n_tr < MIN_TRAIN:
            continue
        Xtr = X[train]
        xt = X[t]
        for tgt in TARGETS:
            ytr = y_map[tgt][train]
            p0 = clip_p(float(np.mean(ytr)))
            out[tgt]["M0"][t] = p0
            if (k - last_fit[tgt]) >= REFIT_EVERY or cache[tgt] is None:
                try:
                    cache[tgt] = fit_bundle(Xtr, ytr)
                except Exception:
                    cache[tgt] = {"constant": True, "p0": p0}
                last_fit[tgt] = k
            pred = predict_bundle(cache[tgt], xt)
            for m in PREDICTORS:
                out[tgt][m][t] = pred[m]
        if (k + 1) % 200 == 0:
            log(f"  WF {k + 1}/{len(idx)}")
    return out


def metric_row(target, model, period, st, base_brier, **extra) -> dict:
    rec = {
        "target": target,
        "model": model,
        "period": period,
        "N": st["N"],
        "prevalence": st["prevalence"],
        "brier": st["brier"],
        "brier_skill_vs_M0": 0.0 if model == "M0" else bss(st["brier"], base_brier),
        "log_loss": st["log_loss"],
        "auc": st["auc"],
        "balanced_accuracy": st["balanced_accuracy"],
        "bss_median": np.nan,
        "bss_min": np.nan,
        "bss_max": np.nan,
        "n_offsets_bss_gt0": np.nan,
        "n_offsets": np.nan,
        "selected": extra.pop("selected", ""),
        "note": extra.pop("note", ""),
    }
    rec.update(extra)
    return rec


def write_feature_spec(meta: dict) -> None:
    lines = []
    lines.append("# Feature specification — Phase 2 (frozen before holdout scoring)")
    lines.append("")
    lines.append("Written after computing the chronological split and **before** looking at holdout metrics.")
    lines.append("Holdout is not used for feature, target, model, or threshold choices.")
    lines.append("")
    lines.append("## Chronological split")
    lines.append("")
    lines.append("| item | value |")
    lines.append("|---|---|")
    lines.append(f"| eligible N | {meta['n_eligible']} |")
    lines.append(f"| development N | {meta['n_dev']} |")
    lines.append(f"| holdout N | {meta['n_hold']} |")
    lines.append(f"| split: last development date | **{meta['split_date']}** |")
    lines.append(f"| first holdout date | {meta['hold_start']} |")
    lines.append(f"| last eligible date | {meta['last_eligible']} |")
    lines.append("| rule | first 80% of eligible dates by chronological order; last 20% untouched |")
    lines.append("")
    lines.append("## Targets (frozen)")
    lines.append("")
    lines.append("- `UP_60D` = 1 if P(t+60)/P(t) − 1 > +20%, else 0.")
    lines.append("- `ADVERSE_60D` = 1 if MAE < −15%, else 0.")
    lines.append("- MAE = min_{s=t+1,...,t+60} [P(s)/P(t) − 1]. Event day t is excluded from the path.")
    lines.append("- Horizon 60 calendar days of BTC daily closes. No change after seeing results.")
    lines.append("")
    lines.append("## Features (frozen)")
    lines.append("")
    lines.append("### A. BTC percentiles (strictly expanding, s < t, min 365 finite observations)")
    lines.append("")
    for c in CRYPTO_PCTL:
        lines.append(f"- `{c}`")
    lines.append("")
    lines.append("Underlying raw series: ret_1d, ret_3d, ret_7d, dd_30 from trailing 30d high,")
    lines.append("20d stdev of daily returns, volume / prior-20d median volume (Binance-era volume only).")
    lines.append("2017-08-17 splice-day ret_1d is NaN (Bitstamp→Binance join).")
    lines.append("")
    lines.append("### B. Frozen macro 12w changes")
    lines.append("")
    for c in MACRO_FEATS:
        lines.append(f"- `{c}`")
    lines.append("")
    lines.append("Weekly Friday series from Phase 6A through 2023-12-29 (spliced, not rewritten).")
    lines.append("2024+ Fridays use the same sources as Phase 6H: Fed H.10 Nominal Broad Dollar,")
    lines.append("Fed H.15 2Y, Treasury TIPS par real 10Y, Yahoo `^IXIC`.")
    lines.append("")
    lines.append("### Daily alignment")
    lines.append("")
    lines.append("For BTC date t, attach the latest Friday-week macro row with `week <= t`")
    lines.append("(`merge_asof` backward). No future Friday is used. Typical lag is 0–6 days")
    lines.append("(Friday itself through the following Thursday). Lag > 10 days is treated as missing")
    lines.append("and later median-imputed on the training fold only.")
    lines.append("")
    lines.append("Friday levels themselves were as-of constructed from daily prints with a 7-day")
    lines.append("staleness cap at weekly construction time (Phase 6A/6H).")
    lines.append("")
    lines.append("## Models (frozen)")
    lines.append("")
    lines.append("| id | spec |")
    lines.append("|---|---|")
    lines.append("| M0 | expanding mature base rate |")
    lines.append("| M1 | Logistic L2 C=1.0 |")
    lines.append("| M2 | Probit (statsmodels) |")
    lines.append("| M3 | Elastic-net logistic l1_ratio=0.5 C=1.0 saga |")
    lines.append("| M4 | Additive natural cubic splines, df=4 per feature, Binomial GLM (patsy `cr` + statsmodels GLM). pygam was not installed. |")
    lines.append("| M5 | sklearn GradientBoostingClassifier n_estimators=100 max_depth=2 learning_rate=0.05 |")
    lines.append("")
    lines.append("Train-only median imputation. Train-only StandardScaler for M1–M3.")
    lines.append("M4/M5: impute only. Min train N=100. Mature labels: s <= t − 60 days.")
    lines.append(
        f"M0 is updated every prediction date. M1–M5 are refit every {REFIT_EVERY} eligible dates "
        "(coefficients held between refits). Training rows remain strictly mature. "
        "Complexity of each specification is unchanged."
    )
    lines.append("")
    lines.append("## Selection (development walk-forward only)")
    lines.append("")
    lines.append("A candidate must have BSS>0 **and** LogLoss < M0 **and** AUC>0.55.")
    lines.append("If several qualify, pick highest BSS. If none qualify: NONE.")
    lines.append("")
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "feature_spec.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_report(meta, metrics, preds_pack, df, selected, classes, calib, disp) -> None:
    def L(target, model, period):
        q = metrics[
            (metrics["target"] == target)
            & (metrics["model"] == model)
            & (metrics["period"] == period)
        ]
        return None if q.empty else q.iloc[0].to_dict()

    hdr = "| model | N | prev | brier | BSS | logloss | AUC | bal_acc |"
    sep = "|---|---:|---:|---:|---:|---:|---:|---:|"

    def line(target, model, period):
        r = L(target, model, period)
        if r is None:
            return f"| {model} | — |"
        return (
            f"| {model} | {int(r['N'])} | {pct(r['prevalence'], 3)} | {pct(r['brier'], 4)} | "
            f"{pct(r['brier_skill_vs_M0'], 3)} | {pct(r['log_loss'], 4)} | "
            f"{pct(r['auc'], 3)} | {pct(r['balanced_accuracy'], 3)} |"
        )

    lines = []
    lines.append("# Statistical model competition — Phase 2")
    lines.append("")
    lines.append(
        "Chronological 80/20 holdout. Expanding walk-forward on development. "
        "Not a trading strategy. Holdout was not used to choose features, targets, models, or thresholds."
    )
    lines.append("")
    lines.append("Brier = mean squared probability error (lower better).")
    lines.append("BSS = 1 − Brier_model / Brier_M0. BSS>0 means improvement on the expanding base rate.")
    lines.append("AUC = ranking probability, not accuracy.")
    lines.append("Log loss penalizes confident wrong probabilities (lower better).")
    lines.append("Balanced accuracy uses a frozen 0.5 cutoff (not optimized).")
    lines.append("")
    lines.append("## 1. Split")
    lines.append("")
    lines.append(f"Last development date: **{meta['split_date']}**. First holdout date: {meta['hold_start']}.")
    lines.append(f"Eligible N={meta['n_eligible']} (dev {meta['n_dev']} / holdout {meta['n_hold']}).")
    lines.append("Walk-forward N is slightly smaller than eligible development N because the first dates lack min-train=100 mature labels.")
    lines.append("")
    lines.append("## 2. Eligible counts by target")
    lines.append("")
    lines.append("| target | development N | holdout N | development prevalence | holdout prevalence |")
    lines.append("|---|---:|---:|---:|---:|")
    for tgt in TARGETS:
        d = L(tgt, "M0", "DEV_WF")
        h = L(tgt, "M0", "HOLDOUT")
        lines.append(
            f"| {tgt} | {int(d['N']) if d else 0} | {int(h['N']) if h else 0} | "
            f"{pct(d['prevalence'], 3) if d else 'NA'} | {pct(h['prevalence'], 3) if h else 'NA'} |"
        )
    lines.append("")

    for tgt in TARGETS:
        lines.append(f"## Development walk-forward — {tgt}")
        lines.append("")
        lines.append(hdr)
        lines.append(sep)
        for m in MODELS:
            tag = " ← selected" if selected[tgt] == m else ""
            lines.append(line(tgt, m, "DEV_WF").replace(f"| {m} |", f"| {m}{tag} |", 1))
        lines.append("")
        beat = []
        m0 = L(tgt, "M0", "DEV_WF")
        for m in ("M1", "M2", "M3", "M4", "M5"):
            r = L(tgt, m, "DEV_WF")
            if r and m0 and np.isfinite(r["brier_skill_vs_M0"]) and r["brier_skill_vs_M0"] > 0:
                beat.append(m)
        lines.append("Models with BSS>0 vs M0: " + (", ".join(beat) if beat else "none") + ".")
        lines.append(f"Selected candidate: **{selected[tgt] or 'NONE'}**.")
        lines.append("")

    lines.append("## Holdout (untouched 20%)")
    lines.append("")
    for tgt in TARGETS:
        lines.append(f"### {tgt} — class **{classes[tgt]}**")
        lines.append("")
        if selected[tgt] is None:
            lines.append("NO CANDIDATE. Holdout was not used to rescue a development failure.")
            lines.append("")
            continue
        lines.append(hdr)
        lines.append(sep)
        lines.append(line(tgt, "M0", "HOLDOUT"))
        lines.append(line(tgt, selected[tgt], "HOLDOUT"))
        nov = L(tgt, selected[tgt], "HOLDOUT_NONOVERLAP_SUMMARY")
        if nov is not None:
            lines.append(
                f"Non-overlap median BSS={pct(nov['bss_median'], 3)}; "
                f"min={pct(nov['bss_min'], 3)}; max={pct(nov['bss_max'], 3)}; "
                f"BSS>0: {int(nov['n_offsets_bss_gt0'] or 0)}/{int(nov['n_offsets'] or 0)} evaluable."
            )
        cal = calib[tgt]
        if cal:
            lines.append("")
            lines.append(
                f"Canonical logistic calibration on holdout: intercept={pct(cal.get('intercept'), 3)}, "
                f"slope={pct(cal.get('slope'), 3)} (ideal ~0 and ~1). Not OLS on probabilities."
            )
            if cal.get("bins"):
                lines.append("")
                lines.append("| bin | N | mean predicted | mean actual |")
                lines.append("|---|---:|---:|---:|")
                for b in cal["bins"]:
                    lines.append(f"| {b['bin']} | {b['N']} | {pct(b['mean_p'], 3)} | {pct(b['mean_y'], 3)} |")
        lines.append("")

    lines.append("## Answers")
    lines.append("")
    lines.append(f"1. Exact chronological 80/20 split date: last development date **{meta['split_date']}**.")
    ntxt = []
    for tgt in TARGETS:
        d = L(tgt, "M0", "DEV_WF")
        h = L(tgt, "M0", "HOLDOUT")
        ntxt.append(f"{tgt} dev N={int(d['N']) if d else 0}, holdout N={int(h['N']) if h else 0}")
    lines.append("2. Eligible observations: " + "; ".join(ntxt) + ".")
    beat_txt = []
    for tgt in TARGETS:
        m0 = L(tgt, "M0", "DEV_WF")
        names = []
        for m in ("M1", "M2", "M3", "M4", "M5"):
            r = L(tgt, m, "DEV_WF")
            if r and m0 and np.isfinite(r["brier_skill_vs_M0"]) and r["brier_skill_vs_M0"] > 0:
                names.append(m)
        beat_txt.append(f"{tgt}: {', '.join(names) if names else 'none'}")
    lines.append("3. Which models beat M0 during development (BSS>0)? " + " | ".join(beat_txt) + ".")
    lines.append(f"4. Candidate for UP_60D: **{selected['UP_60D'] or 'NONE'}**.")
    lines.append(f"5. Candidate for ADVERSE_60D: **{selected['ADVERSE_60D'] or 'NONE'}**.")
    hold_txt = []
    for tgt in TARGETS:
        if selected[tgt] is None:
            hold_txt.append(f"{tgt}: no candidate")
            continue
        r = L(tgt, selected[tgt], "HOLDOUT")
        hold_txt.append(
            f"{tgt} {selected[tgt]} BSS={pct(r['brier_skill_vs_M0'], 3) if r else 'NA'} "
            f"AUC={pct(r['auc'], 3) if r else 'NA'} class={classes[tgt]}"
        )
    lines.append("6. Untouched 20%: " + "; ".join(hold_txt) + ".")
    soph = []
    for tgt in TARGETS:
        m1 = L(tgt, "M1", "DEV_WF")
        others = []
        for m in ("M2", "M3", "M4", "M5"):
            r = L(tgt, m, "DEV_WF")
            if r and m1 and np.isfinite(r["brier"]) and np.isfinite(m1["brier"]) and r["brier"] < m1["brier"]:
                others.append(m)
        soph.append(
            f"{tgt}: "
            + (
                f"{', '.join(others)} beat M1 on Brier in development"
                if others
                else "no more sophisticated model beat M1 on Brier in development"
            )
        )
    lines.append("7. Did more sophisticated models improve on logistic (M1)? " + " | ".join(soph) + ".")
    cal_txt = []
    for tgt in TARGETS:
        if selected[tgt] is None:
            cal_txt.append(f"{tgt}: n/a")
            continue
        c = calib[tgt]
        cal_txt.append(f"{tgt} intercept={pct(c.get('intercept'), 3)} slope={pct(c.get('slope'), 3)}")
    lines.append("8. Probability calibration (holdout logistic, selected only): " + "; ".join(cal_txt) + ".")
    nov_txt = []
    for tgt in TARGETS:
        if selected[tgt] is None:
            nov_txt.append(f"{tgt}: n/a")
            continue
        nov = L(tgt, selected[tgt], "HOLDOUT_NONOVERLAP_SUMMARY")
        if nov is None:
            nov_txt.append(f"{tgt}: no offsets")
        else:
            ok = bool(np.isfinite(nov["bss_median"]) and nov["bss_median"] > 0)
            nov_txt.append(
                f"{tgt} median BSS={pct(nov['bss_median'], 3)} "
                f"({int(nov['n_offsets_bss_gt0'] or 0)}/{int(nov['n_offsets'] or 0)}) survive={ok}"
            )
    lines.append("9. Non-overlapping evaluation: " + "; ".join(nov_txt) + ".")
    lines.append(f"10. Continue toward a formal entry decision framework? **{disp}**")
    lines.append("")
    lines.append("## Decision")
    lines.append("")
    lines.append(f"**{disp}**")
    lines.append("")
    lines.append(
        "Predictive research only. Not ENTER/EXIT rules. Spec was not changed after seeing holdout numbers."
    )
    lines.append("")
    (RESULTS / "MODEL_COMPETITION.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    warnings.filterwarnings("ignore", category=RuntimeWarning)
    warnings.filterwarnings("ignore", category=ConvergenceWarning)
    RESULTS.mkdir(parents=True, exist_ok=True)
    btc = load_btc()
    log("Expanding BTC percentiles")
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
    need = CRYPTO_PCTL[:5] + ["UP_60D", "ADVERSE_60D"]
    elig = np.ones(len(df), dtype=bool)
    for c in need:
        elig &= np.isfinite(pd.to_numeric(df[c], errors="coerce").to_numpy(dtype=float))
    df["eligible"] = elig
    elig_df = df.loc[df["eligible"]].sort_values("date")
    n_el = len(elig_df)
    if n_el < 200:
        raise RuntimeError(f"Too few eligible days ({n_el}).")
    n_dev = int(np.floor(0.80 * n_el))
    split_date = pd.Timestamp(elig_df.iloc[n_dev - 1]["date"])
    hold_start = pd.Timestamp(elig_df.iloc[n_dev]["date"])
    meta = {
        "n_eligible": n_el,
        "n_dev": n_dev,
        "n_hold": n_el - n_dev,
        "split_date": split_date.date().isoformat(),
        "hold_start": hold_start.date().isoformat(),
        "last_eligible": pd.Timestamp(elig_df.iloc[-1]["date"]).date().isoformat(),
    }
    log(f"Split last-dev={meta['split_date']} first-hold={meta['hold_start']} N_dev={n_dev} N_hold={n_el - n_dev}")
    write_feature_spec(meta)
    log("wrote feature_spec.md (holdout still sealed)")

    dates = df["date"].to_numpy()
    X = df[FEATURES].to_numpy(dtype=float)
    eligible = df["eligible"].to_numpy()
    is_dev = eligible & (pd.to_datetime(df["date"]) <= split_date)
    is_hold = eligible & (pd.to_datetime(df["date"]) >= hold_start)
    y_map = {tgt: df[tgt].to_numpy(dtype=float) for tgt in TARGETS}
    log("Walk-forward (both targets)")
    preds = walkforward_both(X, y_map, dates, eligible)

    rows = []
    selected = {}
    classes = {}
    calib = {}
    for tgt in TARGETS:
        y = df[tgt].to_numpy(dtype=float)
        pmap = preds[tgt]
        dev_scores = {}
        for m in MODELS:
            st = score_block(y[is_dev], pmap[m][is_dev])
            dev_scores[m] = st
        m0b = dev_scores["M0"]["brier"]
        cand = select_candidate(dev_scores)
        selected[tgt] = cand
        log(f"{tgt} selected={cand}")
        for m in MODELS:
            rows.append(
                metric_row(
                    tgt,
                    m,
                    "DEV_WF",
                    dev_scores[m],
                    m0b,
                    selected="yes" if m == cand else "",
                )
            )
            nov = nonoverlap(y, pmap[m], pmap["M0"], is_dev)
            rows.append(
                metric_row(
                    tgt,
                    m,
                    "DEV_NONOVERLAP_SUMMARY",
                    {"N": nov["n_off"], "prevalence": np.nan, "brier": np.nan, "log_loss": np.nan, "auc": np.nan, "balanced_accuracy": np.nan},
                    np.nan,
                    bss_median=nov["bss_median"],
                    bss_min=nov["bss_min"],
                    bss_max=nov["bss_max"],
                    n_offsets_bss_gt0=nov["n_pos"],
                    n_offsets=nov["n_off"],
                    note=f"skipped_low_n={nov['n_low']}",
                )
            )
        hold_m0 = score_block(y[is_hold], pmap["M0"][is_hold])
        rows.append(metric_row(tgt, "M0", "HOLDOUT", hold_m0, hold_m0["brier"]))
        if cand is None:
            classes[tgt] = "NO CANDIDATE"
            calib[tgt] = {}
        else:
            hold_c = score_block(y[is_hold], pmap[cand][is_hold])
            rows.append(metric_row(tgt, cand, "HOLDOUT", hold_c, hold_m0["brier"], selected="yes"))
            nov_h = nonoverlap(y, pmap[cand], pmap["M0"], is_hold)
            rows.append(
                metric_row(
                    tgt,
                    cand,
                    "HOLDOUT_NONOVERLAP_SUMMARY",
                    {"N": nov_h["n_off"], "prevalence": np.nan, "brier": np.nan, "log_loss": np.nan, "auc": np.nan, "balanced_accuracy": np.nan},
                    np.nan,
                    bss_median=nov_h["bss_median"],
                    bss_min=nov_h["bss_min"],
                    bss_max=nov_h["bss_max"],
                    n_offsets_bss_gt0=nov_h["n_pos"],
                    n_offsets=nov_h["n_off"],
                    selected="yes",
                    note=f"skipped_low_n={nov_h['n_low']}",
                )
            )
            classes[tgt] = classify_holdout(hold_c, hold_m0, nov_h)
            calib[tgt] = logit_calibration(y[is_hold], pmap[cand][is_hold])
            calib[tgt]["bins"] = reliability_table(y[is_hold], pmap[cand][is_hold])

    n_val = sum(1 for v in classes.values() if v == "VALIDATED")
    n_mix = sum(1 for v in classes.values() if v == "MIXED")
    if n_val >= 1:
        disp = "PROMISING"
    elif n_mix >= 1:
        disp = "WEAK"
    else:
        disp = "NO EDGE"

    metrics = pd.DataFrame(rows)
    metrics.to_csv(RESULTS / "model_metrics.csv", index=False)
    write_report(meta, metrics, preds, df, selected, classes, calib, disp)
    log(f"Disposition {disp}")
    log(f"wrote {RESULTS / 'model_metrics.csv'}")
    log(f"wrote {RESULTS / 'MODEL_COMPETITION.md'}")


if __name__ == "__main__":
    main()
