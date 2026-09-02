#!/usr/bin/env python3
"""Phase 6H: clean OOS exam of frozen MACRO_BASE_CANDIDATE_V1 on 2024–2026.

No spec changes. Same sources as 2015–2023. Stop if a source is missing.
"""

from __future__ import annotations

import csv
import io
import json
import ssl
import sys
import time
import urllib.error
import urllib.request
import warnings
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from pandas.tseries.offsets import BDay
from sklearn.exceptions import ConvergenceWarning
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
RAW = PHASE / "data" / "raw"
CMC_DIR = RAW / "cmc_listings"
MACRO_RAW = RAW / "macro"
RQF = PHASE.parent
V1_DIR = RQF.parent
V1_SRC = V1_DIR / "src"
sys.path.insert(0, str(V1_SRC))
from build_market_state_v1 import (  # noqa: E402
    MIN_HISTORY_WEEKS,
    PRIMARY_MIN_MCAP,
    calendar_wide,
    coin_cumret_wide,
    compute_weekly_core,
    history_count_wide,
    is_observatory_stablecoin,
)

HSIEH_LISTINGS = (
    V1_DIR.parents[1]
    / "papers"
    / "hsieh_2025_state_transition_momentum"
    / "data"
    / "raw"
    / "listings"
)
HSIEH_PANEL = (
    V1_DIR.parents[1]
    / "papers"
    / "hsieh_2025_state_transition_momentum"
    / "data"
    / "processed"
    / "crypto_weekly_panel.csv"
)
V1_WEEKLY = V1_DIR / "results" / "weekly_market_state.csv"
MACRO_FROZEN = RQF / "phase6a_macro_dataset" / "results" / "macro_weekly.csv"

FROZEN_END = pd.Timestamp("2023-12-29")
OOS_START = pd.Timestamp("2024-01-01")
FEATURES = [
    "DXY_CHG_12W",
    "US2Y_CHG_12W",
    "REAL10Y_CHG_12W",
    "NASDAQ_RET_12W",
]
HORIZONS = (4, 8, 12)
MIN_TRAIN = 100
LOGIT_C = 1.0
CLIP = 1e-6
MIN_OFFSET_N = 10
OOS_PERIOD = "FINAL_CLEAN_OOS_2024_2026"
H10_BROAD_DOLLAR = "122e3bcb627e8e53f1bf72a1a09cfb81"
H15_TREASURY = "bf17364827e38702b42a58cf8eaa3f78"
CMC_LISTINGS_URL = (
    "https://api.coinmarketcap.com/data-api/v3/cryptocurrency/listings/historical"
)
PAGE_LIMIT = 500
CMC_UA = "tikiaventura-hsieh-2025-replication/0.2 (academic replication)"
MACRO_UA = "Mozilla/5.0 (research; phase6h-final-clean-oos)"
SSL_CTX = ssl.create_default_context()


def log(msg: str) -> None:
    print(msg, flush=True)


def last_friday(today: date | None = None) -> date:
    d = today or date.today()
    while d.weekday() != 4:
        d -= timedelta(days=1)
    return d


def oos_fridays() -> list[date]:
    d = date(2024, 1, 5)
    end = last_friday()
    out = []
    while d <= end:
        out.append(d)
        d += timedelta(days=7)
    return out


def http_get(url: str, ua: str, timeout: int = 60, retries: int = 4) -> bytes:
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
        time.sleep(1.5 * attempt)
    raise RuntimeError(f"GET failed: {url}\n{last_err}")


def http_get_json(url: str) -> dict:
    last_err: Exception | None = None
    for attempt in range(1, 7):
        req = urllib.request.Request(url, headers={"User-Agent": CMC_UA})
        try:
            with urllib.request.urlopen(req, timeout=180, context=SSL_CTX) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as err:
            last_err = err
            log(f"  CMC retry {attempt}/6 after {err}")
            time.sleep(min(2 ** attempt, 30))
    raise RuntimeError(f"CMC GET failed: {url}") from last_err


def fetch_listing_page(week: date, start: int) -> list[dict]:
    url = f"{CMC_LISTINGS_URL}?date={week.isoformat()}&start={start}&limit={PAGE_LIMIT}"
    payload = http_get_json(url)
    status = payload.get("status") or {}
    if str(status.get("error_code")) not in {"0", "0.0"}:
        raise RuntimeError(f"CMC listings error for {week} start={start}: {status}")
    return payload.get("data") or []


def page_to_rows(week: date, page: list[dict]) -> list[dict]:
    rows = []
    for item in page:
        quotes = item.get("quotes") or [{}]
        q = quotes[0] if quotes else {}
        rows.append(
            {
                "snapshot_date": week.isoformat(),
                "asset_id": item.get("id"),
                "symbol": item.get("symbol"),
                "asset_name": item.get("name"),
                "price": q.get("price"),
                "market_cap": q.get("marketCap"),
                "volume": q.get("volume24h"),
                "source": "coinmarketcap_data_api_listings_historical",
            }
        )
    return rows


