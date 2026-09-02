#!/usr/bin/env python3
"""Hsieh, Huang & Liu (2025) — core-table replication.

Spec taken from the published PDF (Finance Research Letters 86, 108356).
Internal paper inconsistency on market-state windows is documented in README.md.
This script does not read Wen / Moskowitz / rally-map files.
"""

from __future__ import annotations

import json
import socket
import sys
import time
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

PAPER_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = PAPER_DIR / "data" / "raw"
LISTINGS_DIR = RAW_DIR / "listings"
PROCESSED_DIR = PAPER_DIR / "data" / "processed"
RESULTS_DIR = PAPER_DIR / "results"

SAMPLE_START = date(2015, 1, 1)
SAMPLE_END = date(2023, 12, 31)
# Appendix A: weekly returns = log difference of Friday closes.
WEEK_END_WEEKDAY = 4  # Monday=0 … Friday=4
CMC_LISTINGS_URL = (
    "https://api.coinmarketcap.com/data-api/v3/cryptocurrency/listings/historical"
)
CMC_MAP_URL = (
    "https://api.coinmarketcap.com/data-api/v3/map/all"
    "?listing_status=active,inactive,untracked"
)
PAGE_LIMIT = 500
USER_AGENT = "tikiaventura-hsieh-2025-replication/0.2 (academic replication)"
MAX_RETRIES = 6
MIN_MCAP_USD = 1_000_000.0
MIN_PRICE_HISTORY_WEEKS = 20
FORMATION_J = 2
HOLDING_KS = (1, 2, 3, 4)
N_QUANTILES = 5
# Momentum-leg weighting is not stated. Equal-weighted is the replica choice
# because Table 4 Panels B–C drop small/illiquid coins, which would barely
# move a value-weighted WML. Value-weighted rows are also written.
WEIGHTINGS = ("equal", "value")
# Newey-West lag length is not stated. Use 4 weekly lags (one month).
NEWEY_WEST_LAGS = 4

# Stablecoin screen is required but the paper does not list tickers.
# Filter by CMC id when known, else symbol/name. NOT a paper appendix list.
STABLECOIN_IDS = {
    825, 3408, 4687, 4943, 2563, 3330, 3306, 6952, 9566, 7129, 11419, 11423,
    3717, 5176, 4195, 7859, 7083, 3662, 6739, 7246, 2588, 13502, 27722,
    8886, 22636, 16080, 23121, 21794, 1420, 7033, 19623, 27565,
}
STABLECOIN_SYMBOLS = {
    "USDT", "USDC", "BUSD", "DAI", "TUSD", "USDP", "PAX", "GUSD", "FRAX",
    "LUSD", "USDD", "UST", "USTC", "FEI", "MIM", "SUSD", "USDJ", "CUSD",
    "USDN", "HUSD", "USDK", "FDUSD", "PYUSD", "EURC", "EURT", "EURS",
    "USDE", "USDS", "CRVUSD", "GHO", "DOLA", "OUSD", "ALUSD", "SUSD",
    "USDX", "USDQ", "XAUT", "PAXG",  # gold-pegged excluded? paper says stablecoins only
}
# Do not treat PAXG/XAUT as USD stablecoins.
STABLECOIN_SYMBOLS -= {"XAUT", "PAXG"}
STABLECOIN_NAME_BITS = (
    "tether", "usd coin", "binance usd", "trueusd", "terrausd", "dai ",
    "gemini dollar", "paxos standard", "frax", "liquity usd", "first digital usd",
    "paypal usd", "usdd", "fei usd", "magic internet money", "origin dollar",
    "neutrino usd", "huobi usd", "stablecoin",
)

STATE_COLS = [
    "week",
    "market_return",
    "trailing_4w_market_return",
    "state_cooper_4w",
    "prior_state_1w",
    "subsequent_state_1w",
    "state",
    "prior_state",
    "transition",
]
MOM_COLS = [
    "transition",
    "formation_period",
    "holding_period",
    "weighting",
    "state_definition",
    "winner_return",
    "loser_return",
    "momentum_return",
    "standard_error",
    "t_stat",
    "p_value",
    "N",
]


def log(msg: str) -> None:
    print(msg, flush=True)


def week_ends_in_sample() -> list[date]:
    d = SAMPLE_START
    while d.weekday() != WEEK_END_WEEKDAY:
        d += timedelta(days=1)
    out = []
    while d <= SAMPLE_END:
        out.append(d)
        d += timedelta(days=7)
    return out


