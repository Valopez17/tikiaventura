#!/usr/bin/env python3
"""Phase 3B: Binance BTCUSDT daily derivatives panel. No models."""

from __future__ import annotations

import io
import json
import sys
import time
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
RESULTS = ROOT / "results"
VISION = "https://data.binance.vision"
S3 = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision"
FAPI_FUNDING = "https://fapi.binance.com/fapi/v1/fundingRate"
NS = {"s": "http://s3.amazonaws.com/doc/2006-03-01/"}

SYMBOL = "BTCUSDT"
MIN_PCTL_HIST = 365
PANEL_END = date(2026, 8, 29)  # last complete Vision daily date at build time
UA = "tikiaventura-phase3b/1.0 (research; derivatives coverage audit)"
DOWNLOAD_WORKERS = 12

KLINE_COLS = [
    "open_time",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "close_time",
    "quote_volume",
    "count",
    "taker_buy_volume",
    "taker_buy_quote_volume",
    "ignore",
]

STRESS_DATES = [
    date(2020, 3, 12),
    date(2021, 5, 19),
    *pd.date_range("2021-11-10", "2021-11-20").date,
    date(2022, 6, 18),
    date(2022, 11, 8),
    date(2022, 11, 9),
    date(2022, 11, 10),
    date(2024, 8, 5),
]


def log(msg: str) -> None:
    print(msg, flush=True)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def epoch_ms(x) -> int:
    """Binance Vision klines are ms until ~2025, then some spot files are microseconds."""
    v = int(x)
    if v >= 10**14:
        v //= 1000
    if v >= 10**14:
        v //= 1000
    return v


def ms_to_utc(ms: int) -> datetime:
    return datetime.fromtimestamp(epoch_ms(ms) / 1000.0, tz=timezone.utc)


def http_get(url: str, timeout: int = 60) -> bytes:
    req = Request(url, headers={"User-Agent": UA})
    with urlopen(req, timeout=timeout) as resp:
        return resp.read()


def list_s3_zips(prefix: str) -> list[str]:
    keys: list[str] = []
    marker = None
    while True:
        url = f"{S3}?delimiter=/&prefix={quote(prefix)}&max-keys=1000"
        if marker:
            url += f"&marker={quote(marker)}"
        root = ET.fromstring(http_get(url))
        contents = root.findall("s:Contents", NS)
        for c in contents:
            key = c.find("s:Key", NS).text
            if key and key.endswith(".zip"):
                keys.append(key)
        truncated = root.find("s:IsTruncated", NS)
        if truncated is None or truncated.text != "true" or not contents:
            break
        marker = contents[-1].find("s:Key", NS).text
    return keys


def vision_url(key: str) -> str:
    return f"{VISION}/{key}"


def dest_for_key(key: str) -> Path:
    return RAW / key.replace("data/", "", 1)


def download_zip(key: str) -> dict:
    dest = dest_for_key(key)
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 0:
        return {"key": key, "path": str(dest), "status": "skipped_exists", "bytes": dest.stat().st_size}
    url = vision_url(key)
    try:
        payload = http_get(url)
    except (HTTPError, URLError) as exc:
        return {"key": key, "path": str(dest), "status": f"error:{exc}", "bytes": 0}
    dest.write_bytes(payload)
    return {"key": key, "path": str(dest), "status": "downloaded", "bytes": len(payload)}


def read_zip_csv(path: Path) -> pd.DataFrame:
    with zipfile.ZipFile(path) as zf:
        name = zf.namelist()[0]
        raw = zf.read(name)
    text = raw.decode("utf-8")
    first = text.splitlines()[0] if text else ""
    header = first.split(",")[0].strip().lstrip("\ufeff")
    if header.isalpha() or header in {"calc_time", "open_time", "create_time"}:
        df = pd.read_csv(io.StringIO(text))
    else:
        df = pd.read_csv(io.StringIO(text), header=None, names=KLINE_COLS)
    return df


def expanding_pctl(x: np.ndarray, min_n: int = MIN_PCTL_HIST) -> np.ndarray:
    """Phase 1 convention: rank xt against finite history strictly before t."""
    n = len(x)
    out = np.full(n, np.nan)
    for t in range(n):
        xt = x[t]
        if not np.isfinite(xt):
            continue
        hist = x[:t]
        hist = hist[np.isfinite(hist)]
        if hist.size < min_n:
            continue
        out[t] = 100.0 * float(np.mean(hist <= xt))
    return out


def coverage_stats(s: pd.Series) -> dict:
    v = pd.to_numeric(s, errors="coerce")
    idx = s.index
    finite = v.notna()
    n = int(len(v))
    n_fin = int(finite.sum())
    first = last = None
    largest_gap = 0
    n_gaps = 0
    if n_fin:
        first = idx[finite.to_numpy()].min()
        last = idx[finite.to_numpy()].max()
        span = pd.date_range(first, last, freq="D")
        present = set(pd.DatetimeIndex(idx[finite.to_numpy()]).normalize())
        missing = [d for d in span if d not in present]
        n_gaps = len(missing)
        if missing:
            run = 1
            largest_gap = 1
            for i in range(1, len(missing)):
                if (missing[i] - missing[i - 1]).days == 1:
                    run += 1
                    largest_gap = max(largest_gap, run)
                else:
                    run = 1
    return {
        "first": None if first is None else pd.Timestamp(first).date().isoformat(),
        "last": None if last is None else pd.Timestamp(last).date().isoformat(),
        "n": n,
        "n_finite": n_fin,
        "pct_missing": 100.0 * (1.0 - n_fin / n) if n else np.nan,
        "n_missing_inside_span": n_gaps,
        "largest_gap_days": largest_gap,
    }


def fmt_num(x, nd=6):
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return "NA"
    if isinstance(x, (int, np.integer)):
        return str(int(x))
    return f"{float(x):.{nd}g}"


# ---------------------------------------------------------------------------
# Step 1 — verify
# ---------------------------------------------------------------------------


def verify_sources() -> dict:
    log("=== Step 1: verify Vision prefixes (list, do not download full history) ===")
    specs = {
        "funding_monthly": "data/futures/um/monthly/fundingRate/BTCUSDT/",
        "funding_daily": "data/futures/um/daily/fundingRate/BTCUSDT/",
        "premium_1h_monthly": "data/futures/um/monthly/premiumIndexKlines/BTCUSDT/1h/",
        "premium_1h_daily": "data/futures/um/daily/premiumIndexKlines/BTCUSDT/1h/",
        "perp_1d_monthly": "data/futures/um/monthly/klines/BTCUSDT/1d/",
        "perp_1d_daily": "data/futures/um/daily/klines/BTCUSDT/1d/",
        "metrics_daily": "data/futures/um/daily/metrics/BTCUSDT/",
        "spot_1d_monthly": "data/spot/monthly/klines/BTCUSDT/1d/",
        "spot_1d_daily": "data/spot/daily/klines/BTCUSDT/1d/",
        "mark_1h_monthly": "data/futures/um/monthly/markPriceKlines/BTCUSDT/1h/",
        "index_1h_monthly": "data/futures/um/monthly/indexPriceKlines/BTCUSDT/1h/",
    }
    info = {}
    for name, prefix in specs.items():
        zips = list_s3_zips(prefix)
        info[name] = {
            "prefix": prefix,
            "n_zip": len(zips),
            "first": zips[0] if zips else None,
            "last": zips[-1] if zips else None,
            "keys": zips,
        }
        log(f"  {name}: n={len(zips)} first={zips[0] if zips else None} last={zips[-1] if zips else None}")
    return info