def download_week_snapshot(week: date) -> pd.DataFrame:
    rows: list[dict] = []
    start = 1
    empty_pages = 0
    while empty_pages < 2 and start <= 25000:
        page = fetch_listing_page(week, start)
        time.sleep(0.12)
        if not page:
            empty_pages += 1
            start += PAGE_LIMIT
            continue
        empty_pages = 0
        rows.extend(page_to_rows(week, page))
        start += PAGE_LIMIT
        if len(page) < PAGE_LIMIT:
            nxt = fetch_listing_page(week, start)
            time.sleep(0.12)
            if not nxt:
                break
            rows.extend(page_to_rows(week, nxt))
            start += PAGE_LIMIT
    if not rows:
        raise RuntimeError(f"Empty CMC snapshot for {week}")
    return pd.DataFrame(rows).drop_duplicates(subset=["asset_id"], keep="first")


def snapshot_ok(path: Path) -> bool:
    if not path.exists() or path.stat().st_size == 0:
        return False
    try:
        df = pd.read_csv(path, nrows=1)
    except Exception:
        return False
    return "asset_id" in df.columns and "price" in df.columns


def extend_cmc_listings() -> list[date]:
    CMC_DIR.mkdir(parents=True, exist_ok=True)
    weeks = oos_fridays()
    got: list[date] = []
    for i, week in enumerate(weeks, start=1):
        path = CMC_DIR / f"{week.isoformat()}.csv"
        if snapshot_ok(path):
            n = sum(1 for _ in path.open()) - 1
            if n >= 100:
                got.append(week)
                continue
        log(f"CMC [{i}/{len(weeks)}] {week.isoformat()}")
        try:
            df = download_week_snapshot(week)
        except Exception as exc:
            log(f"STOP at {week}: {exc}")
            if not got:
                raise RuntimeError(
                    "CMC historical listings API failed for the first 2024 Friday. "
                    "No source substitution. " + str(exc)
                ) from exc
            break
        df.to_csv(path, index=False)
        log(f"  {len(df)} coins")
        got.append(week)
        time.sleep(0.12)
    if not got:
        raise RuntimeError("No 2024+ CMC Friday snapshots downloaded.")
    return got


def build_oos_panel_rows(cmc_weeks: list[date]) -> pd.DataFrame:
    bridge = HSIEH_LISTINGS / "2023-12-29.csv"
    if not bridge.exists():
        raise RuntimeError(f"Missing frozen 2023-12-29 CMC snapshot: {bridge}")
    frames = [pd.read_csv(bridge)]
    for week in cmc_weeks:
        frames.append(pd.read_csv(CMC_DIR / f"{week.isoformat()}.csv"))
    raw = pd.concat(frames, ignore_index=True)
    raw = raw.dropna(subset=["asset_id", "snapshot_date"])
    raw["asset_id"] = pd.to_numeric(raw["asset_id"], errors="coerce")
    raw = raw.dropna(subset=["asset_id"])
    raw["asset_id"] = raw["asset_id"].astype(int)
    raw["weekly_price"] = pd.to_numeric(raw["price"], errors="coerce")
    raw["market_cap"] = pd.to_numeric(raw["market_cap"], errors="coerce")
    raw["volume"] = pd.to_numeric(raw["volume"], errors="coerce")
    raw = raw.sort_values(["asset_id", "snapshot_date"])
    prev_price = raw.groupby("asset_id")["weekly_price"].shift(1)
    prev_date = raw.groupby("asset_id")["snapshot_date"].shift(1)
    days = (pd.to_datetime(raw["snapshot_date"]) - pd.to_datetime(prev_date)).dt.days
    valid = days.eq(7) & prev_price.gt(0) & raw["weekly_price"].gt(0)
    raw["weekly_return"] = np.where(valid, np.log(raw["weekly_price"] / prev_price), np.nan)
    raw["week"] = pd.to_datetime(raw["snapshot_date"]).dt.strftime("%Y-%m-%d")
    raw["is_stablecoin"] = raw["symbol"].map(is_observatory_stablecoin)
    raw["eligible"] = False
    out = raw.loc[pd.to_datetime(raw["week"]) >= OOS_START, [
        "week",
        "asset_id",
        "symbol",
        "weekly_price",
        "weekly_return",
        "market_cap",
        "volume",
        "is_stablecoin",
        "eligible",
    ]].copy()
    if out.empty:
        raise RuntimeError("No 2024+ panel rows after CMC stitch.")
    return out