def http_get_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    last_err: Exception | None = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            with urllib.request.urlopen(req, timeout=180) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, socket.timeout, OSError) as err:
            last_err = err
            sleep_s = min(2 ** attempt, 30)
            log(f"  retry {attempt}/{MAX_RETRIES} after {err}; sleep {sleep_s}s")
            time.sleep(sleep_s)
    raise RuntimeError(f"GET failed after {MAX_RETRIES} retries: {url}") from last_err


def snapshot_path(week: date) -> Path:
    return LISTINGS_DIR / f"{week.isoformat()}.csv"


def snapshot_is_complete(path: Path) -> bool:
    if not path.exists() or path.stat().st_size == 0:
        return False
    try:
        df = pd.read_csv(path, nrows=1)
    except Exception:
        return False
    return "asset_id" in df.columns and "price" in df.columns


def _fetch_listing_page(week: date, start: int) -> list[dict]:
    url = (
        f"{CMC_LISTINGS_URL}?date={week.isoformat()}"
        f"&start={start}&limit={PAGE_LIMIT}"
    )
    payload = http_get_json(url)
    status = payload.get("status") or {}
    if str(status.get("error_code")) not in {"0", "0.0"}:
        raise RuntimeError(f"CMC listings error for {week} start={start}: {status}")
    return payload.get("data") or []


def _page_to_rows(week: date, page: list[dict]) -> list[dict]:
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
                "slug": item.get("slug"),
                "cmc_rank": item.get("cmcRank"),
                "circulating_supply": item.get("circulatingSupply"),
                "price": q.get("price"),
                "market_cap": q.get("marketCap"),
                "volume": q.get("volume24h"),
                "quote_last_updated": q.get("lastUpdated"),
                "item_last_updated": item.get("lastUpdated"),
                "source": "coinmarketcap_data_api_listings_historical",
            }
        )
    return rows


def download_week_snapshot(week: date) -> pd.DataFrame:
    rows: list[dict] = []
    start = 1
    empty_pages = 0
    max_start = 25000
    while empty_pages < 2 and start <= max_start:
        page = _fetch_listing_page(week, start)
        time.sleep(0.12)
        if not page:
            empty_pages += 1
            start += PAGE_LIMIT
            continue
        empty_pages = 0
        rows.extend(_page_to_rows(week, page))
        start += PAGE_LIMIT
        if len(page) < PAGE_LIMIT:
            nxt = _fetch_listing_page(week, start)
            time.sleep(0.12)
            if not nxt:
                break
            rows.extend(_page_to_rows(week, nxt))
            start += PAGE_LIMIT
    if not rows:
        raise RuntimeError(f"Empty CMC snapshot for {week}")
    return pd.DataFrame(rows).drop_duplicates(subset=["asset_id"], keep="first")


def truncated_snapshot_weeks(expected: list[date]) -> list[date]:
    recs = []
    for week in expected:
        path = snapshot_path(week)
        if not path.exists():
            continue
        n = sum(1 for _ in path.open()) - 1
        recs.append((week, n))
    if not recs:
        return []
    weeks, counts = zip(*recs)
    idx = pd.to_datetime(list(weeks))
    s = pd.Series(counts, index=idx)

    def looks_short(n: int) -> bool:
        return (n % PAGE_LIMIT) in {PAGE_LIMIT - 2, PAGE_LIMIT - 1}

    clean = s.copy()
    clean[s.map(looks_short)] = np.nan
    med = clean.reindex(s.index).interpolate(limit_direction="both")
    med = med.fillna(s.rolling(13, center=True, min_periods=3).median())
    bad = []
    for week, n, m in zip(weeks, counts, med.tolist()):
        if pd.isna(m) or m <= 0:
            continue
        if n < 0.80 * m:
            bad.append(week)
        elif looks_short(n) and n < 0.95 * m:
            bad.append(week)
    return bad