def sample_headers(info: dict) -> dict:
    """Download one sample per KEEP source if missing; record columns."""
    samples = {
        "funding": info["funding_monthly"]["keys"][0],
        "premium_1h": info["premium_1h_monthly"]["keys"][0],
        "perp_1d": info["perp_1d_monthly"]["keys"][0],
        "metrics": info["metrics_daily"]["keys"][0],
        "spot_1d": info["spot_1d_monthly"]["keys"][0],
        "premium_1h_early_daily": info["premium_1h_daily"]["keys"][0],
        "perp_1d_early_daily": info["perp_1d_daily"]["keys"][0],
    }
    headers = {}
    for name, key in samples.items():
        rec = download_zip(key)
        path = Path(rec["path"])
        df = read_zip_csv(path)
        headers[name] = {
            "key": key,
            "columns": list(df.columns),
            "n_rows": int(len(df)),
            "head": df.head(2).astype(str).to_dict(orient="records"),
            "tail": df.tail(1).astype(str).to_dict(orient="records"),
        }
        log(f"  sample {name}: cols={list(df.columns)} n={len(df)}")
    return headers


# ---------------------------------------------------------------------------
# Step 2 — download verified archives
# ---------------------------------------------------------------------------


def keys_to_download(info: dict) -> list[str]:
    """Smallest complete history: monthly cores + daily edges Vision hosts."""
    keys: list[str] = []
    keys.extend(info["funding_monthly"]["keys"])  # 2020-01 .. 2026-07
    keys.extend(info["premium_1h_monthly"]["keys"])
    keys.extend(info["perp_1d_monthly"]["keys"])
    keys.extend(info["spot_1d_monthly"]["keys"])
    keys.extend(info["metrics_daily"]["keys"])

    prem_d = info["premium_1h_daily"]["keys"]
    perp_d = info["perp_1d_daily"]["keys"]
    spot_d = info["spot_1d_daily"]["keys"]

    keys.extend([k for k in prem_d if "2019-12" in k])
    keys.extend([k for k in prem_d if "2026-08" in k])
    keys.extend([k for k in perp_d if "2019-12" in k])
    keys.extend([k for k in perp_d if "2026-08" in k])
    keys.extend([k for k in spot_d if "2026-08" in k])

    # unique preserve order
    seen = set()
    uniq = []
    for k in keys:
        if k not in seen:
            seen.add(k)
            uniq.append(k)
    return uniq


def fetch_rest_funding(start_ms: int, end_ms: int) -> pd.DataFrame:
    rows = []
    cursor = start_ms
    while cursor < end_ms:
        url = f"{FAPI_FUNDING}?symbol={SYMBOL}&startTime={cursor}&endTime={end_ms}&limit=1000"
        payload = json.loads(http_get(url).decode())
        if not payload:
            break
        rows.extend(payload)
        last = int(payload[-1]["fundingTime"])
        nxt = last + 1
        if nxt <= cursor or len(payload) < 1000:
            break
        cursor = nxt
        time.sleep(0.05)
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df["fundingTime"] = pd.to_numeric(df["fundingTime"])
    df["fundingRate"] = pd.to_numeric(df["fundingRate"])
    df = df.drop_duplicates(subset=["fundingTime"]).sort_values("fundingTime")
    return df


def download_rest_funding_gaps() -> dict:
    """Vision monthly funding starts 2020-01 and ends 2026-07. REST fills gaps."""
    RAW.mkdir(parents=True, exist_ok=True)
    pre_path = RAW / "rest" / "funding_pre_vision.json"
    tail_path = RAW / "rest" / "funding_aug2026.json"
    pre_path.parent.mkdir(parents=True, exist_ok=True)
    rec = {"endpoint": FAPI_FUNDING, "symbol": SYMBOL}

    # listing-era through 2020-01-15 overlap
    if not pre_path.exists():
        log("  REST funding 2019-09 → 2020-01 (Vision gap + overlap)")
        pre = fetch_rest_funding(1567987200000, 1579150000000)
        pre_path.write_text(pre.to_json(orient="records"))
        rec["pre_status"] = "downloaded"
        rec["pre_n"] = int(len(pre))
    else:
        pre = pd.read_json(pre_path)
        rec["pre_status"] = "skipped_exists"
        rec["pre_n"] = int(len(pre))

    if not tail_path.exists():
        log("  REST funding 2026-07 overlap → 2026-08-29")
        tail = fetch_rest_funding(1782864000000, int(datetime(2026, 8, 30, tzinfo=timezone.utc).timestamp() * 1000))
        tail_path.write_text(tail.to_json(orient="records"))
        rec["tail_status"] = "downloaded"
        rec["tail_n"] = int(len(tail))
    else:
        tail = pd.read_json(tail_path)
        rec["tail_status"] = "skipped_exists"
        rec["tail_n"] = int(len(tail))

    rec["pre_path"] = str(pre_path)
    rec["tail_path"] = str(tail_path)
    rec["pre_first"] = None if pre.empty else int(pre["fundingTime"].min())
    rec["pre_last"] = None if pre.empty else int(pre["fundingTime"].max())
    rec["tail_first"] = None if tail.empty else int(tail["fundingTime"].min())
    rec["tail_last"] = None if tail.empty else int(tail["fundingTime"].max())
    return rec


def download_all(info: dict) -> list[dict]:
    keys = keys_to_download(info)
    log(f"=== Step 2: download {len(keys)} Vision ZIPs (skip existing) ===")
    recs = []
    with ThreadPoolExecutor(max_workers=DOWNLOAD_WORKERS) as ex:
        futs = {ex.submit(download_zip, k): k for k in keys}
        n = 0
        for fut in as_completed(futs):
            rec = fut.result()
            recs.append(rec)
            n += 1
            if n % 200 == 0 or rec["status"] not in {"skipped_exists", "downloaded"}:
                log(f"  {n}/{len(keys)} {rec['status']} {Path(rec['key']).name}")
    n_err = sum(1 for r in recs if str(r["status"]).startswith("error"))
    log(f"  done: {len(recs)} files, errors={n_err}")
    return recs


# ---------------------------------------------------------------------------
# Construct daily features
# ---------------------------------------------------------------------------


def load_funding(info: dict, rest_rec: dict) -> tuple[pd.DataFrame, dict]:
    frames = []
    for key in info["funding_monthly"]["keys"]:
        df = read_zip_csv(dest_for_key(key))
        df["source"] = "vision_monthly"
        frames.append(df)
    vis = pd.concat(frames, ignore_index=True)
    vis = vis.rename(columns={"calc_time": "fundingTime", "last_funding_rate": "fundingRate"})
    vis["fundingTime"] = pd.to_numeric(vis["fundingTime"])
    vis["fundingRate"] = pd.to_numeric(vis["fundingRate"])
    vis["funding_interval_hours"] = pd.to_numeric(vis["funding_interval_hours"], errors="coerce")

    pre = pd.read_json(rest_rec["pre_path"])
    tail = pd.read_json(rest_rec["tail_path"])
    for part, label in ((pre, "rest_pre_vision"), (tail, "rest_aug2026")):
        part = part.copy()
        part["source"] = label
        if "funding_interval_hours" not in part.columns:
            part["funding_interval_hours"] = np.nan
        frames_rest = part[["fundingTime", "fundingRate", "funding_interval_hours", "source"]]
        vis = pd.concat(
            [vis[["fundingTime", "fundingRate", "funding_interval_hours", "source"]], frames_rest],
            ignore_index=True,
        )

    vis["fundingTime"] = pd.to_numeric(vis["fundingTime"]).map(epoch_ms).astype("int64")
    vis["fundingRate"] = pd.to_numeric(vis["fundingRate"])
    vis = vis.sort_values("fundingTime")
    vis_only = vis.loc[vis["source"].eq("vision_monthly"), ["fundingTime", "fundingRate"]].drop_duplicates("fundingTime")
    rest_only = vis.loc[vis["source"].str.startswith("rest"), ["fundingTime", "fundingRate"]].drop_duplicates("fundingTime")
    ov = vis_only.merge(rest_only, on="fundingTime", suffixes=("_vis", "_rest"))
    n_mismatch = int((ov["fundingRate_vis"] - ov["fundingRate_rest"]).abs().gt(1e-12).sum()) if len(ov) else 0
    vis["in_vision"] = vis["source"].eq("vision_monthly")
    vis = vis.sort_values(["fundingTime", "in_vision"]).drop_duplicates("fundingTime", keep="last")

    vis["ts"] = vis["fundingTime"].map(ms_to_utc)
    vis["date"] = vis["ts"].dt.tz_convert("UTC").dt.date
    vis = vis.loc[vis["date"] <= PANEL_END].copy()

    meta = {
        "n_prints": int(len(vis)),
        "first_ts": vis["ts"].min().isoformat() if len(vis) else None,
        "last_ts": vis["ts"].max().isoformat() if len(vis) else None,
        "n_duplicates_dropped": None,
        "interval_values": vis["funding_interval_hours"].dropna().unique().tolist(),
        "n_rest_only": int((vis["source"] != "vision_monthly").sum()),
        "n_vision": int((vis["source"] == "vision_monthly").sum()),
        "n_overlap_prints": int(len(ov)),
        "n_overlap_rate_mismatch": n_mismatch,
    }
    return vis, meta