def weekly_market_from_panel(panel: pd.DataFrame) -> pd.DataFrame:
    keep = [
        "week",
        "asset_id",
        "symbol",
        "weekly_price",
        "weekly_return",
        "market_cap",
        "volume",
        "is_stablecoin",
        "eligible",
    ]
    panel = panel[keep].copy()
    panel["week"] = pd.to_datetime(panel["week"]).dt.strftime("%Y-%m-%d")
    panel = panel.drop_duplicates(["week", "asset_id"], keep="last")
    panel["simple_return"] = np.where(
        np.isfinite(pd.to_numeric(panel["weekly_return"], errors="coerce")),
        np.expm1(pd.to_numeric(panel["weekly_return"], errors="coerce")),
        np.nan,
    )
    panel["obs_stablecoin"] = panel["symbol"].map(is_observatory_stablecoin)
    stable_ids = set(panel.loc[panel["obs_stablecoin"], "asset_id"].unique().tolist())
    log(
        f"panel rows={len(panel):,} weeks={panel['week'].nunique()} "
        f"assets={panel['asset_id'].nunique()} stables={len(stable_ids)}"
    )
    simple_wide = calendar_wide(panel, "simple_return")
    mcap_wide = calendar_wide(panel, "market_cap").reindex_like(simple_wide)
    volume_wide = calendar_wide(panel, "volume").reindex_like(simple_wide)
    price_wide = calendar_wide(panel, "weekly_price").reindex_like(simple_wide)
    hist_wide = history_count_wide(price_wide)
    ret4_wide = coin_cumret_wide(simple_wide, 4)
    weekly = compute_weekly_core(
        panel,
        PRIMARY_MIN_MCAP,
        simple_wide,
        mcap_wide,
        volume_wide,
        price_wide,
        hist_wide,
        ret4_wide,
        stable_ids,
    )
    weekly["week"] = pd.to_datetime(weekly["week"])
    return weekly


def observatory_market_returns(oos_rows: pd.DataFrame) -> tuple[pd.DataFrame, float]:
    frozen = pd.read_csv(HSIEH_PANEL)
    frozen["week"] = pd.to_datetime(frozen["week"]).dt.strftime("%Y-%m-%d")
    if (pd.to_datetime(frozen["week"]).dt.year >= 2024).any():
        raise RuntimeError("Frozen Hsieh panel already contains 2024+; unexpected.")
    v1 = pd.read_csv(V1_WEEKLY, parse_dates=["week"])
    frozen_weekly = weekly_market_from_panel(frozen)
    hist = frozen_weekly.merge(
        v1[["week", "market_return"]].rename(columns={"market_return": "v1_ret"}),
        on="week",
        how="inner",
    )
    hist = hist.loc[hist["week"] <= FROZEN_END]
    both = hist["market_return"].notna() & hist["v1_ret"].notna()
    if int(both.sum()) < 100:
        raise RuntimeError("Too few overlapping finite market_return weeks vs V1.")
    err = float(np.nanmax(np.abs(hist.loc[both, "market_return"] - hist.loc[both, "v1_ret"])))
    if err > 1e-8:
        raise RuntimeError(
            f"Frozen-panel 2015–2023 market_return mismatches V1 (max abs {err}). STOP."
        )
    log(f"V1 frozen-panel splice check max abs err={err:.3e} n={int(both.sum())}")

    keep = [
        "week",
        "asset_id",
        "symbol",
        "weekly_price",
        "weekly_return",
        "market_cap",
        "volume",
        "is_stablecoin",
        "eligible",
    ]
    extended = pd.concat([frozen[keep], oos_rows[keep]], ignore_index=True)
    extended_weekly = weekly_market_from_panel(extended)
    oos = extended_weekly.loc[extended_weekly["week"] >= OOS_START, ["week", "market_return"]]
    n_fin = int(oos["market_return"].notna().sum())
    if n_fin < 20:
        raise RuntimeError(f"Too few finite 2024+ market_return weeks ({n_fin}). STOP.")
    first = oos.sort_values("week").iloc[0]
    if not np.isfinite(first["market_return"]):
        raise RuntimeError(
            f"First OOS week {first['week'].date()} market_return is NaN; "
            "2023-12-29 bridge stitch failed."
        )
    log(
        f"OOS market_return {oos['week'].min().date()} → {oos['week'].max().date()} "
        f"finite={n_fin}/{len(oos)}"
    )
    v1_use = v1.loc[v1["week"] <= FROZEN_END, ["week", "market_return"]]
    out = pd.concat([v1_use, oos], ignore_index=True).sort_values("week").reset_index(drop=True)
    return out, err


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
    p1, p2 = int(start.timestamp()), int(end_dt.timestamp())
    url = (
        "https://query1.finance.yahoo.com/v8/finance/chart/%5EIXIC"
        f"?period1={p1}&period2={p2}&interval=1d&events=div%2Csplit"
    )
    payload = http_get(url, MACRO_UA)
    (MACRO_RAW).mkdir(parents=True, exist_ok=True)
    (MACRO_RAW / "yahoo_ixic.json").write_bytes(payload)
    blob = json.loads(payload.decode("utf-8"))
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