def download_raw() -> None:
    LISTINGS_DIR.mkdir(parents=True, exist_ok=True)
    map_path = RAW_DIR / "cmc_cryptocurrency_map.json"
    if not map_path.exists():
        log("Downloading CMC cryptocurrency map.")
        payload = http_get_json(CMC_MAP_URL)
        map_path.write_text(json.dumps(payload), encoding="utf-8")
    weeks = week_ends_in_sample()
    log(f"Friday snapshots: {weeks[0]} → {weeks[-1]} ({len(weeks)} weeks).")
    missing = [w for w in weeks if not snapshot_is_complete(snapshot_path(w))]
    log(f"Weeks already on disk: {len(weeks) - len(missing)}; to download: {len(missing)}")
    for i, week in enumerate(missing, start=1):
        log(f"[{i}/{len(missing)}] listings {week.isoformat()}")
        df = download_week_snapshot(week)
        df.to_csv(snapshot_path(week), index=False)
        log(f"  {len(df)} coins → {week.isoformat()}.csv")
        time.sleep(0.12)
    truncated = truncated_snapshot_weeks(weeks)
    if truncated:
        log(f"Re-downloading {len(truncated)} truncated Friday snapshots.")
        for i, week in enumerate(truncated, start=1):
            path = snapshot_path(week)
            if path.exists():
                path.unlink()
            log(f"[repair {i}/{len(truncated)}] listings {week.isoformat()}")
            df = download_week_snapshot(week)
            df.to_csv(path, index=False)
            log(f"  {len(df)} coins → {path.name}")
            time.sleep(0.12)


def load_friday_snapshots() -> pd.DataFrame:
    weeks = week_ends_in_sample()
    frames = []
    missing = []
    for week in weeks:
        path = snapshot_path(week)
        if not snapshot_is_complete(path):
            missing.append(week)
            continue
        frames.append(pd.read_csv(path))
    if missing:
        raise FileNotFoundError(f"Missing Friday snapshots, e.g. {missing[:3]}")
    panel = pd.concat(frames, ignore_index=True)
    panel["snapshot_date"] = pd.to_datetime(panel["snapshot_date"]).dt.date
    return panel


def write_manifest(raw: pd.DataFrame) -> pd.DataFrame:
    grouped = (
        raw.sort_values(["asset_id", "snapshot_date"])
        .groupby("asset_id", as_index=False)
        .agg(
            symbol=("symbol", "last"),
            asset_name=("asset_name", "last"),
            first_date=("snapshot_date", "min"),
            last_date=("snapshot_date", "max"),
            N=("snapshot_date", "size"),
            source=("source", "first"),
            price_available=("price", lambda s: bool(s.notna().any())),
            market_cap_available=("market_cap", lambda s: bool(s.notna().any())),
            volume_available=("volume", lambda s: bool(s.notna().any())),
        )
    )
    grouped["asset_id"] = grouped["asset_id"].astype(int)
    dest = RAW_DIR / "data_manifest.csv"
    grouped.to_csv(dest, index=False)
    log(f"Wrote {dest} ({len(grouped)} assets).")
    return grouped


def is_stablecoin(asset_id: int, symbol: str, name: str) -> bool:
    if int(asset_id) in STABLECOIN_IDS:
        return True
    sym = str(symbol or "").upper()
    if sym in STABLECOIN_SYMBOLS:
        return True
    nm = str(name or "").lower()
    return any(bit in nm for bit in STABLECOIN_NAME_BITS)


def build_weekly_panel(raw: pd.DataFrame) -> pd.DataFrame:
    df = raw.copy()
    df = df.dropna(subset=["asset_id", "snapshot_date"])
    df["asset_id"] = df["asset_id"].astype(int)
    df["weekly_price"] = pd.to_numeric(df["price"], errors="coerce")
    df["market_cap"] = pd.to_numeric(df["market_cap"], errors="coerce")
    df["volume"] = pd.to_numeric(df["volume"], errors="coerce")
    df = df.sort_values(["asset_id", "snapshot_date"])
    prev_price = df.groupby("asset_id")["weekly_price"].shift(1)
    prev_date = df.groupby("asset_id")["snapshot_date"].shift(1)
    df["days_since_prev"] = (
        pd.to_datetime(df["snapshot_date"]) - pd.to_datetime(prev_date)
    ).dt.days
    consecutive = df["days_since_prev"].eq(7)
    valid_px = consecutive & prev_price.gt(0) & df["weekly_price"].gt(0)
    # Appendix A: log difference of Friday closes.
    df["weekly_return"] = np.where(
        valid_px, np.log(df["weekly_price"] / prev_price), np.nan
    )
    df["is_stablecoin"] = [
        is_stablecoin(i, s, n)
        for i, s, n in zip(df["asset_id"], df["symbol"], df["asset_name"])
    ]
    out = df[
        [
            "snapshot_date",
            "asset_id",
            "symbol",
            "asset_name",
            "weekly_price",
            "weekly_return",
            "market_cap",
            "volume",
            "is_stablecoin",
        ]
    ].rename(columns={"snapshot_date": "week"})
    dest = PROCESSED_DIR / "crypto_weekly_panel.csv"
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    out.to_csv(dest, index=False)
    log(f"Wrote {dest} ({len(out)} rows).")
    return out