def daily_funding(prints: pd.DataFrame) -> pd.DataFrame:
    g = prints.sort_values("fundingTime").groupby("date", sort=True)
    daily = pd.DataFrame(
        {
            "funding_rate_last": g["fundingRate"].last(),
            "funding_mean_1d": g["fundingRate"].mean(),
            "funding_n_prints": g["fundingRate"].size(),
            "funding_source": g["source"].last(),
        }
    )
    daily.index = pd.to_datetime(pd.Index(daily.index))
    daily = daily.sort_index()
    daily["funding_change_1d"] = daily["funding_rate_last"].diff()

    # 7d mean / 30d sum of *settlements* with date in window ending t
    rate_by_print = prints.set_index("ts")["fundingRate"].sort_index()
    # map each calendar day
    dates = daily.index
    mean7 = []
    cum30 = []
    for t in dates:
        t_end = pd.Timestamp(t).tz_localize("UTC") + pd.Timedelta(hours=23, minutes=59, seconds=59, milliseconds=999)
        w7_start = pd.Timestamp(t).tz_localize("UTC") - pd.Timedelta(days=6)
        w30_start = pd.Timestamp(t).tz_localize("UTC") - pd.Timedelta(days=29)
        s7 = rate_by_print.loc[(rate_by_print.index >= w7_start) & (rate_by_print.index <= t_end)]
        s30 = rate_by_print.loc[(rate_by_print.index >= w30_start) & (rate_by_print.index <= t_end)]
        first = pd.Timestamp(dates.min()).tz_localize("UTC")
        mean7.append(float(s7.mean()) if len(s7) and t >= dates.min() + pd.Timedelta(days=6) else np.nan)
        cum30.append(float(s30.sum()) if len(s30) and t >= dates.min() + pd.Timedelta(days=29) else np.nan)
    daily["funding_mean_7d"] = mean7
    daily["funding_cum_30d"] = cum30
    daily["funding_pctl"] = expanding_pctl(daily["funding_rate_last"].to_numpy(dtype=float))
    return daily


def load_premium(info: dict) -> pd.DataFrame:
    keys = []
    keys.extend([k for k in info["premium_1h_daily"]["keys"] if "2019-12" in k])
    keys.extend(info["premium_1h_monthly"]["keys"])
    keys.extend([k for k in info["premium_1h_daily"]["keys"] if "2026-08" in k])
    frames = []
    for key in keys:
        df = read_zip_csv(dest_for_key(key))
        if "open_time" not in df.columns:
            df.columns = KLINE_COLS
        frames.append(df[KLINE_COLS])
    px = pd.concat(frames, ignore_index=True)
    px["open_time"] = pd.to_numeric(px["open_time"]).map(epoch_ms)
    px["close_time"] = pd.to_numeric(px["close_time"]).map(epoch_ms)
    px["close"] = pd.to_numeric(px["close"])
    px = px.drop_duplicates("open_time").sort_values("open_time")
    px["ts_close"] = px["close_time"].map(ms_to_utc)
    px["date"] = px["ts_close"].dt.tz_convert("UTC").dt.date
    px = px.loc[px["date"] <= PANEL_END].copy()

    # Monthly ZIPs omit some days that still exist as daily Vision files. Fill those only.
    span = pd.date_range(px["date"].min(), px["date"].max(), freq="D")
    have = set(px["date"].unique())
    missing = [d.date() for d in span if d.date() not in have]
    filled = []
    for d in missing:
        key = f"data/futures/um/daily/premiumIndexKlines/BTCUSDT/1h/BTCUSDT-1h-{d.isoformat()}.zip"
        rec = download_zip(key)
        if rec["status"].startswith("error") or not Path(rec["path"]).exists() or Path(rec["path"]).stat().st_size == 0:
            continue
        try:
            df = read_zip_csv(Path(rec["path"]))
        except (zipfile.BadZipFile, KeyError, ValueError):
            continue
        if "open_time" not in df.columns:
            df.columns = KLINE_COLS
        df = df[KLINE_COLS].copy()
        df["open_time"] = pd.to_numeric(df["open_time"]).map(epoch_ms)
        df["close_time"] = pd.to_numeric(df["close_time"]).map(epoch_ms)
        df["close"] = pd.to_numeric(df["close"])
        df["ts_close"] = df["close_time"].map(ms_to_utc)
        df["date"] = df["ts_close"].dt.tz_convert("UTC").dt.date
        frames_d = df.loc[df["date"] == d]
        if len(frames_d):
            px = pd.concat([px, frames_d], ignore_index=True)
            filled.append(d.isoformat())
    if filled:
        log(f"  filled premium daily gaps: {filled}")
        px = px.drop_duplicates("open_time").sort_values("open_time")
    px.attrs["premium_gap_filled"] = filled
    px.attrs["premium_still_missing"] = [d.isoformat() for d in missing if d.isoformat() not in filled]
    return px


def daily_basis(px: pd.DataFrame) -> pd.DataFrame:
    # last bar whose close_time is on UTC day t (already <= 23:59:59.999)
    last = px.sort_values("close_time").groupby("date", sort=True).tail(1)
    daily = pd.DataFrame(
        {
            "basis_last": last["close"].to_numpy(),
            "basis_n_bars": px.groupby("date").size().reindex(last["date"]).to_numpy(),
            "basis_last_close_time": last["ts_close"].to_numpy(),
        },
        index=pd.to_datetime(last["date"].to_numpy()),
    ).sort_index()
    daily["basis_change_1d"] = daily["basis_last"].diff()
    daily["basis_pctl"] = expanding_pctl(daily["basis_last"].to_numpy(dtype=float))
    daily["basis_implementation"] = "binance_premium_index_1h_close"
    return daily


def load_1d_klines(keys: list[str]) -> pd.DataFrame:
    frames = []
    for key in keys:
        df = read_zip_csv(dest_for_key(key))
        if list(df.columns) != KLINE_COLS:
            df = df.copy()
            df.columns = KLINE_COLS
        frames.append(df[KLINE_COLS])
    k = pd.concat(frames, ignore_index=True)
    k["open_time"] = pd.to_numeric(k["open_time"]).map(epoch_ms)
    k["close_time"] = pd.to_numeric(k["close_time"]).map(epoch_ms)
    k["quote_volume"] = pd.to_numeric(k["quote_volume"])
    k["volume"] = pd.to_numeric(k["volume"])
    k = k.drop_duplicates("open_time").sort_values("open_time")
    k["date"] = k["open_time"].map(lambda ms: ms_to_utc(int(ms)).date())
    k = k.loc[k["date"] <= PANEL_END].copy()
    return k


def daily_perp(info: dict) -> pd.DataFrame:
    keys = [k for k in info["perp_1d_daily"]["keys"] if "2019-12" in k]
    keys.extend(info["perp_1d_monthly"]["keys"])
    keys.extend([k for k in info["perp_1d_daily"]["keys"] if "2026-08" in k])
    k = load_1d_klines(keys)
    daily = pd.DataFrame(
        {
            "perp_quote_volume": k["quote_volume"].to_numpy(),
            "perp_base_volume": k["volume"].to_numpy(),
            "perp_close_time": k["close_time"].map(ms_to_utc).to_numpy(),
        },
        index=pd.to_datetime(k["date"].to_numpy()),
    ).sort_index()
    # Phase 1 rel_volume: prior window median (shift 1)
    prior_med = daily["perp_quote_volume"].shift(1).rolling(30, min_periods=30).median()
    daily["perp_volume_rel_30d"] = daily["perp_quote_volume"] / prior_med
    daily["perp_volume_pctl"] = expanding_pctl(daily["perp_quote_volume"].to_numpy(dtype=float))
    return daily