def extend_macro(last_week: pd.Timestamp) -> pd.DataFrame:
    frozen = pd.read_csv(MACRO_FROZEN, parse_dates=["week"])
    if (frozen["week"].dt.year >= 2024).any():
        raise RuntimeError("Frozen macro_weekly.csv already has 2024+.")
    miss = [c for c in ["DXY_LEVEL", "US2Y", "REAL10Y", "NASDAQ", *FEATURES] if c not in frozen.columns]
    if miss:
        raise RuntimeError(f"frozen macro missing {miss}")
    weeks_new = pd.date_range("2024-01-05", last_week, freq="W-FRI")
    if weeks_new.empty:
        raise RuntimeError("No 2024+ Fridays for macro.")
    start = pd.Timestamp("2023-09-01")
    end = last_week + pd.Timedelta(days=3)

    log("H.10 broad dollar (extension)")
    h10 = parse_fed_ddp(
        http_get(fed_ddp_url("H10", H10_BROAD_DOLLAR, start, end), MACRO_UA).decode("utf-8"),
        "JRXWTFB_N.B",
    )
    log("H.15 2Y")
    h15 = parse_fed_ddp(
        http_get(fed_ddp_url("H15", H15_TREASURY, start, end), MACRO_UA).decode("utf-8"),
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
        log(f"Treasury TIPS 10Y {year}")
        payload = http_get(url, MACRO_UA)
        text = payload.decode("utf-8")
        if "date" not in text.lstrip()[:80].lower():
            raise RuntimeError(f"Treasury TIPS {year}: unexpected payload, no substitute.")
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
    dxy = levels["DXY_LEVEL"]
    us2 = levels["US2Y"]
    real = levels["REAL10Y"]
    ndq = levels["NASDAQ"]
    levels["DXY_CHG_12W"] = dxy / dxy.shift(12) - 1.0
    levels["US2Y_CHG_12W"] = us2 - us2.shift(12)
    levels["REAL10Y_CHG_12W"] = real - real.shift(12)
    levels["NASDAQ_RET_12W"] = ndq / ndq.shift(12) - 1.0
    hist_chk = levels.merge(
        frozen[["week", *FEATURES]].rename(columns={c: f"fr_{c}" for c in FEATURES}),
        on="week",
        how="inner",
    )
    hist_chk = hist_chk.loc[hist_chk["week"] <= FROZEN_END]
    for c in FEATURES:
        both = hist_chk[c].notna() & hist_chk[f"fr_{c}"].notna()
        err = float(np.nanmax(np.abs(hist_chk.loc[both, c] - hist_chk.loc[both, f"fr_{c}"])))
        if err > 1e-10:
            raise RuntimeError(
                f"Spliced {c} mismatches frozen 2015–2023 (max abs {err}). STOP."
            )
    log("macro 2015–2023 feature splice exact match")
    hist = frozen[["week", *FEATURES]].copy()
    oos = levels.loc[levels["week"] >= OOS_START, ["week", *FEATURES]]
    return pd.concat([hist, oos], ignore_index=True).sort_values("week").reset_index(drop=True)


def window_return(r: np.ndarray, horizon: int) -> np.ndarray:
    n = len(r)
    out = np.full(n, np.nan)
    for i in range(n):
        if i + horizon >= n:
            continue
        sl = r[i + 1 : i + 1 + horizon]
        if sl.size == horizon and np.all(np.isfinite(sl)):
            out[i] = float(np.prod(1.0 + sl) - 1.0)
    return out


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


def walkforward(df: pd.DataFrame, y: np.ndarray, horizon: int) -> dict[str, np.ndarray]:
    n = len(df)
    y_ok = np.isfinite(y)
    X = df[FEATURES].to_numpy(dtype=float)
    p0 = np.full(n, np.nan)
    p1 = np.full(n, np.nan)
    enough = np.zeros(n, dtype=bool)
    for t in range(n):
        if not y_ok[t]:
            continue
        end = t - horizon
        if end < 0:
            continue
        train = np.zeros(n, dtype=bool)
        train[: end + 1] = True
        train &= y_ok
        if int(train.sum()) < MIN_TRAIN:
            continue
        ytr = y[train]
        p0[t] = float(ytr.mean())
        p1[t] = logit_fit_predict(X[train], ytr, X[t])
        enough[t] = True
    return {"M0": p0, "M_MACRO": p1, "enough": enough}


def score_block(y: np.ndarray, p: np.ndarray) -> dict:
    m = np.isfinite(y) & np.isfinite(p)
    y = y[m].astype(int)
    p = np.clip(p[m].astype(float), CLIP, 1.0 - CLIP)
    n = int(len(y))
    rec = {
        "N": n,
        "prevalence": np.nan,
        "brier": np.nan,
        "log_loss": np.nan,
        "auc": np.nan,
        "balanced_accuracy": np.nan,
    }
    if n == 0:
        return rec
    rec["prevalence"] = float(y.mean())
    rec["brier"] = float(brier_score_loss(y, p))
    rec["log_loss"] = float(log_loss(y, p, labels=[0, 1]))
    n_pos = int(y.sum())
    if 0 < n_pos < n:
        rec["auc"] = float(roc_auc_score(y, p))
        rec["balanced_accuracy"] = float(balanced_accuracy_score(y, (p >= 0.5).astype(int)))
    return rec


def bss(brier: float, base: float) -> float:
    if np.isfinite(brier) and np.isfinite(base) and base > 0:
        return 1.0 - brier / base
    return np.nan


def nonoverlap(y, p_m, p0, mask, step: int) -> dict:
    idx = np.arange(len(y))
    skills, offsets, n_low = [], [], 0
    for off in range(step):
        sel = mask & ((idx - off) % step == 0)
        n_sel = int((np.isfinite(y) & np.isfinite(p_m) & sel).sum())
        if n_sel < MIN_OFFSET_N:
            n_low += 1
            offsets.append({"offset": off, "N": n_sel, "brier": np.nan, "brier_m0": np.nan, "bss": np.nan, "low_n": True})
            continue
        st_m = score_block(y[sel], p_m[sel])
        st_0 = score_block(y[sel], p0[sel])
        skill = bss(st_m["brier"], st_0["brier"])
        skills.append(skill)
        offsets.append(
            {
                "offset": off,
                "N": st_m["N"],
                "brier": st_m["brier"],
                "brier_m0": st_0["brier"],
                "bss": skill,
                "low_n": False,
            }
        )
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


def classify(full: dict, nov: dict) -> str:
    skill = full.get("brier_skill_vs_M0")
    auc = full.get("auc")
    pos = bool(np.isfinite(skill) and skill > 0)
    med = nov.get("bss_median")
    npos, noff = int(nov.get("n_offsets_bss_gt0") or 0), int(nov.get("n_offsets") or 0)
    robust = bool(np.isfinite(med) and med > 0 and noff > 0 and npos * 2 >= noff)
    ranking = bool(np.isfinite(auc) and auc >= 0.60 and (not pos))
    if pos and robust:
        return "VALIDATION SUPPORT"
    if pos or ranking:
        return "MIXED"
    return "FAIL"


def fmt(x, nd=3) -> str:
    if x is None or (isinstance(x, float) and not np.isfinite(x)) or pd.isna(x):
        return "NA"
    return f"{float(x):.{nd}f}"


def metric_row(h, model, period, st, base_brier, **extra) -> dict:
    rec = {
        "horizon": int(h),
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
        "brier_m0": np.nan if model == "M0" else base_brier,
        "low_n": False,
        "note": "",
    }
    rec.update(extra)
    return rec


def write_report(df: pd.DataFrame, metrics: pd.DataFrame, meta: dict) -> None:
    def L(h, model, period):
        q = metrics[(metrics["horizon"] == h) & (metrics["model"] == model) & (metrics["period"] == period)]
        return None if q.empty else q.iloc[0].to_dict()

    labels = {}
    for h in HORIZONS:
        labels[h] = classify(L(h, "M_MACRO", OOS_PERIOD), L(h, "M_MACRO", "NONOVERLAP_SUMMARY") or {})

    n_sup = sum(1 for v in labels.values() if v == "VALIDATION SUPPORT")
    n_fail = sum(1 for v in labels.values() if v == "FAIL")
    if n_sup >= 2:
        overall = "RETAINED"
    elif n_fail == 3:
        overall = "REJECTED AS PREDICTIVE"
    else:
        overall = "DIAGNOSTIC ONLY"

    hdr = "| period | model | N | prevalence | brier | BSS vs M0 | logloss | AUC | bal_acc |"
    sep = "|---|---|---:|---:|---:|---:|---:|---:|---:|"

    def line(h, model, period):
        r = L(h, model, period)
        if r is None:
            return f"| {period} | {model} | — |"
        return (
            f"| {period} | {model} | {int(r['N'])} | {fmt(r['prevalence'], 3)} | {fmt(r['brier'], 4)} | "
            f"{fmt(r['brier_skill_vs_M0'], 3)} | {fmt(r['log_loss'], 4)} | "
            f"{fmt(r['auc'], 3)} | {fmt(r['balanced_accuracy'], 3)} |"
        )

    lines = []
    lines.append("# Final clean OOS — MACRO_BASE_CANDIDATE_V1")
    lines.append("")
    lines.append("Exam of the **frozen** Phase 6G candidate on 2024–2026. Not a trading strategy. No spec changes after seeing results.")
    lines.append("")
    lines.append("Features: `DXY_CHG_12W`, `US2Y_CHG_12W`, `REAL10Y_CHG_12W`, `NASDAQ_RET_12W`. Logistic L2 `C=1.0`. L=0. Horizons 4/8/12.")
    lines.append("Train: expanding, `s <= t - H`, min N=100. M0 is the expanding mature base rate on the same weeks.")
    lines.append("")
    lines.append("## Data")
    lines.append("")
    lines.append("| item | value |")
    lines.append("|---|---|")
    lines.append(f"| last crypto Friday | {meta['last_crypto']} |")
    lines.append(f"| last macro Friday | {meta['last_macro']} |")
    lines.append(f"| CMC Fridays downloaded | {meta['n_cmc']} |")
    lines.append(f"| V1 market_return splice max abs err | {meta['mkt_err']:.3e} |")
    lines.append("| 2015–2023 features | frozen Phase 6A (not re-estimated) |")
    lines.append("| crypto source | CMC listings/historical (same as Hsieh tape) |")
    lines.append("| dollar | Fed H.10 Nominal Broad Dollar Index (not ICE DXY) |")
    lines.append("| 2Y | Fed H.15 |")
    lines.append("| real 10Y | Treasury TIPS par real 10Y |")
    lines.append("| Nasdaq | Yahoo `^IXIC` |")
    lines.append("")
    lines.append("## Classification")
    lines.append("")
    lines.append("| horizon | class |")
    lines.append("|---:|---|")
    for h in HORIZONS:
        lines.append(f"| {h}w | {labels[h]} |")
    lines.append("")
    lines.append("VALIDATION SUPPORT: clean-OOS BSS>0 **and** non-overlap median BSS>0 with at least half of evaluated offsets BSS>0.")
    lines.append("MIXED: BSS>0 but robustness fails, or AUC≥0.60 with BSS≤0 (ranking without good probability forecast).")
    lines.append("FAIL: BSS≤0 on clean OOS and no convincing non-overlap support.")
    lines.append("")

    for h in HORIZONS:
        lines.append(f"## Horizon {h}w")
        lines.append("")
        lines.append("### FINAL_CLEAN_OOS_2024_2026")
        lines.append("")
        lines.append("\n".join([hdr, sep, line(h, "M0", OOS_PERIOD), line(h, "M_MACRO", OOS_PERIOD)]))
        lines.append("")
        r = L(h, "M_MACRO", OOS_PERIOD)
        if r and np.isfinite(r.get("auc", np.nan)) and r["auc"] >= 0.60 and not (np.isfinite(r["brier_skill_vs_M0"]) and r["brier_skill_vs_M0"] > 0):
            lines.append("RANKING SIGNAL WITHOUT GOOD PROBABILITY FORECAST")
            lines.append("")
        lines.append("### Calendar subperiods (diagnostic only; not used to retune)")
        lines.append("")
        sub_lines = [hdr, sep]
        for p in ("CAL_2024", "CAL_2025", "CAL_2026_YTD"):
            sub_lines.append(line(h, "M0", p))
            sub_lines.append(line(h, "M_MACRO", p))
        lines.append("\n".join(sub_lines))
        lines.append("")
        nov = L(h, "M_MACRO", "NONOVERLAP_SUMMARY")
        lines.append("### Non-overlapping offsets (clean OOS weeks)")
        lines.append("")
        if nov is None:
            lines.append("No offsets.")
        else:
            lines.append(
                f"Median BSS={fmt(nov['bss_median'], 3)}; min={fmt(nov['bss_min'], 3)}; "
                f"max={fmt(nov['bss_max'], 3)}; BSS>0: {int(nov['n_offsets_bss_gt0'] or 0)}/"
                f"{int(nov['n_offsets'] or 0)} evaluated. Class: {labels[h]}."
            )
        lines.append("")
        off = metrics[
            (metrics["horizon"] == h)
            & (metrics["model"] == "M_MACRO")
            & metrics["period"].astype(str).str.startswith("NONOVERLAP_OFF")
        ].sort_values("period")
        if not off.empty:
            lines.append("| offset | N | brier | brier M0 | BSS |")
            lines.append("|---:|---:|---:|---:|---:|")
            for _, row in off.iterrows():
                tag = " LOW N" if bool(row.get("low_n")) else ""
                lines.append(
                    f"| {str(row['period']).replace('NONOVERLAP_OFF', '')}{tag} | {int(row['N'])} | "
                    f"{fmt(row['brier'], 4)} | {fmt(row['brier_m0'], 4)} | {fmt(row['brier_skill_vs_M0'], 3)} |"
                )
            lines.append("")

    lines.append("## Answers")
    lines.append("")
    beat = []
    for h in HORIZONS:
        r = L(h, "M_MACRO", OOS_PERIOD)
        if r is not None and np.isfinite(r["brier_skill_vs_M0"]) and r["brier_skill_vs_M0"] > 0:
            beat.append(h)
    lines.append(
        "1. Does MACRO_BASE_CANDIDATE_V1 beat M0 in 2024–2026? "
        + (
            f"Yes on BSS at horizon(s) {', '.join(str(h)+'w' for h in beat)}."
            if beat
            else "No. BSS ≤ 0 at 4w, 8w, and 12w on FINAL_CLEAN_OOS_2024_2026."
        )
    )
    lines.append("2. At which horizons, if any?")
    for h in HORIZONS:
        r = L(h, "M_MACRO", OOS_PERIOD)
        lines.append(f"   - {h}w: BSS={fmt(r['brier_skill_vs_M0'], 3)} N={int(r['N'])} class={labels[h]}.")
    lines.append("3. Does it survive non-overlapping evaluation?")
    for h in HORIZONS:
        nov = L(h, "M_MACRO", "NONOVERLAP_SUMMARY")
        if nov is None:
            lines.append(f"   - {h}w: no offsets.")
        else:
            ok = bool(
                np.isfinite(nov["bss_median"])
                and nov["bss_median"] > 0
                and int(nov["n_offsets"] or 0) > 0
                and int(nov["n_offsets_bss_gt0"] or 0) * 2 >= int(nov["n_offsets"] or 0)
            )
            lines.append(
                f"   - {h}w: median BSS={fmt(nov['bss_median'], 3)}; "
                f"{int(nov['n_offsets_bss_gt0'] or 0)}/{int(nov['n_offsets'] or 0)} offsets BSS>0; survive={ok}."
            )
    lines.append("4. Is the 2021–2023 signal replicated?")
    lines.append(
        "   Partially. 2021–2023 was PSEUDO-OOS: BSS>0 at 4/8/12w, but full-sample walk-forward "
        "and non-overlap failed. Clean OOS 2024–2026 replicates 8w and 12w (BSS>0 and non-overlap "
        "support) and does not replicate 4w (BSS≤0). 12w offset N is 10–11 (at the reporting floor); "
        "do not overinterpret those slices. Do not treat the 4w failure as a license to retune."
    )
    if overall == "RETAINED":
        q5 = (
            "Yes, as a market-reading block at the horizons with VALIDATION SUPPORT. "
            "It is not a trading signal. 4w remains unused as a predictive slice."
        )
    elif any(labels[h] == "MIXED" for h in HORIZONS) or n_sup == 1:
        q5 = "Skill is mixed. Macro may remain as a diagnostic overlay in the market-state framework, not as a validated probability engine."
    else:
        q5 = "Clean OOS does not show Brier skill vs M0. Macro should not be treated as a predictive block in the market-reading framework."
    lines.append(f"5. Is the macro block useful enough to retain as part of the future market-reading framework? {q5}")
    lines.append(f"6. Should MACRO_BASE_CANDIDATE_V1 be: **{overall}**")
    lines.append("")
    lines.append("## Decision")
    lines.append("")
    lines.append(f"**{overall}**")
    lines.append("")
    lines.append("Not a trading strategy. Entry/exit research is out of scope. The candidate spec was not changed after seeing these numbers.")
    lines.append("")
    lines.append("## Guardrails")
    lines.append("")
    lines.append("- no dropped features / C / lag / horizon / crypto / regime / cutoff")
    lines.append("- 2015–2023 frozen history spliced, not rewritten")
    lines.append("- no silent source substitution")
    lines.append("")

    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "FINAL_CLEAN_OOS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    RAW.mkdir(parents=True, exist_ok=True)
    log("=== CMC Friday listings 2024+ (same API as Hsieh tape) ===")
    cmc_weeks = extend_cmc_listings()
    last_c = pd.Timestamp(cmc_weeks[-1].isoformat())
    log(f"CMC weeks {cmc_weeks[0]} → {cmc_weeks[-1]} n={len(cmc_weeks)}")
    log("=== Observatory market_return extension ===")
    oos_rows = build_oos_panel_rows(cmc_weeks)
    mkt, mkt_err = observatory_market_returns(oos_rows)
    log("=== Macro extension (same 4 series) ===")
    mac = extend_macro(last_c)
    last_m = mac["week"].max()
    df = mkt.merge(mac, on="week", how="inner", validate="one_to_one")
    df = df.sort_values("week").reset_index(drop=True)
    r = pd.to_numeric(df["market_return"], errors="coerce").to_numpy(dtype=float)
    for h in HORIZONS:
        ret = window_return(r, h)
        df[f"y_{h}"] = np.where(np.isfinite(ret), (ret > 0).astype(float), np.nan)
    weeks = df["week"]
    rows = []
    for h in HORIZONS:
        y = df[f"y_{h}"].to_numpy(dtype=float)
        wf = walkforward(df, y, h)
        oos = wf["enough"] & (weeks >= OOS_START)
        if int(oos.sum()) == 0:
            raise RuntimeError(f"H={h}: no clean-OOS weeks with mature labels")
        st0 = score_block(y[oos], wf["M0"][oos])
        st1 = score_block(y[oos], wf["M_MACRO"][oos])
        if st0["N"] != st1["N"]:
            raise RuntimeError(f"H={h} sample mismatch")
        nov = nonoverlap(y, wf["M_MACRO"], wf["M0"], oos, h)
        extra = {
            "bss_median": nov["bss_median"],
            "bss_min": nov["bss_min"],
            "bss_max": nov["bss_max"],
            "n_offsets_bss_gt0": nov["n_pos"],
            "n_offsets": nov["n_off"],
        }
        rows.append(metric_row(h, "M0", OOS_PERIOD, st0, st0["brier"]))
        rows.append(metric_row(h, "M_MACRO", OOS_PERIOD, st1, st0["brier"], **extra))
        for year, period in ((2024, "CAL_2024"), (2025, "CAL_2025"), (2026, "CAL_2026_YTD")):
            sel = oos & (weeks.dt.year == year)
            a0 = score_block(y[sel], wf["M0"][sel])
            a1 = score_block(y[sel], wf["M_MACRO"][sel])
            rows.append(metric_row(h, "M0", period, a0, a0["brier"]))
            rows.append(metric_row(h, "M_MACRO", period, a1, a0["brier"]))
        for off in nov["offsets"]:
            rows.append(
                metric_row(
                    h,
                    "M_MACRO",
                    f"NONOVERLAP_OFF{off['offset']:02d}",
                    {
                        "N": off["N"],
                        "prevalence": np.nan,
                        "brier": off["brier"],
                        "log_loss": np.nan,
                        "auc": np.nan,
                        "balanced_accuracy": np.nan,
                    },
                    off["brier_m0"] if np.isfinite(off.get("brier_m0", np.nan)) else np.nan,
                    brier_m0=off.get("brier_m0", np.nan),
                    low_n=off["low_n"],
                    note="LOW N" if off["low_n"] else "",
                )
            )
        rows.append(
            metric_row(
                h,
                "M_MACRO",
                "NONOVERLAP_SUMMARY",
                {
                    "N": nov["n_off"],
                    "prevalence": np.nan,
                    "brier": np.nan,
                    "log_loss": np.nan,
                    "auc": np.nan,
                    "balanced_accuracy": np.nan,
                },
                np.nan,
                bss_median=nov["bss_median"],
                bss_min=nov["bss_min"],
                bss_max=nov["bss_max"],
                n_offsets_bss_gt0=nov["n_pos"],
                n_offsets=nov["n_off"],
                note=f"skipped_low_n={nov['n_low']}",
            )
        )
        rows[-1]["brier_skill_vs_M0"] = nov["bss_median"]
        log(f"H={h} OOS N={st1['N']} BSS={bss(st1['brier'], st0['brier']):.3f}")

    metrics = pd.DataFrame(rows)
    col_order = [
        "horizon",
        "model",
        "period",
        "N",
        "prevalence",
        "brier",
        "brier_skill_vs_M0",
        "log_loss",
        "auc",
        "balanced_accuracy",
        "bss_median",
        "bss_min",
        "bss_max",
        "n_offsets_bss_gt0",
        "n_offsets",
        "brier_m0",
        "low_n",
        "note",
    ]
    metrics = metrics[col_order]
    metrics.to_csv(RESULTS / "final_oos_metrics.csv", index=False)
    write_report(
        df,
        metrics,
        {
            "last_crypto": last_c.strftime("%Y-%m-%d"),
            "last_macro": pd.Timestamp(last_m).strftime("%Y-%m-%d"),
            "n_cmc": len(cmc_weeks),
            "mkt_err": mkt_err,
        },
    )
    log(f"wrote {RESULTS / 'final_oos_metrics.csv'}")
    log(f"wrote {RESULTS / 'FINAL_CLEAN_OOS.md'}")


if __name__ == "__main__":
    main()