def apply_eligibility(panel: pd.DataFrame) -> pd.DataFrame:
    """Appendix A filters, applied at the token-week level."""
    df = panel.copy()
    df = df.sort_values(["asset_id", "week"])
    df["lag_mcap"] = df.groupby("asset_id")["market_cap"].shift(1)
    df["n_price_obs"] = df.groupby("asset_id")["weekly_price"].transform(
        lambda s: s.where(s.gt(0)).expanding().count()
    )
    eligible = (
        ~df["is_stablecoin"]
        & df["weekly_price"].gt(0)
        & df["lag_mcap"].ge(MIN_MCAP_USD)
        & df["volume"].gt(0)
        & df["n_price_obs"].ge(MIN_PRICE_HISTORY_WEEKS)
        & df["weekly_return"].notna()
        & np.isfinite(df["weekly_return"])
    )
    df["eligible"] = eligible
    n_coins = df.loc[df["eligible"], "asset_id"].nunique()
    log(
        f"Eligible token-weeks: {int(df['eligible'].sum())}; "
        f"unique coins ever eligible: {n_coins} "
        f"(paper Table 1 full-sample unique coins = 2130)."
    )
    return df


def build_market_states(panel: pd.DataFrame) -> pd.DataFrame:
    usable = panel.loc[panel["eligible"]].dropna(subset=["weekly_return", "lag_mcap"])
    usable = usable[usable["lag_mcap"] > 0]

    def vw_return(g: pd.DataFrame) -> float:
        w = g["lag_mcap"].to_numpy(dtype=float)
        r = g["weekly_return"].to_numpy(dtype=float)
        denom = w.sum()
        if denom <= 0:
            return np.nan
        return float(np.dot(w, r) / denom)

    rows = []
    for week, g in usable.groupby("week"):
        rows.append({"week": week, "market_return": vw_return(g), "n_coins": int(len(g))})
    weekly = pd.DataFrame(rows).sort_values("week").reset_index(drop=True)
    r = weekly["market_return"]
    weekly["trailing_4w_market_return"] = (
        r.shift(1) + r.shift(2) + r.shift(3) + r.shift(4)
    )
    # Section 3.1 Cooper: state of week t from R^m_{t-5:t-1}.
    weekly["state_cooper_4w"] = np.where(
        weekly["trailing_4w_market_return"].isna(),
        pd.NA,
        np.where(weekly["trailing_4w_market_return"] >= 0.0, "UP", "DOWN"),
    )
    # Table 3 / Asem-Tian notes: prior = past 1-week market; subsequent = this week.
    weekly["prior_state_1w"] = np.where(
        r.shift(1).isna(), pd.NA, np.where(r.shift(1) >= 0.0, "UP", "DOWN")
    )
    weekly["subsequent_state_1w"] = np.where(
        r.isna(), pd.NA, np.where(r >= 0.0, "UP", "DOWN")
    )
    # Default columns for the required market_states.csv schema: Table 3 transition.
    weekly["state"] = weekly["subsequent_state_1w"]
    weekly["prior_state"] = weekly["prior_state_1w"]
    weekly["transition"] = np.where(
        weekly["prior_state"].isna() | weekly["state"].isna(),
        pd.NA,
        weekly["prior_state"].astype("string") + "->" + weekly["state"].astype("string"),
    )
    out = weekly[STATE_COLS + ["n_coins"]].copy()
    dest = PROCESSED_DIR / "market_states.csv"
    out.to_csv(dest, index=False)
    log(
        f"Wrote {dest} ({len(out)} weeks). "
        f"Table-3 transitions: {out['transition'].value_counts(dropna=True).to_dict()}"
    )
    return out


def _quantile_labels(ranks: pd.Series) -> pd.Series:
    # 1 = loser, 5 = winner. Ties broken by first-occurrence rank.
    q = pd.qcut(ranks.rank(method="first"), N_QUANTILES, labels=False, duplicates="drop")
    return q + 1