def daily_spot(info: dict) -> pd.DataFrame:
    # monthly from 2019-12 is enough for the ratio; keep all monthly (small) + Aug 2026 daily
    keys = list(info["spot_1d_monthly"]["keys"])
    keys.extend([k for k in info["spot_1d_daily"]["keys"] if "2026-08" in k])
    k = load_1d_klines(keys)
    daily = pd.DataFrame(
        {"spot_quote_volume": k["quote_volume"].to_numpy()},
        index=pd.to_datetime(k["date"].to_numpy()),
    ).sort_index()
    return daily


def load_oi(info: dict) -> tuple[pd.DataFrame, dict]:
    rows = []
    n_dup_ts = 0
    n_files = 0
    n_bad_ts = 0
    for key in info["metrics_daily"]["keys"]:
        df = read_zip_csv(dest_for_key(key))
        n_files += 1
        ts = pd.to_datetime(df["create_time"], utc=True, errors="coerce")
        n_bad_ts += int(ts.isna().sum())
        before = len(df)
        df = df.copy()
        df["ts"] = ts
        df = df.dropna(subset=["ts"])
        df = df.drop_duplicates("ts", keep="last")
        n_dup_ts += before - len(df)
        df["sum_open_interest_value"] = pd.to_numeric(df["sum_open_interest_value"], errors="coerce")
        df["sum_open_interest"] = pd.to_numeric(df["sum_open_interest"], errors="coerce")
        df["date"] = df["ts"].dt.tz_convert("UTC").dt.date
        file_day = date.fromisoformat(Path(key).stem.split("metrics-")[-1])
        df = df.loc[
            (df["date"] == file_day)
            & (df["ts"].dt.hour * 3600 + df["ts"].dt.minute * 60 + df["ts"].dt.second <= 23 * 3600 + 59 * 60 + 59)
        ]
        # Last snapshot of the day can be 0E-8 garbage (observed 2022-03-07, 2024-07-10, 2024-07-12).
        # Use the last strictly positive notional at or before 23:59:59 UTC.
        pos = df.loc[df["sum_open_interest_value"] > 0].sort_values("ts")
        if len(pos):
            last = pos.iloc[-1]
            n_snap = int(len(df))
            dt_diffs = df.sort_values("ts")["ts"].diff().dt.total_seconds().dropna()
            med_step = float(dt_diffs.median()) if len(dt_diffs) else np.nan
            rows.append(
                {
                    "date": last["date"],
                    "oi_value": float(last["sum_open_interest_value"]),
                    "oi_contracts": float(last["sum_open_interest"]),
                    "oi_n_snapshots": n_snap,
                    "oi_last_ts": last["ts"],
                    "oi_first_ts": df["ts"].min(),
                    "oi_median_step_sec": med_step,
                    "oi_used_last_positive": bool(last["ts"] != df.sort_values("ts").iloc[-1]["ts"]),
                }
            )
        if n_files % 400 == 0:
            log(f"  metrics parsed {n_files}/{len(info['metrics_daily']['keys'])}")
    oi = pd.DataFrame(rows)
    oi.index = pd.to_datetime(oi["date"])
    oi = oi.sort_index()
    meta = {
        "n_files": n_files,
        "n_days": int(len(oi)),
        "n_dup_timestamps_dropped": n_dup_ts,
        "n_bad_ts": n_bad_ts,
        "n_last_positive_fallback": int(oi["oi_used_last_positive"].sum()) if len(oi) and "oi_used_last_positive" in oi.columns else 0,
        "first": oi.index.min().date().isoformat() if len(oi) else None,
        "last": oi.index.max().date().isoformat() if len(oi) else None,
    }
    return oi, meta


def daily_oi(oi: pd.DataFrame, perp: pd.DataFrame) -> pd.DataFrame:
    d = oi.copy()
    d["oi_change_1d"] = d["oi_value"] / d["oi_value"].shift(1) - 1.0
    d["oi_change_7d"] = d["oi_value"] / d["oi_value"].shift(7) - 1.0
    d["oi_change_1d"] = d["oi_change_1d"].replace([np.inf, -np.inf], np.nan)
    d["oi_change_7d"] = d["oi_change_7d"].replace([np.inf, -np.inf], np.nan)
    d["oi_pctl"] = expanding_pctl(d["oi_value"].to_numpy(dtype=float))
    aligned = d.join(perp[["perp_quote_volume"]], how="left")
    vol = aligned["perp_quote_volume"]
    d["oi_over_volume"] = np.where((vol > 0) & vol.notna(), d["oi_value"] / vol, np.nan)
    return d


def build_panel(fund: pd.DataFrame, basis: pd.DataFrame, perp: pd.DataFrame, spot: pd.DataFrame, oi: pd.DataFrame) -> pd.DataFrame:
    start = min(s.index.min() for s in [fund, basis, perp, oi] if len(s))
    idx = pd.date_range(start, PANEL_END, freq="D")
    panel = pd.DataFrame(index=idx)
    panel.index.name = "date"
    panel = panel.join(fund, how="left")
    panel = panel.join(basis, how="left")
    panel = panel.join(perp, how="left")
    panel = panel.join(spot, how="left")
    oi_cols = [
        "oi_value",
        "oi_change_1d",
        "oi_change_7d",
        "oi_pctl",
        "oi_over_volume",
        "oi_n_snapshots",
        "oi_last_ts",
        "oi_contracts",
        "oi_median_step_sec",
    ]
    panel = panel.join(oi[oi_cols], how="left")
    panel["perp_spot_volume_ratio"] = np.where(
        (panel["spot_quote_volume"] > 0) & panel["spot_quote_volume"].notna() & panel["perp_quote_volume"].notna(),
        panel["perp_quote_volume"] / panel["spot_quote_volume"],
        np.nan,
    )
    panel["flag_funding"] = panel["funding_rate_last"].notna().astype(int)
    panel["flag_basis"] = panel["basis_last"].notna().astype(int)
    panel["flag_perp"] = panel["perp_quote_volume"].notna().astype(int)
    panel["flag_oi"] = panel["oi_value"].notna().astype(int)
    panel["flag_spot_quote"] = panel["spot_quote_volume"].notna().astype(int)
    panel["basis_implementation"] = panel["basis_implementation"].fillna("binance_premium_index_1h_close")
    return panel


# ---------------------------------------------------------------------------
# Audits
# ---------------------------------------------------------------------------