def formation_and_hold_returns(panel: pd.DataFrame) -> pd.DataFrame:
    df = panel.sort_values(["asset_id", "week"]).copy()
    df["formation_return"] = df.groupby("asset_id")["weekly_return"].transform(
        lambda s: s.rolling(FORMATION_J, min_periods=FORMATION_J).sum().shift(1)
    )
    weeks = sorted(df["week"].unique())
    week_index = {w: i for i, w in enumerate(weeks)}
    recs = []
    for t in weeks:
        g = df[
            (df["week"] == t)
            & df["eligible"]
            & df["formation_return"].notna()
            & df["lag_mcap"].gt(0)
        ].copy()
        if len(g) < N_QUANTILES:
            continue
        g["q"] = _quantile_labels(g["formation_return"])
        if g["q"].nunique() < N_QUANTILES:
            continue
        losers = g.loc[g["q"] == 1, ["asset_id", "lag_mcap"]].copy()
        winners = g.loc[g["q"] == N_QUANTILES, ["asset_id", "lag_mcap"]].copy()
        i = week_index[t]
        for offset in range(max(HOLDING_KS)):
            if i + offset >= len(weeks):
                break
            hold_week = weeks[i + offset]
            hold = df.loc[df["week"] == hold_week, ["asset_id", "weekly_return"]]
            recs.append(_portfolio_row(t, hold_week, offset, losers, winners, hold, "equal"))
            recs.append(_portfolio_row(t, hold_week, offset, losers, winners, hold, "value"))
    out = pd.DataFrame([r for r in recs if r is not None])
    log(f"Formation/hold rows: {len(out)}")
    return out


def _portfolio_row(
    form_week: date,
    hold_week: date,
    offset: int,
    losers: pd.DataFrame,
    winners: pd.DataFrame,
    hold: pd.DataFrame,
    weighting: str,
) -> dict | None:
    l = losers.merge(hold, on="asset_id")
    w = winners.merge(hold, on="asset_id")
    l = l.dropna(subset=["weekly_return"])
    w = w.dropna(subset=["weekly_return"])
    if l.empty or w.empty:
        return None
    if weighting == "equal":
        loser_r = float(l["weekly_return"].mean())
        winner_r = float(w["weekly_return"].mean())
    else:
        if l["lag_mcap"].sum() <= 0 or w["lag_mcap"].sum() <= 0:
            return None
        loser_r = float(np.average(l["weekly_return"], weights=l["lag_mcap"]))
        winner_r = float(np.average(w["weekly_return"], weights=w["lag_mcap"]))
    return {
        "form_week": form_week,
        "hold_week": hold_week,
        "offset": offset,
        "weighting": weighting,
        "winner_return": winner_r,
        "loser_return": loser_r,
        "momentum_return": winner_r - loser_r,
    }


def jegadeesh_titman_calendar(hold_rows: pd.DataFrame) -> pd.DataFrame:
    """Average overlapping K-week portfolios in calendar time (JT 1993)."""
    rows = []
    for weighting, g_w in hold_rows.groupby("weighting"):
        for k in HOLDING_KS:
            g = g_w.loc[g_w["offset"] < k]
            cal = (
                g.groupby("hold_week", as_index=False)[
                    ["winner_return", "loser_return", "momentum_return"]
                ].mean()
                .rename(columns={"hold_week": "week"})
            )
            cal["holding_period"] = int(k)
            cal["weighting"] = weighting
            rows.append(cal)
    return pd.concat(rows, ignore_index=True)


def newey_west_mean(series: pd.Series, lags: int = NEWEY_WEST_LAGS) -> dict:
    y = pd.to_numeric(series, errors="coerce").dropna()
    n = int(y.shape[0])
    if n < 8:
        return {
            "mean": np.nan,
            "se": np.nan,
            "t_stat": np.nan,
            "p_value": np.nan,
            "N": n,
        }
    x = np.ones(n)
    res = sm.OLS(y.to_numpy(dtype=float), x).fit(
        cov_type="HAC", cov_kwds={"maxlags": int(lags), "use_correction": True}
    )
    return {
        "mean": float(res.params[0]),
        "se": float(res.bse[0]),
        "t_stat": float(res.tvalues[0]),
        "p_value": float(res.pvalues[0]),
        "N": n,
    }


def attach_states(calendar: pd.DataFrame, states: pd.DataFrame) -> pd.DataFrame:
    st = states.copy()
    st["week"] = pd.to_datetime(st["week"]).dt.date
    calendar = calendar.copy()
    calendar["week"] = pd.to_datetime(calendar["week"]).dt.date
    return calendar.merge(
        st[["week", "state_cooper_4w", "prior_state_1w", "subsequent_state_1w", "transition"]],
        on="week",
        how="left",
    )


def summarize_slice(
    g: pd.DataFrame,
    transition: str,
    k: int,
    weighting: str,
    state_definition: str,
) -> dict:
    w = newey_west_mean(g["winner_return"])
    l = newey_west_mean(g["loser_return"])
    m = newey_west_mean(g["momentum_return"])
    return {
        "transition": transition,
        "formation_period": FORMATION_J,
        "holding_period": k,
        "weighting": weighting,
        "state_definition": state_definition,
        "winner_return": w["mean"],
        "loser_return": l["mean"],
        "momentum_return": m["mean"],
        "standard_error": m["se"],
        "t_stat": m["t_stat"],
        "p_value": m["p_value"],
        "N": m["N"],
    }


def build_momentum_table(calendar: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (k, weighting), g0 in calendar.groupby(["holding_period", "weighting"]):
        k = int(k)
        rows.append(summarize_slice(g0, "UNCONDITIONAL", k, weighting, "none"))
        # Table 2 note: UP/DOWN from past one-week market (prior_state_1w).
        for lab, sub in (("UP", "UP"), ("DOWN", "DOWN")):
            gg = g0[g0["prior_state_1w"] == sub]
            rows.append(
                summarize_slice(gg, lab, k, weighting, "table2_past_1w")
            )
        # Section 3.1 Cooper 4-week (body text, conflicts with Table 2 note).
        for lab in ("UP", "DOWN"):
            gg = g0[g0["state_cooper_4w"] == lab]
            rows.append(
                summarize_slice(gg, f"COOPER4W_{lab}", k, weighting, "section31_cooper_4w")
            )
        # Table 3: Asem-Tian prior 1w -> subsequent 1w.
        for trans in ("UP->UP", "UP->DOWN", "DOWN->UP", "DOWN->DOWN"):
            gg = g0[g0["transition"] == trans]
            rows.append(
                summarize_slice(gg, trans, k, weighting, "table3_asem_tian_1w")
            )
    out = pd.DataFrame(rows)[MOM_COLS]
    dest = RESULTS_DIR / "state_transition_momentum.csv"
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out.to_csv(dest, index=False)
    log(f"Wrote {dest} ({len(out)} rows).")
    return out


def _fmt(x, nd=4) -> str:
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return "NA"
    return f"{x:.{nd}f}"


def _sig(p) -> str:
    if p is None or not np.isfinite(p):
        return "NA"
    if p < 0.05:
        return "significant at 5%"
    if p < 0.10:
        return "significant at 10%"
    return "not significant"


def write_summary(
    manifest: pd.DataFrame,
    panel: pd.DataFrame,
    states: pd.DataFrame,
    mom: pd.DataFrame,
) -> None:
    n_raw = int(manifest["asset_id"].nunique())
    n_elig = int(panel.loc[panel["eligible"], "asset_id"].nunique())
    n_weeks = int(states["week"].nunique())
    n_up_c = int((states["state_cooper_4w"] == "UP").sum())
    n_down_c = int((states["state_cooper_4w"] == "DOWN").sum())
    trans = states["transition"].value_counts(dropna=True).to_dict()

    def row(transition, k, weighting, state_def):
        m = mom[
            (mom["transition"] == transition)
            & (mom["holding_period"] == k)
            & (mom["weighting"] == weighting)
            & (mom["state_definition"] == state_def)
        ]
        if m.empty:
            return None
        return m.iloc[0]

    def line(r) -> str:
        if r is None:
            return "missing"
        return (
            f"W={_fmt(r.winner_return)} L={_fmt(r.loser_return)} "
            f"WML={_fmt(r.momentum_return)} t={_fmt(r.t_stat, 2)} "
            f"p={_fmt(r.p_value, 3)} N={int(r.N)}"
        )

    ew = "equal"
    k1 = 1
    unc = row("UNCONDITIONAL", k1, ew, "none")
    t2u = row("UP", k1, ew, "table2_past_1w")
    t2d = row("DOWN", k1, ew, "table2_past_1w")
    uu = row("UP->UP", k1, ew, "table3_asem_tian_1w")
    ud = row("UP->DOWN", k1, ew, "table3_asem_tian_1w")
    du = row("DOWN->UP", k1, ew, "table3_asem_tian_1w")
    dd = row("DOWN->DOWN", k1, ew, "table3_asem_tian_1w")
    uu2 = row("UP->UP", 2, ew, "table3_asem_tian_1w")

    paper_uu_k1 = 0.0119
    paper_uu_t = 2.31
    paper_ud_k1 = 0.0094
    paper_du_k1 = -0.0082
    paper_dd_k1 = 0.0071
    paper_up_k1 = 0.0089
    paper_down_k1 = 0.0065

    def match_sign_sig(r, paper_wml, paper_sig: bool) -> str:
        if r is None or not np.isfinite(r.momentum_return):
            return "NO"
        sign_ok = (r.momentum_return > 0) == (paper_wml > 0) or (
            abs(paper_wml) < 1e-12 and abs(r.momentum_return) < 1e-12
        )
        our_sig = bool(r.p_value < 0.05)
        if paper_sig:
            return "YES" if (r.momentum_return > 0 and our_sig) else "NO"
        return "YES" if (not our_sig) else "NO"

    # Core claim: UP-UP significant; others not. Use K=1 equal-weighted Table-3 def.
    core_ok = (
        uu is not None
        and uu.momentum_return > 0
        and uu.p_value < 0.05
        and ud is not None
        and ud.p_value >= 0.05
        and du is not None
        and du.p_value >= 0.05
        and dd is not None
        and dd.p_value >= 0.05
    )
    mag_close = (
        uu is not None
        and np.isfinite(uu.momentum_return)
        and abs(uu.momentum_return - paper_uu_k1) / paper_uu_k1 < 0.5
    )
    if core_ok and mag_close and abs(n_elig - 2130) / 2130 < 0.25:
        verdict = "A — CORE RESULT REPLICATED"
    elif core_ok or (
        uu is not None and uu.momentum_return > 0 and uu.p_value < 0.10
    ):
        verdict = "B — PARTIAL REPLICATION"
    else:
        verdict = "C — REPLICATION NOT CONFIRMED"

    text = f"""# Replication summary — Hsieh, Huang & Liu (2025)

Phase: core academic replication after reading the published PDF.
Script: `src/replicate_hsieh_2025.py`
Date written: {datetime.now().date().isoformat()}
Primary reported slice below: **J=2, K=1, equal-weighted, Table-3 1-week Asem–Tian states**.

## Answers

1. **¿Pudimos reconstruir correctamente el universo del paper?**
   Partially. Source is CoinMarketCap, period 2015–2023, Friday log returns,
   stablecoins excluded, mcap ≥ $1m, zero volume dropped, <20-week histories
   dropped. We observe Friday snapshots rather than the authors’ daily file,
   so the zero-volume filter uses Friday volume, not every day of the week.

2. **¿Cuál fue el número de criptomonedas?**
   Raw unique `asset_id` on Friday snapshots: **{n_raw}**.
   Unique coins ever passing Appendix A screens: **{n_elig}**.
   Paper Table 1 full sample: **2130**.
   Weeks in market-state file: **{n_weeks}**.

3. **¿Coincide aproximadamente con el paper?**
   {'YES, within 25%' if abs(n_elig - 2130) / 2130 < 0.25 else 'NO'}:
   replica eligible unique coins = {n_elig} vs paper 2130.

4. **¿Pudimos reconstruir el market return value-weighted?**
   Yes, using lagged market cap of eligible coins. Replica difference: Friday
   snapshots, not daily-to-Friday aggregation from a daily file.

5. **¿Pudimos reproducir UP/DOWN?**
   Two definitions, because the PDF contradicts itself:
   - Section 3.1 Cooper 4-week: UP={n_up_c}, DOWN={n_down_c}.
   - Tables 2–3 notes / Asem–Tian 1-week prior vs subsequent:
     {trans}.
   Primary table uses the Table 3 note (1-week prior and subsequent).

6. **¿Existe momentum unconditional?**
   {line(unc)}

7. **¿Existe momentum en UP→UP?**
   K=1: {line(uu)}
   K=2: {line(uu2)}
   Paper Table 3 K=1 WML=0.0119 (t=2.31); K=2 WML=0.0101 (t=2.45).

8. **¿Existe momentum en UP→DOWN?**
   {line(ud)}
   Paper Table 3 K=1 WML=0.0094 (t=0.93).

9. **¿Existe momentum en DOWN→UP?**
   {line(du)}
   Paper Table 3 K=1 WML=-0.0082 (t=-0.56).

10. **¿Existe momentum en DOWN→DOWN?**
    {line(dd)}
    Paper Table 3 K=1 WML=0.0071 (t=1.06).

11. **¿Los signos coinciden con el paper?**
    UNCONDITIONAL/Table2 UP K=1 paper WML={paper_up_k1}: replica {line(t2u)}
    Table2 DOWN K=1 paper WML={paper_down_k1}: replica {line(t2d)}
    UP→UP sign match: {'YES' if uu is not None and uu.momentum_return > 0 else 'NO'}
    UP→DOWN paper +0.0094: replica sign {'YES' if ud is not None and ud.momentum_return > 0 else 'NO'}
    DOWN→UP paper -0.0082: replica sign {'YES' if du is not None and du.momentum_return < 0 else 'NO'}
    DOWN→DOWN paper +0.0071: replica sign {'YES' if dd is not None and dd.momentum_return > 0 else 'NO'}

12. **¿Las magnitudes son similares?**
    UP→UP K=1 paper 0.0119 vs replica {_fmt(None if uu is None else uu.momentum_return)}.
    50% relative band: {'YES' if mag_close else 'NO'}.

13. **¿Los t-stats/significance son similares?**
    UP→UP paper t=2.31 (5%): replica t={_fmt(None if uu is None else uu.t_stat, 2)} ({_sig(None if uu is None else uu.p_value)}).
    Other transitions paper all insignificant at 5%: 
    UP→DOWN {_sig(None if ud is None else ud.p_value)};
    DOWN→UP {_sig(None if du is None else du.p_value)};
    DOWN→DOWN {_sig(None if dd is None else dd.p_value)}.

14. **¿Cuál es la principal diferencia frente al paper?**
    (a) Friday CMC *listings* snapshots, not the authors’ daily tape.
    (b) Stablecoin list is ours; the paper does not enumerate tickers.
    (c) Momentum legs equal-weighted (not stated in the PDF).
    (d) Newey–West lags = 4 (not stated).
    (e) Paper body uses Cooper 4-week states; Tables 2–3 notes use 1-week
    Asem–Tian states. We replicate Tables 2–3 using the table notes.

15. **¿Podemos afirmar que replicamos la conclusión central?**
    Central claim: WML significant only in UP→UP. This replica:
    UP→UP {_sig(None if uu is None else uu.p_value)};
    others as above.

## Comparison with the paper’s conclusions

Primary slice: J=2, K=1, equal-weighted, Table-3 1-week transitions.
Returns are weekly decimals, as in the paper.

| Hallazgo | Paper | Nuestra réplica | Match |
| --- | --- | --- | --- |
| Momentum unconditional | not a numbered main-text claim; Table 2 UP K=1 WML=0.0089 (t=1.80) | {line(unc)} | {'YES' if unc is not None and unc.momentum_return > 0 else 'NO'} |
| UP→UP momentum | 0.0119 (t=2.31), significant 5% | {line(uu)} | {match_sign_sig(uu, paper_uu_k1, True)} |
| UP→DOWN momentum | 0.0094 (t=0.93), not significant | {line(ud)} | {match_sign_sig(ud, paper_ud_k1, False)} |
| DOWN→UP momentum | -0.0082 (t=-0.56), not significant | {line(du)} | {match_sign_sig(du, paper_du_k1, False)} |
| DOWN→DOWN momentum | 0.0071 (t=1.06), not significant | {line(dd)} | {match_sign_sig(dd, paper_dd_k1, False)} |

Table 2 UP vs DOWN (past 1-week note), J=2 K=1 equal-weighted:

| Hallazgo | Paper | Nuestra réplica |
| --- | --- | --- |
| UP markets WML | 0.0089 (t=1.80) | {line(t2u)} |
| DOWN markets WML | 0.0065 (t=1.39) | {line(t2d)} |

### {verdict}
"""
    dest = RESULTS_DIR / "replication_summary.md"
    dest.write_text(text, encoding="utf-8")
    log(f"Wrote {dest}")
    log("VERDICT: " + verdict)


def main() -> int:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    log(f"Paper root: {PAPER_DIR}")
    download_raw()
    raw = load_friday_snapshots()
    log(f"Loaded Friday snapshots: {len(raw)} rows.")
    manifest = write_manifest(raw)
    panel = build_weekly_panel(raw)
    panel = apply_eligibility(panel)
    # Rewrite panel with eligibility flag for local use; keep file columns plus eligible.
    panel_out = panel[
        [
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
    ]
    panel_out.to_csv(PROCESSED_DIR / "crypto_weekly_panel.csv", index=False)
    states = build_market_states(panel)
    hold_rows = formation_and_hold_returns(panel)
    calendar = jegadeesh_titman_calendar(hold_rows)
    calendar = attach_states(calendar, states)
    calendar.to_csv(PROCESSED_DIR / "momentum_calendar.csv", index=False)
    mom = build_momentum_table(calendar)
    write_summary(manifest, panel, states, mom)
    log("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