def write_coverage(panel: pd.DataFrame, info: dict, headers: dict, fund_meta: dict, oi_meta: dict, rest_rec: dict, download_recs: list[dict], built_at: str) -> None:
    feats = [
        "funding_rate_last",
        "funding_mean_1d",
        "funding_change_1d",
        "funding_mean_7d",
        "funding_cum_30d",
        "funding_pctl",
        "basis_last",
        "basis_change_1d",
        "basis_pctl",
        "perp_quote_volume",
        "perp_volume_rel_30d",
        "perp_volume_pctl",
        "perp_spot_volume_ratio",
        "oi_value",
        "oi_change_1d",
        "oi_change_7d",
        "oi_pctl",
        "oi_over_volume",
    ]
    lines = []
    a = lines.append
    a("# Derivatives coverage audit")
    a("")
    a(f"Built: `{built_at}`. Decision time: end of UTC day t. Panel last date: **{PANEL_END.isoformat()}** (last complete Vision daily file).")
    a("")
    a("No Coinglass / Glassnode / CryptoQuant / CME / Yahoo substitution.")
    a("")
    a("## Raw source listing (Step 1)")
    a("")
    a("| source | prefix | n_zip | first key | last key |")
    a("|---|---|---:|---|---|")
    for name in [
        "funding_monthly",
        "funding_daily",
        "premium_1h_monthly",
        "premium_1h_daily",
        "perp_1d_monthly",
        "perp_1d_daily",
        "metrics_daily",
        "spot_1d_monthly",
        "spot_1d_daily",
        "mark_1h_monthly",
        "index_1h_monthly",
    ]:
        d = info[name]
        a(f"| {name} | `{d['prefix']}` | {d['n_zip']} | `{d['first']}` | `{d['last']}` |")
    a("")
    a("### Sample headers")
    a("")
    for name, h in headers.items():
        a(f"- **{name}** (`{h['key']}`): columns `{h['columns']}`, n_rows={h['n_rows']}")
    a("")
    a("### Timestamp semantics (from samples + full read)")
    a("")
    a("- **Funding Vision:** `calc_time` milliseconds UTC = settlement instant. Header: `calc_time,funding_interval_hours,last_funding_rate`.")
    a("- **Funding REST:** `fundingTime` milliseconds UTC. Overlap with Vision on 2020-01-01 matches to the printed rate (including 2ms quirks).")
    a("- **Premium 1h:** kline `open_time`/`close_time` ms UTC. Daily `basis_last` = `close` of the last bar with `close_time` on UTC day t (the 23:00–23:59 bar, close_time 23:59:59.999).")
    a("- **1d klines:** `open_time` = 00:00:00 UTC of t; `close_time` = 23:59:59.999 UTC of t. Quote volume = USDT.")
    a("- **Metrics OI:** `create_time` naive datetime, treated as **UTC**. Last snapshot on calendar date t with time ≤ 23:59:59. File-day spill into t+1 dropped.")
    a("")
    a("## REST gap fill (same Binance BTCUSDT, not a vendor switch)")
    a("")
    a(f"- Pre-Vision: `data/raw/rest/funding_pre_vision.json` n={rest_rec['pre_n']} status={rest_rec['pre_status']}")
    a(f"- Aug 2026 tail: `data/raw/rest/funding_aug2026.json` n={rest_rec['tail_n']} status={rest_rec['tail_status']}")
    a(f"- Funding prints in panel: n={fund_meta['n_prints']}, vision={fund_meta['n_vision']}, rest_used={fund_meta['n_rest_only']}")
    a(f"- REST vs Vision overlapping fundingTime rows: {fund_meta['n_overlap_prints']}; |rate| mismatch > 1e-12: {fund_meta['n_overlap_rate_mismatch']}")
    a(f"- First funding print: {fund_meta['first_ts']}")
    a(f"- Last funding print: {fund_meta['last_ts']}")
    a(f"- `funding_interval_hours` unique (Vision rows): {fund_meta['interval_values']}")
    a("")
    a("Vision **daily** `fundingRate` prefix has **0** files. Current month funding cannot come from Vision.")
    a("")
    a("## Download")
    a("")
    n_skip = sum(1 for r in download_recs if r["status"] == "skipped_exists")
    n_dl = sum(1 for r in download_recs if r["status"] == "downloaded")
    n_err = sum(1 for r in download_recs if str(r["status"]).startswith("error"))
    a(f"- Vision ZIP attempts: {len(download_recs)}; downloaded={n_dl}; skipped_exists={n_skip}; errors={n_err}. Existing ZIPs are never overwritten.")
    a(f"- OI metrics files listed: {oi_meta['n_files']}; days with a last snapshot: {oi_meta['n_days']}")
    a(f"- Duplicate OI timestamps dropped (keep last): {oi_meta['n_dup_timestamps_dropped']}")
    a(f"- Days where last snapshot was non-positive so an earlier same-day positive print was used: {oi_meta.get('n_last_positive_fallback', 'NA')}")
    a("")
    a("## Feature coverage")
    a("")
    a("| feature | first finite | last finite | N finite | % missing (panel) | missing days inside span | largest gap (days) |")
    a("|---|---|---|---:|---:|---:|---:|")
    for col in feats:
        st = coverage_stats(panel[col])
        a(
            f"| `{col}` | {st['first']} | {st['last']} | {st['n_finite']} | {st['pct_missing']:.2f} | {st['n_missing_inside_span']} | {st['largest_gap_days']} |"
        )
    a("")
    a("Panel index is a complete UTC calendar from the earliest series start through "
      f"`{PANEL_END.isoformat()}` (N={len(panel)}). Pre-history is left as NaN, not filled.")
    a("")
    a("## Explicit questions")
    a("")
    a("### 1. Does funding really start near 2019-09?")
    a("")
    a("**On Binance REST, yes. On Binance Vision monthly archives, no.**")
    a("")
    a("- USD-M BTCUSDT listing is 2019-09. REST first print in the pull: see first_ts above (expected **2019-09-10 08:00 UTC**).")
    a("- Vision monthly `fundingRate` first file: **2020-01**. 2019-09 and 2019-12 monthly URLs return **404**. Daily Vision fundingRate: **empty**.")
    a("- This build uses REST for 2019-09-10 through 2019-12-31 and Vision from 2020-01-01, after checking that 2020-01-01 prints match.")
    a("")
    a("### 2. Does basis have the same start?")
    a("")
    a("**No.** Premium-index 1h daily Vision starts **2019-12-24** (first bar 03:00 UTC — incomplete first day). Monthly 1h starts **2020-01**. Mark/index 1h also exist from ~2019-12 / 2020-01 but were **not** mixed in; basis is premium index only.")
    a("")
    a("### 3. Does perp volume have complete history?")
    a("")
    a("Vision daily 1d klines start **2019-12-31** (one day before monthly 2020-01). Monthly 2020-01 through 2026-07 plus daily 2026-08-01..29. No 1m/aggTrades. Quote-volume field present. Gaps inside that span are reported in the table above.")
    a("")
    a("### 4. When does OI actually start?")
    a("")
    a(f"**{oi_meta['first']}** through **{oi_meta['last']}**. File `BTCUSDT-metrics-2020-08-31.zip` is **404**. No backfill. REST `openInterestHist` was not used (30-day cap).")
    a("")
    a("### 5. Is there enough overlap for later modeling?")
    a("")
    a("Core funding + basis + perp quote volume overlap from **2020-01-01** (basis from 2019-12-24, perp from 2019-12-31, funding from 2019-09-10). Expanding percentiles need 365 prior finite days → funding/basis/volume percentiles from ~late 2020 / early 2021. OI levels from 2020-09-01; `oi_pctl` only after 365 OI days (~2021-09-01). That is shorter than Phase 2's 2015– BTC-percentile sample. Later 3F tests must restrict to the derivatives overlap, not pretend 2015–2019 has these features.")
    a("")
    a("### 6. Are there structural source changes?")
    a("")
    a("- **Funding packaging:** Vision monthly from 2020-01; REST elsewhere. Values match on overlap. Interval hours on Vision samples remain **8** through 2026-07; REST rows do not always carry interval.")
    a("- **Premium files:** early daily ZIPs include a header row; monthly 1h ZIPs often have no header. Same kline layout.")
    a("- **OI cadence:** 2020-09-01 metrics file is ~5-minute snapshots with **duplicate timestamps**. 2026-08-29 file is **irregular** (first snapshot 01:10, last 23:40, not a 5-minute grid). Median step is stored as `oi_median_step_sec`.")
    a("- **OI last snapshot:** three metrics files (2022-03-07, 2024-07-10, 2024-07-12) end at 23:55 with `0E-8` notional while earlier snapshots that day are large and positive. Daily `oi_value` uses the last **strictly positive** `sum_open_interest_value` ≤ 23:59:59 UTC, not the garbage trailing row.")
    a("- **Premium monthly holes:** some monthly 1h ZIPs omit days that still exist as daily Vision files (e.g. 2021-07-01, 2021-07-24–27). Those days are filled from the daily prefix when the ZIP exists. 2019-12-25 through 2019-12-30 daily URLs return **404** and stay missing.")
    a("- **Spot vs Phase 1:** Phase 1 volume is **base BTC**. This panel's ratio uses Vision spot **quote USDT** vs perp **quote USDT**.")
    a("- **Spot kline timestamps:** monthly/daily spot 1d files switch from **milliseconds** to **microseconds** beginning **2025-01**. This build divides values ≥ 1e14 by 1000 so dates stay on the UTC day. Perp/premium/funding samples remain milliseconds.")
    a("")
    a("## Known source gaps")
    a("")
    a("| gap | expected? |")
    a("|---|---|")
    a("| Vision funding 2019-09–2019-12 | Yes — files 404; filled from REST |")
    a("| Vision daily fundingRate | Yes — prefix empty; Aug 2026 from REST |")
    a("| Vision monthly files for 2026-08 | Yes — month incomplete; daily klines/metrics/premium used |")
    a("| OI before 2020-09-01 | Yes — metrics not published |")
    a("| Premium 2019-12-25–2019-12-30 | Yes — daily Vision 404; no fill |")
    a("| Perp 1d before 2019-12-31 | Yes — first daily file |")
    a("| Panel 2026-08-30 (build calendar today) | Yes — Vision daily lag; not included |")
    a("")
    RESULTS.joinpath("DERIVATIVES_COVERAGE_AUDIT.md").write_text("\n".join(lines) + "\n")


def write_data_audit(panel: pd.DataFrame, prints: pd.DataFrame, fund_meta: dict, built_at: str) -> str:
    lines = []
    a = lines.append
    a("# Derivatives data audit")
    a("")
    a(f"Built: `{built_at}`. Sanity only. **Do not retune definitions from stress dates.**")
    a("")
    a("## Mechanical checks")
    a("")
    dates = panel.index
    sorted_ok = bool(dates.is_monotonic_increasing)
    unique_ok = bool(dates.is_unique)
    freq_ok = bool(len(dates) == (dates.max() - dates.min()).days + 1)
    a(f"- dates sorted: **{sorted_ok}**")
    a(f"- dates unique: **{unique_ok}**")
    a(f"- complete UTC calendar (no missing index days): **{freq_ok}** N={len(panel)}")
    a(f"- timezone: index is naive UTC calendar dates (no DST). Funding/premium/klines converted with `tz=UTC`. OI `create_time` has no zone; treated as UTC.")
    a("")
    n_dup_prints = int(prints["fundingTime"].duplicated().sum())
    a(f"- duplicate funding prints after merge: **{n_dup_prints}** (must be 0)")
    a(f"- funding prints per day: min={int(panel['funding_n_prints'].min()) if panel['funding_n_prints'].notna().any() else 'NA'} "
      f"median={fmt_num(panel['funding_n_prints'].median(), 2)} max={int(panel['funding_n_prints'].max()) if panel['funding_n_prints'].notna().any() else 'NA'}")
    # 00/08/16 pattern
    hours = prints["ts"].dt.hour
    a(f"- funding settlement hours UTC (value counts): {prints.assign(hour=hours).groupby('hour').size().to_dict()}")
    a("")
    # future timestamps
    last_allowed = datetime(PANEL_END.year, PANEL_END.month, PANEL_END.day, 23, 59, 59, 999000, tzinfo=timezone.utc)
    n_future_fund = int((prints["ts"] > last_allowed).sum())
    a(f"- funding prints after panel end 23:59:59 UTC: **{n_future_fund}**")
    a(f"- basis last close times after panel end: **{int((pd.to_datetime(panel['basis_last_close_time'], utc=True) > last_allowed).sum()) if 'basis_last_close_time' in panel.columns else 'NA'}**")
    a("")
    a("- daily funding aggregation: `funding_rate_last` = last settlement with date t; `funding_mean_1d` = mean of settlements whose UTC date is t. 00:00 UTC print belongs to that calendar day, not the previous day.")
    a("")
    oi = panel["oi_value"]
    a("- OI non-positive among finite: **{n}** (must be 0 after dropping trailing 0E-8 snapshots)".replace("{n}", str(int(((oi <= 0) & oi.notna()).sum()))))
    a(f"- OI max: {fmt_num(oi.max(), 4)} min finite: {fmt_num(oi.min(), 4)}")
    a(f"- perp quote volume < 0: **{int((panel['perp_quote_volume'] < 0).sum())}**")
    a(f"- spot quote volume < 0: **{int((panel['spot_quote_volume'] < 0).sum())}**")
    a("")
    b = panel["basis_last"]
    a(f"- basis_last finite min/median/max: {fmt_num(b.min(), 6)} / {fmt_num(b.median(), 6)} / {fmt_num(b.max(), 6)}")
    a(f"- |basis_last| > 0.05 (5%): **{int((b.abs() > 0.05).sum())}** — flagged, not dropped")
    a(f"- |basis_last| > 0.2: **{int((b.abs() > 0.2).sum())}**")
    a("- basis implementation (single): `binance_premium_index_1h_close`. Mark/index not mixed. CME not used.")
    a("")
    a("- spot/perp units: both Vision 1d kline **quote asset volume (USDT)**. Phase 1 `binance_btcusdt_1d.csv` volume is **base BTC** and was **not** used. Ratio omitted where either quote series is missing.")
    a(f"- perp_spot_volume_ratio finite min/median/max: {fmt_num(panel['perp_spot_volume_ratio'].min(), 4)} / {fmt_num(panel['perp_spot_volume_ratio'].median(), 4)} / {fmt_num(panel['perp_spot_volume_ratio'].max(), 4)}")
    a("")
    a("- percentiles: `expanding_pctl` uses `hist = x[:t]` (strictly before t), `mean(hist <= xt)`, min 365 finite prior observations. Same as Phase 1 `MIN_HIST=365`. OI threshold was **not** shortened.")
    a("")
    a("### Missing-data pattern")
    a("")
    a("- Funding NaNs before first REST print and nowhere intended inside the funding span except true holes (see coverage).")
    a("- Basis NaNs before 2019-12-24.")
    a("- Perp NaNs before 2019-12-31.")
    a("- OI NaNs before 2020-09-01 by construction (not backfilled).")
    a("- `*_pctl` NaN until 365 prior finite observations.")
    a("- `funding_mean_7d` / `funding_cum_30d` NaN until 7 / 30 calendar days from first funding day.")
    a("- `perp_volume_rel_30d` NaN until 30 prior perp days (Phase 1-style prior median).")
    a("")
    a("## Stress dates (descriptive only)")
    a("")
    cols = [
        "funding_rate_last",
        "funding_mean_1d",
        "funding_pctl",
        "basis_last",
        "basis_pctl",
        "perp_quote_volume",
        "perp_volume_rel_30d",
        "perp_spot_volume_ratio",
        "oi_value",
        "oi_change_1d",
        "oi_pctl",
    ]
    a("| date | " + " | ".join(cols) + " |")
    a("|" + "|".join(["---"] * (1 + len(cols))) + "|")
    for d in STRESS_DATES:
        ts = pd.Timestamp(d)
        if ts not in panel.index:
            a(f"| {d.isoformat()} | " + " | ".join(["not in panel"] * len(cols)) + " |")
            continue
        row = panel.loc[ts]
        cells = [d.isoformat()]
        for c in cols:
            val = row[c]
            if c in {"perp_quote_volume", "oi_value"}:
                cells.append(fmt_num(val, 4))
            elif c.endswith("_pctl"):
                cells.append(fmt_num(val, 4))
            else:
                cells.append(fmt_num(val, 6))
        a("| " + " | ".join(cells) + " |")
    a("")
    a("These dates were not used to change formulas, windows, or inclusion rules.")
    a("")
    a("## Source splice")
    a("")
    a("Funding is the only spliced series: REST (2019-09-10–2019-12-31 and 2026-08-01–2026-08-29) + Vision monthly (2020-01–2026-07). Overlap on 2020-01-01: identical `fundingTime` and `fundingRate`. No other series is spliced across vendors.")
    a("")
    a("## Disposition")
    a("")
    core_ok = (
        panel["funding_rate_last"].notna().sum() > 2000
        and panel["basis_last"].notna().sum() > 2000
        and panel["perp_quote_volume"].notna().sum() > 2000
        and sorted_ok
        and unique_ok
        and n_dup_prints == 0
        and n_future_fund == 0
    )
    oi_short = panel["oi_value"].notna().sum() < panel["funding_rate_last"].notna().sum()
    if core_ok and oi_short:
        disp = "PASS WITH LIMITATIONS"
        why = (
            "Funding, premium-index basis, and perp quote volume reconstruct without look-ahead "
            "and overlap for years. OI starts 2020-09-01 (later than funding), Vision funding files "
            "start 2020-01 (REST fills 2019-Q4 and 2026-08), and OI snapshot cadence changes over time. "
            "Percentiles burn 365 days. Not a FAIL: timestamps are usable."
        )
    elif core_ok:
        disp = "PASS"
        why = "Core funding + basis + perp activity are clean and timestamp-safe."
    else:
        disp = "FAIL"
        why = "Core reconstruction failed a mechanical check (see above)."
    a(f"**{disp}**")
    a("")
    a(why)
    a("")
    a("Predictive value is **not** tested here. High funding is not a bearish rule; negative funding is not a bullish rule.")
    text = "\n".join(lines) + "\n"
    RESULTS.joinpath("DERIVATIVES_DATA_AUDIT.md").write_text(text)
    return disp


def write_dictionary(panel: pd.DataFrame, built_at: str) -> None:
    def first_valid(col: str) -> str:
        s = panel[col].dropna()
        return s.index.min().date().isoformat() if len(s) else "NA"

    rows = [
        {
            "name": "funding_rate_last",
            "formula": "Last BTCUSDT USD-M funding settlement with fundingTime ≤ 23:59:59 UTC on t (UTC date of the settlement).",
            "units": "rate per 8h interval (not annualized)",
            "source": "Vision monthly fundingRate; REST for Vision gaps",
            "econ": "Cost of being long the perp that interval. Positive → longs pay shorts (crowded long / bullish basis). Measures crowding / carry, not a directional rule.",
            "up": "Possibly after deeply negative funding (short crowding). Untested.",
            "adv": "Possibly at high positive funding extremes (long crowding). Untested.",
            "ts": "Settlement instant UTC.",
            "lim": "Exchange-specific. 8h interval in this sample; do not annualize without documenting the interval. Vision missing 2019-Q4 and 2026-08.",
        },
        {
            "name": "funding_mean_1d",
            "formula": "Mean of all settlements whose UTC calendar date is t.",
            "units": "rate per interval",
            "source": "same funding prints",
            "econ": "Day's average carry, less noisy than a single 16:00 print.",
            "up": "Same as level, milder. Untested.",
            "adv": "Same as level, milder. Untested.",
            "ts": "Only prints on day t.",
            "lim": "Typically 3 prints (00:00, 08:00, 16:00 UTC).",
        },
        {
            "name": "funding_change_1d",
            "formula": "funding_rate_last(t) − funding_rate_last(t−1)",
            "units": "rate difference",
            "source": "derived",
            "econ": "Speed of crowding / de-crowding.",
            "up": "Untested.",
            "adv": "Fast spike into already-high funding may coincide with stress. Untested.",
            "ts": "Both ends ≤ t.",
            "lim": "NaN on first funding day.",
        },
        {
            "name": "funding_mean_7d",
            "formula": "Mean of all settlements with timestamp in [t 00:00 UTC − 6d, t 23:59:59.999 UTC]. NaN if t is within 6 days of first funding day.",
            "units": "rate per interval",
            "source": "derived",
            "econ": "Persistent carry over a week.",
            "up": "Untested.",
            "adv": "Untested.",
            "ts": "Prints ≤ t only.",
            "lim": "Window is calendar 7d of prints, not 7 prints. Not tuned.",
        },
        {
            "name": "funding_cum_30d",
            "formula": "Sum of all settlements in [t 00:00 UTC − 29d, t 23:59:59.999 UTC]. NaN if t is within 29 days of first funding day.",
            "units": "sum of interval rates (not $ PnL)",
            "source": "derived",
            "econ": "Running cost of staying long for ~30d of 8h prints.",
            "up": "Untested.",
            "adv": "Large positive sum = longs have paid a lot. Untested.",
            "ts": "Prints ≤ t.",
            "lim": "Not dollar-weighted by OI. Not annualized.",
        },
        {
            "name": "funding_pctl",
            "formula": "Expanding percentile of funding_rate_last:  mean(I(x_s ≤ x_t) for finite s < t). NaN if fewer than 365 finite prior observations.",
            "units": "percentile in [0, 100], Phase 1 scale",
            "source": "derived (Phase 1 convention)",
            "econ": "Where today's last funding sits in this contract's history.",
            "up": "Low percentile (cheap/negative vs history). Untested.",
            "adv": "High percentile. Untested.",
            "ts": "History strictly before t.",
            "lim": "Unstable early; 365-day gate.",
        },
        {
            "name": "basis_last",
            "formula": "Close of the last USD-M BTCUSDT premium-index 1h kline with close_time on UTC date t.",
            "units": "(mark−index)/index as published in the premium index kline close",
            "source": "Vision premiumIndexKlines 1h",
            "econ": "Perp richness vs spot index. Positive = perp premium (long demand / bullish basis).",
            "up": "Extreme cheap/negative basis (short crowding). Untested.",
            "adv": "Extreme rich basis. Untested.",
            "ts": "Bar close_time 23:59:59.999 UTC on t.",
            "lim": "Binance-specific. First day 2019-12-24 starts 03:00 UTC. Not CME annualized basis.",
        },
        {
            "name": "basis_change_1d",
            "formula": "basis_last(t) − basis_last(t−1)",
            "units": "premium-index difference",
            "source": "derived",
            "econ": "Speed of richness change.",
            "up": "Untested.",
            "adv": "Untested.",
            "ts": "Both ≤ t.",
            "lim": "NaN on first basis day.",
        },
        {
            "name": "basis_pctl",
            "formula": "Expanding percentile of basis_last, s < t, min 365 finite priors.",
            "units": "percentile in [0, 100], Phase 1 scale",
            "source": "derived",
            "econ": "Historical rarity of today's premium.",
            "up": "Untested.",
            "adv": "Untested.",
            "ts": "History strictly before t.",
            "lim": "Same 365-day gate.",
        },
        {
            "name": "perp_quote_volume",
            "formula": "USD-M BTCUSDT 1d kline quote asset volume for UTC day t.",
            "units": "USDT",
            "source": "Vision futures um 1d klines",
            "econ": "Leveraged-market activity that day.",
            "up": "High volume with rising prices can be participation. Untested.",
            "adv": "High volume with falling prices can be stress. Untested.",
            "ts": "Completed 1d bar, close_time 23:59:59.999 UTC t.",
            "lim": "Binance only. Starts 2019-12-31.",
        },
        {
            "name": "perp_volume_rel_30d",
            "formula": "perp_quote_volume(t) / median(perp_quote_volume[t−30 .. t−1]). Prior window only (Phase 1 rel_volume style).",
            "units": "ratio",
            "source": "derived",
            "econ": "Unusual perp activity vs the last 30 days.",
            "up": "Untested.",
            "adv": "Very high relative volume often coincides with liquidations/stress. Untested.",
            "ts": "Median uses s < t.",
            "lim": "NaN until 30 prior perp days. Window not tuned.",
        },
        {
            "name": "perp_volume_pctl",
            "formula": "Expanding percentile of perp_quote_volume, s < t, min 365.",
            "units": "percentile in [0, 100], Phase 1 scale",
            "source": "derived",
            "econ": "Historical rarity of today's perp USDT volume.",
            "up": "Untested.",
            "adv": "Untested.",
            "ts": "History strictly before t.",
            "lim": "Level percentiles mix secular growth in Binance volume; interpret with care.",
        },
        {
            "name": "perp_spot_volume_ratio",
            "formula": "perp_quote_volume(t) / spot_quote_volume(t), both USDT quote volume from Vision 1d klines.",
            "units": "ratio (USDT/USDT)",
            "source": "Vision USD-M 1d + Vision spot 1d",
            "econ": "How much activity sits in perps vs spot. High ratio = leverage-heavy tape.",
            "up": "Untested.",
            "adv": "Possibly when perps dominate. Untested.",
            "ts": "Both completed UTC day t bars.",
            "lim": "Phase 1 spot tape is base BTC volume and was not used. Ratio NaN if either quote series missing. Binance-specific.",
        },
        {
            "name": "oi_value",
            "formula": "Last strictly positive `sum_open_interest_value` snapshot on UTC date t with create_time ≤ 23:59:59 UTC, after dropping duplicate timestamps (keep last) and dropping t+1 spill. Trailing 0E-8 rows are ignored.",
            "units": "USDT notional",
            "source": "Vision daily metrics BTCUSDT",
            "econ": "Stock of leveraged positions (notional).",
            "up": "Rising OI with rising price can be fuel. Untested.",
            "adv": "High OI into a drop can be unwind fuel. Untested.",
            "ts": "Last snapshot ≤ t 23:59:59 UTC. Late-sample last snapshot may be before 23:59 (e.g. 23:40).",
            "lim": "Starts 2020-09-01. Cadence changes (5m duplicates → irregular). No 2019 OI. No mcap ratio in 3B.",
        },
        {
            "name": "oi_change_1d",
            "formula": "oi_value(t) / oi_value(t−1) − 1",
            "units": "fraction",
            "source": "derived",
            "econ": "1-day notional OI growth/contraction.",
            "up": "Untested.",
            "adv": "Fast OI drop with negative returns may be forced unwind. Untested.",
            "ts": "Both days' last snapshots ≤ their day ends.",
            "lim": "Percent change, not a dollar difference. NaN if prior day missing.",
        },
        {
            "name": "oi_change_7d",
            "formula": "oi_value(t) / oi_value(t−7) − 1",
            "units": "fraction",
            "source": "derived",
            "econ": "Week-scale position build/unwind.",
            "up": "Untested.",
            "adv": "Untested.",
            "ts": "t and t−7 last snapshots only.",
            "lim": "Calendar 7d, not 7 business days (crypto 24/7).",
        },
        {
            "name": "oi_pctl",
            "formula": "Expanding percentile of oi_value, s < t, min 365 finite OI days. Not shortened.",
            "units": "percentile in [0, 100], Phase 1 scale",
            "source": "derived",
            "econ": "Historical crowding of Binance BTCUSDT notional OI.",
            "up": "Untested.",
            "adv": "Right tail. Untested.",
            "ts": "History strictly before t.",
            "lim": "First valid ~365 days after 2020-09-01. Secular growth in OI makes recent percentiles often high.",
        },
        {
            "name": "oi_over_volume",
            "formula": "oi_value(t) / perp_quote_volume(t) if perp_quote_volume > 0",
            "units": "USDT OI per USDT daily perp volume (days of volume)",
            "source": "derived",
            "econ": "How large the position stock is relative to that day's trading. High = sticky crowding / thin vs OI.",
            "up": "Untested.",
            "adv": "High ratio may mean painful unwind. Untested.",
            "ts": "Both known at end of t.",
            "lim": "Optional; only where both clean. Not oi_over_mcap (no frozen BTC mcap series used).",
        },
    ]

    lines = []
    a = lines.append
    a("# Derivatives feature dictionary")
    a("")
    a(f"Built: `{built_at}`. Exchange: Binance USD-M **BTCUSDT** unless noted. Decision time: end of UTC day t.")
    a("")
    a("Percentiles are in **[0, 100]**, same scale as Phase 1. Ranking rule: history strictly before t, min 365.")
    a("")
    a("Do not treat high funding as deterministically bearish or negative funding as bullish. These series measure crowding, leverage, participation, and position build/unwind. Predictive value is for Phase 3F.")
    a("")
    for r in rows:
        a(f"## `{r['name']}`")
        a("")
        a(f"- **Exact formula:** {r['formula']}")
        a(f"- **Units:** {r['units']}")
        a(f"- **Source:** {r['source']}")
        a(f"- **First valid date (this build):** {first_valid(r['name'])}")
        a(f"- **Expected economic interpretation:** {r['econ']}")
        a(f"- **Likely relevance to UP_60D:** {r['up']}")
        a(f"- **Likely relevance to ADVERSE_60D:** {r['adv']}")
        a(f"- **Timestamp rule:** {r['ts']}")
        a(f"- **Known limitation:** {r['lim']}")
        a("")
    RESULTS.joinpath("DERIVATIVES_FEATURE_DICTIONARY.md").write_text("\n".join(lines) + "\n")


def main() -> int:
    built_at = utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    RAW.mkdir(parents=True, exist_ok=True)
    PROCESSED.mkdir(parents=True, exist_ok=True)
    RESULTS.mkdir(parents=True, exist_ok=True)

    info = verify_sources()
    headers = sample_headers(info)
    download_recs = download_all(info)
    rest_rec = download_rest_funding_gaps()
    rest_rec["downloaded_at_utc"] = built_at

    manifest = {
        "downloaded_at_utc": built_at,
        "panel_end": PANEL_END.isoformat(),
        "rest_funding": rest_rec,
        "vision_counts": {k: {"n_zip": info[k]["n_zip"], "first": info[k]["first"], "last": info[k]["last"]} for k in info},
        "n_zip_attempts": len(download_recs),
        "n_zip_errors": sum(1 for r in download_recs if str(r["status"]).startswith("error")),
    }
    (RAW / "DOWNLOAD_MANIFEST.json").write_text(json.dumps(manifest, indent=2, default=str))

    log("=== construct daily panel ===")
    prints, fund_meta = load_funding(info, rest_rec)
    fund = daily_funding(prints)
    log(f"  funding days={len(fund)} prints={len(prints)}")
    px = load_premium(info)
    basis = daily_basis(px)
    log(f"  basis days={len(basis)} 1h bars={len(px)}")
    perp = daily_perp(info)
    log(f"  perp days={len(perp)}")
    spot = daily_spot(info)
    log(f"  spot days={len(spot)}")
    log("  parsing OI metrics (all daily files)…")
    oi_raw, oi_meta = load_oi(info)
    oi = daily_oi(oi_raw, perp)
    log(f"  oi days={len(oi)}")

    panel = build_panel(fund, basis, perp, spot, oi)
    out_cols = [
        "funding_rate_last",
        "funding_mean_1d",
        "funding_change_1d",
        "funding_mean_7d",
        "funding_cum_30d",
        "funding_pctl",
        "basis_last",
        "basis_change_1d",
        "basis_pctl",
        "perp_quote_volume",
        "perp_volume_rel_30d",
        "perp_volume_pctl",
        "perp_spot_volume_ratio",
        "oi_value",
        "oi_change_1d",
        "oi_change_7d",
        "oi_pctl",
        "oi_over_volume",
        "funding_n_prints",
        "funding_source",
        "flag_funding",
        "flag_basis",
        "flag_perp",
        "flag_oi",
        "flag_spot_quote",
        "spot_quote_volume",
        "basis_implementation",
        "oi_n_snapshots",
        "oi_last_ts",
        "oi_median_step_sec",
    ]
    out = panel[out_cols].copy()
    out.index.name = "date"
    if "oi_last_ts" in out.columns:
        ts = pd.to_datetime(out["oi_last_ts"], utc=True, errors="coerce")
        out["oi_last_ts"] = ts.dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    csv_path = PROCESSED / "btc_derivatives_daily.csv"
    out.to_csv(csv_path, date_format="%Y-%m-%d")
    log(f"  wrote {csv_path} rows={len(out)}")

    log("=== write audits ===")
    write_coverage(panel, info, headers, fund_meta, oi_meta, rest_rec, download_recs, built_at)
    disp = write_data_audit(panel, prints, fund_meta, built_at)
    write_dictionary(panel, built_at)
    log(f"disposition: {disp}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
