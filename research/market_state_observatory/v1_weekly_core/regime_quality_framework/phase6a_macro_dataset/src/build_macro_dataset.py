#!/usr/bin/env python3
"""Phase 6A: build a weekly Friday macro dataset, 2015–2023.

No models. No crypto. No 2024–2026. No scores. Dataset + audit only.
"""

from __future__ import annotations

import csv
import io
import json
import ssl
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from pandas.tseries.offsets import BDay, MonthEnd

PHASE6A = Path(__file__).resolve().parents[1]
RESULTS = PHASE6A / "results"
RAW_DIR = PHASE6A / "data" / "raw"

# Output sample: Fridays inside 2015-01-01 .. 2023-12-31.
SAMPLE_START = pd.Timestamp("2015-01-01")
SAMPLE_END = pd.Timestamp("2023-12-31")
HARD_END = pd.Timestamp("2023-12-31")
# Daily/weekly lookback so 12w changes exist on the first sample Friday.
LOOKBACK_START = pd.Timestamp("2014-10-01")
# Monthly M2 needs extra history because of the conservative release lag.
M2_LOOKBACK = pd.Timestamp("2014-01-01")

USER_AGENT = "Mozilla/5.0 (research; phase6a-macro-dataset)"
SSL_CTX = ssl.create_default_context()

# Fed DDP package hashes (preformatted / custom packages, date-bounded in URL).
H10_BROAD_DOLLAR = "122e3bcb627e8e53f1bf72a1a09cfb81"
H15_TREASURY = "bf17364827e38702b42a58cf8eaa3f78"
H41_RESERVE_BANK_CREDIT = "fa0b01b3825a8b2c8d1e0cd3e95bf6c1"
H6_MONEY_STOCK = "798e2796917702a5f8423426ba7e6b42"

# M2: conservative availability after month-end. Not an ALFRED vintage date.
M2_LAG_DAYS = 21


@dataclass
class SeriesAudit:
    name: str
    output_level_col: str
    source: str
    identifier: str
    raw_frequency: str
    first_raw: str = ""
    last_raw: str = ""
    n_raw: int = 0
    n_raw_missing: int = 0
    weekly_alignment: str = ""
    release_lag: str = ""
    vintage: str = ""
    contemporaneous: str = ""
    lookahead_risk: str = ""
    fallback: str = "none"
    notes: str = ""
    included: bool = True
    omit_reason: str = ""
    weekly_first: str = ""
    weekly_last: str = ""
    weekly_n: int = 0
    weekly_missing: int = 0
    weekly_missing_pct: float = 0.0
    extra: dict = field(default_factory=dict)


AUDITS: list[SeriesAudit] = []
WARNINGS: list[str] = []


def log(msg: str) -> None:
    print(msg, flush=True)


def assert_no_future(ts: pd.Series, label: str) -> None:
    ts = pd.to_datetime(ts, errors="coerce").dropna()
    if ts.empty:
        raise RuntimeError(f"{label}: no dates after parsing")
    mx = ts.max()
    if mx > HARD_END:
        raise RuntimeError(
            f"{label}: observation {mx.date()} exceeds hard end {HARD_END.date()}. "
            "2024–2026 must not be used."
        )
    if (ts.dt.year >= 2024).any():
        raise RuntimeError(f"{label}: found year>=2024")


def http_get(url: str, timeout: int = 60, retries: int = 4, min_bytes: int = 64) -> bytes:
    last_err: Exception | None = None
    for attempt in range(1, retries + 1):
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(req, timeout=timeout, context=SSL_CTX) as resp:
                payload = resp.read()
            if len(payload) >= min_bytes:
                return payload
            last_err = RuntimeError(f"empty/short payload ({len(payload)} bytes)")
            log(f"  retry {attempt}/{retries} empty payload")
        except (urllib.error.URLError, TimeoutError, ssl.SSLError) as exc:
            last_err = exc
            log(f"  retry {attempt}/{retries} {exc}")
        time.sleep(1.5 * attempt)
    raise RuntimeError(f"GET failed: {url}\n{last_err}")


def write_raw(name: str, payload: bytes) -> Path:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    path = RAW_DIR / name
    path.write_bytes(payload)
    return path


def parse_fed_ddp(text: str, value_col: str) -> pd.DataFrame:
    """Fed DDP CSV: 5 metadata rows, then Time Period + series columns."""
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
    out = out.dropna(subset=["date"]).sort_values("date").reset_index(drop=True)
    return out


def fed_ddp_url(rel: str, series: str, start: pd.Timestamp, end: pd.Timestamp) -> str:
    frm = start.strftime("%m/%d/%Y")
    to = end.strftime("%m/%d/%Y")
    return (
        "https://www.federalreserve.gov/datadownload/Output.aspx"
        f"?rel={rel}&series={series}&lastObs=&from={frm}&to={to}"
        "&filetype=csv&label=include&layout=seriescolumn"
    )


def asof_friday(
    daily: pd.DataFrame,
    weeks: pd.DatetimeIndex,
    *,
    value_col: str = "value",
    date_col: str = "date",
    asof_col: str | None = None,
    max_staleness_days: int | None = 7,
) -> pd.Series:
    """Last non-missing observation with as-of date on or before Friday."""
    use_asof = asof_col or date_col
    src = daily.dropna(subset=[value_col]).copy()
    src[date_col] = pd.to_datetime(src[date_col])
    src[use_asof] = pd.to_datetime(src[use_asof])
    src = src.sort_values(use_asof)
    keep = [use_asof, value_col]
    if date_col != use_asof:
        keep.insert(1, date_col)
    left = pd.DataFrame({"week": weeks})
    merged = pd.merge_asof(
        left,
        src[keep],
        left_on="week",
        right_on=use_asof,
        direction="backward",
    )
    if max_staleness_days is not None:
        lag = (merged["week"] - merged[use_asof]).dt.days
        merged.loc[lag > max_staleness_days, value_col] = np.nan
    return merged.set_index("week")[value_col]


def pct_change_weeks(level: pd.Series, n: int) -> pd.Series:
    prev = level.shift(n)
    out = level / prev - 1.0
    out[(prev == 0) | prev.isna() | level.isna()] = np.nan
    return out


def pp_change_weeks(level: pd.Series, n: int) -> pd.Series:
    return level - level.shift(n)


def raw_span(df: pd.DataFrame, value_col: str = "value") -> tuple[str, str, int, int]:
    d = df.dropna(subset=[value_col])
    if d.empty:
        return "", "", 0, int(df[value_col].isna().sum())
    return (
        d["date"].min().strftime("%Y-%m-%d"),
        d["date"].max().strftime("%Y-%m-%d"),
        int(len(d)),
        int(df[value_col].isna().sum()),
    )


def weekly_stats(weeks: pd.Series, s: pd.Series) -> tuple[str, str, int, int, float]:
    weeks = pd.to_datetime(weeks, errors="coerce")
    s = pd.to_numeric(s, errors="coerce")
    mask = s.notna()
    if not bool(mask.any()):
        return "", "", 0, int(s.isna().sum()), 100.0
    return (
        weeks[mask].min().strftime("%Y-%m-%d"),
        weeks[mask].max().strftime("%Y-%m-%d"),
        int(mask.sum()),
        int((~mask).sum()),
        100.0 * float((~mask).mean()),
    )


# ---------------------------------------------------------------------------
# Downloads (all date-bounded to HARD_END)
# ---------------------------------------------------------------------------


def download_h10_broad_dollar() -> pd.DataFrame:
    url = fed_ddp_url("H10", H10_BROAD_DOLLAR, LOOKBACK_START, HARD_END)
    log("H.10 Nominal Broad Dollar Index")
    payload = http_get(url)
    write_raw("h10_broad_dollar.csv", payload)
    df = parse_fed_ddp(payload.decode("utf-8"), "JRXWTFB_N.B")
    df = df[(df["date"] >= LOOKBACK_START) & (df["date"] <= HARD_END)]
    assert_no_future(df["date"], "H.10")
    return df


def download_h15_yields() -> pd.DataFrame:
    url = fed_ddp_url("H15", H15_TREASURY, LOOKBACK_START, HARD_END)
    log("H.15 Treasury 2Y / 10Y")
    payload = http_get(url)
    write_raw("h15_treasury_yields.csv", payload)
    text = payload.decode("utf-8")
    y2 = parse_fed_ddp(text, "RIFLGFCY02_N.B").rename(columns={"value": "us2y"})
    y10 = parse_fed_ddp(text, "RIFLGFCY10_N.B").rename(columns={"value": "us10y"})
    df = y2.merge(y10, on="date", how="outer").sort_values("date")
    df = df[(df["date"] >= LOOKBACK_START) & (df["date"] <= HARD_END)]
    assert_no_future(df["date"], "H.15")
    return df


def download_effr() -> pd.DataFrame:
    url = (
        "https://markets.newyorkfed.org/read"
        f"?startDt={LOOKBACK_START.strftime('%Y-%m-%d')}"
        f"&endDt={HARD_END.strftime('%Y-%m-%d')}"
        "&eventCodes=500&productCode=50&format=csv"
    )
    log("NY Fed EFFR")
    payload = http_get(url)
    write_raw("nyfed_effr.csv", payload)
    df = pd.read_csv(io.BytesIO(payload))
    rate_col = "Rate (%)" if "Rate (%)" in df.columns else None
    if rate_col is None:
        raise RuntimeError(f"EFFR: unexpected columns {list(df.columns)}")
    df["date"] = pd.to_datetime(df["Effective Date"])
    df["value"] = pd.to_numeric(df[rate_col], errors="coerce")
    if "Rate Type" in df.columns:
        df = df[df["Rate Type"].astype(str).str.upper().eq("EFFR")]
    df = df[(df["date"] >= LOOKBACK_START) & (df["date"] <= HARD_END)]
    assert_no_future(df["date"], "EFFR")
    # Published ~9:00 a.m. ET the next business day.
    df["asof"] = df["date"] + BDay(1)
    df = df.sort_values("date")[["date", "asof", "value"]].reset_index(drop=True)
    return df


def download_tips_10y() -> pd.DataFrame:
    frames = []
    for year in range(LOOKBACK_START.year, HARD_END.year + 1):
        if year >= 2024:
            raise RuntimeError("refusing Treasury year >= 2024")
        url = (
            "https://home.treasury.gov/resource-center/data-chart-center/"
            f"interest-rates/daily-treasury-rates.csv/{year}/all"
            "?type=daily_treasury_real_yield_curve"
            f"&field_tdr_date_value={year}&page&_format=csv"
        )
        log(f"Treasury TIPS real yield curve {year}")
        payload = http_get(url)
        write_raw(f"treasury_tips_real_{year}.csv", payload)
        text = payload.decode("utf-8")
        peek = text.lstrip()[:80].lower()
        if "date" not in peek:
            raise RuntimeError(f"Treasury TIPS {year}: unexpected payload {peek!r}")
        part = pd.read_csv(io.StringIO(text))
        if "10 YR" not in part.columns:
            raise RuntimeError(f"Treasury TIPS {year}: no 10 YR column {list(part.columns)}")
        part["date"] = pd.to_datetime(part["Date"])
        part["value"] = pd.to_numeric(part["10 YR"], errors="coerce")
        frames.append(part[["date", "value"]])
    df = pd.concat(frames, ignore_index=True)
    df = df[(df["date"] >= LOOKBACK_START) & (df["date"] <= HARD_END)]
    df = df.drop_duplicates("date").sort_values("date").reset_index(drop=True)
    assert_no_future(df["date"], "TIPS 10Y")
    if df["date"].dt.year.nunique() != (HARD_END.year - LOOKBACK_START.year + 1):
        WARNINGS.append("TIPS yearly files did not cover every year 2014–2023.")
    return df


def download_yahoo_daily(symbol: str, file_stub: str) -> pd.DataFrame:
    """Yahoo chart API with unix period2 capped at HARD_END. No 2024 requested."""
    start = datetime(LOOKBACK_START.year, LOOKBACK_START.month, LOOKBACK_START.day, tzinfo=timezone.utc)
    end = datetime(HARD_END.year, HARD_END.month, HARD_END.day, 23, 59, tzinfo=timezone.utc)
    p1 = int(start.timestamp())
    p2 = int(end.timestamp())
    enc = urllib.request.quote(symbol, safe="")
    url = (
        f"https://query1.finance.yahoo.com/v8/finance/chart/{enc}"
        f"?period1={p1}&period2={p2}&interval=1d&events=div%2Csplit"
    )
    log(f"Yahoo {symbol} period1={p1} period2={p2}")
    payload = http_get(url)
    write_raw(f"{file_stub}.json", payload)
    blob = json.loads(payload.decode("utf-8"))
    result = blob.get("chart", {}).get("result")
    if not result:
        raise RuntimeError(f"Yahoo {symbol}: empty chart {blob.get('chart', {}).get('error')}")
    res = result[0]
    ts = res.get("timestamp") or []
    close = (res.get("indicators") or {}).get("quote", [{}])[0].get("close") or []
    if not ts or not close:
        raise RuntimeError(f"Yahoo {symbol}: missing timestamp/close")
    utc_dates = pd.to_datetime(ts, unit="s", utc=True)
    try:
        dates = utc_dates.tz_convert("America/New_York").normalize().tz_localize(None)
    except Exception:
        dates = utc_dates.tz_localize(None).normalize()
    df = pd.DataFrame({"date": dates, "value": pd.to_numeric(close, errors="coerce")})
    df = df.dropna(subset=["date"]).drop_duplicates("date").sort_values("date")
    df = df[(df["date"] >= LOOKBACK_START) & (df["date"] <= HARD_END)]
    assert_no_future(df["date"], f"Yahoo {symbol}")
    return df.reset_index(drop=True)


def download_h41_reserve_bank_credit() -> pd.DataFrame:
    """Wednesday Reserve Bank credit. Single-series DDP package is date-bounded and reliable.

    The wide H.4.1 Table 1 package often returns an empty body for multi-year
    requests, so we do not scrape 180 columns to recover RESH4S (total factors
    supplying). Reserve Bank credit is the policy-relevant stock on H.4.1.
    """
    url = fed_ddp_url("H41", H41_RESERVE_BANK_CREDIT, LOOKBACK_START, HARD_END)
    log("H.4.1 Reserve Bank credit (Wednesday)")
    payload = http_get(url, timeout=90)
    write_raw("h41_reserve_bank_credit.csv", payload)
    if not payload.strip():
        raise RuntimeError("H.4.1 Reserve Bank credit: empty DDP payload")
    df = parse_fed_ddp(payload.decode("utf-8"), "RESH4SC_N.WW")
    df = df[(df["date"] >= LOOKBACK_START) & (df["date"] <= HARD_END)]
    assert_no_future(df["date"], "H.4.1")
    # H.4.1 Wednesday level is released Thursday; known by Friday.
    df["asof"] = df["date"] + BDay(1)
    return df


def download_h6_m2() -> pd.DataFrame:
    url = fed_ddp_url("H6", H6_MONEY_STOCK, M2_LOOKBACK, HARD_END)
    log("H.6 M2 (monthly, seasonally adjusted)")
    payload = http_get(url)
    write_raw("h6_money_stock.csv", payload)
    df = parse_fed_ddp(payload.decode("utf-8"), "M2.M")
    # Fed labels months as YYYY-MM; pandas parses as month-start.
    df["month_start"] = df["date"].dt.to_period("M").dt.to_timestamp()
    df["period_end"] = df["month_start"] + MonthEnd(0)
    df["asof"] = df["period_end"] + pd.Timedelta(days=M2_LAG_DAYS)
    df = df[(df["period_end"] <= HARD_END) & (df["month_start"] >= M2_LOOKBACK)]
    # Do not use a month whose conservative availability date is after HARD_END
    # to represent 2023; December 2023 M2 asof is 2024-01-21 and is therefore
    # NOT assigned to any 2023 Friday.
    assert_no_future(df["period_end"], "H.6 M2 period_end")
    if (df["month_start"].dt.year >= 2024).any():
        raise RuntimeError("H.6 M2 includes 2024+")
    return df.rename(columns={"date": "raw_label_date"})[["month_start", "period_end", "asof", "value"]]


def try_hy_spread() -> pd.DataFrame | None:
    """ICE BofA HY OAS lives on FRED. Omit if FRED is unreachable (do not invent)."""
    url = (
        "https://fred.stlouisfed.org/graph/fredgraph.csv"
        "?id=BAMLH0A0HYM2&cosd=2014-10-01&coed=2023-12-31"
    )
    log("FRED BAMLH0A0HYM2 (attempt; omit on failure)")
    try:
        payload = http_get(url, timeout=12, retries=1)
    except Exception as exc:
        AUDITS.append(
            SeriesAudit(
                name="High yield credit spread",
                output_level_col="HY_SPREAD",
                source="ICE BofA US High Yield Index Option-Adjusted Spread via FRED (BAMLH0A0HYM2)",
                identifier="BAMLH0A0HYM2",
                raw_frequency="daily (business day)",
                included=False,
                omit_reason=(
                    "FRED graph CSV timed out / was unreachable from this environment. "
                    "No FRED API key is present. No date-bounded official ICE CSV was used. "
                    f"Last error: {exc}"
                ),
                lookahead_risk="n/a (omitted)",
                notes="Not invented. Not replaced with a different credit spread.",
            )
        )
        WARNINGS.append(
            "HY_SPREAD omitted: FRED BAMLH0A0HYM2 could not be downloaded. "
            "Do not treat the panel as containing credit-spread information."
        )
        return None
    write_raw("fred_bamlh0a0hym2.csv", payload)
    df = pd.read_csv(io.BytesIO(payload))
    df["date"] = pd.to_datetime(df.iloc[:, 0], errors="coerce")
    df["value"] = pd.to_numeric(df.iloc[:, 1], errors="coerce")
    df = df.dropna(subset=["date"])
    df = df[(df["date"] >= LOOKBACK_START) & (df["date"] <= HARD_END)]
    assert_no_future(df["date"], "HY OAS")
    return df[["date", "value"]].sort_values("date").reset_index(drop=True)


# ---------------------------------------------------------------------------
# Weekly panel
# ---------------------------------------------------------------------------


def build_weekly() -> pd.DataFrame:
    # Align on a lookback Friday grid so 4w/12w changes exist on 2015-01-02.
    # Output rows are sliced to the 2015–2023 sample afterward.
    weeks_full = pd.date_range("2014-10-03", "2023-12-29", freq="W-FRI")
    weeks_out = pd.date_range("2015-01-02", "2023-12-29", freq="W-FRI")
    if weeks_out.min() < SAMPLE_START or weeks_out.max() > SAMPLE_END:
        raise RuntimeError("Friday grid escaped sample window")
    if (weeks_full.year >= 2024).any() or (weeks_out.year >= 2024).any():
        raise RuntimeError("Friday grid includes 2024+")
    weeks = weeks_full
    out = pd.DataFrame({"week": weeks})

    # 1. Broad dollar (DXY_LEVEL proxy — not ICE DXY)
    h10 = download_h10_broad_dollar()
    out["DXY_LEVEL"] = asof_friday(h10, weeks, max_staleness_days=7).values
    a = SeriesAudit(
        name="Broad US dollar (Fed Nominal Broad Dollar Index)",
        output_level_col="DXY_LEVEL",
        source="Board of Governors, H.10 Foreign Exchange Rates, Data Download Program",
        identifier="H10/H10/JRXWTFB_N.B (Nominal Broad Dollar Index, Jan 1997=100)",
        raw_frequency="daily (business day)",
        weekly_alignment="Last non-missing H.10 observation with calendar date on or before Friday; drop if older than 7 calendar days (holiday gap). No interpolation.",
        release_lag="H.10 daily indexes are typically available the same or next business day. Implementation uses observation date, not a verified same-day timestamp.",
        vintage="Current revised history from Board DDP. Not ALFRED vintage / real-time.",
        contemporaneous="Approximately yes for Friday close of the index; official release timing not verified tick-by-tick.",
        lookahead_risk="LOW",
        fallback="Requested ICE DXY was not used. This is the Fed trade-weighted broad dollar, not the ICE U.S. Dollar Index (DXY).",
        notes="Column prefix DXY_ is a project label for a dollar proxy. Do not interpret as ICE DXY.",
    )
    a.first_raw, a.last_raw, a.n_raw, a.n_raw_missing = raw_span(h10)
    AUDITS.append(a)

    # 2. Fed funds (EFFR with 1-business-day publication lag)
    effr = download_effr()
    out["FED_FUNDS"] = asof_friday(
        effr, weeks, asof_col="asof", max_staleness_days=7
    ).values
    a = SeriesAudit(
        name="Effective federal funds rate",
        output_level_col="FED_FUNDS",
        source="Federal Reserve Bank of New York, Markets Data API (EFFR)",
        identifier="NY Fed eventCodes=500, productCode=50, field Rate (%)",
        raw_frequency="daily (business day)",
        weekly_alignment="EFFR for date D is treated as available on D+1 business day (~9:00 a.m. ET). Friday uses the last EFFR whose publication date is on or before Friday (typically Thursday's rate). Stale >7 calendar days → missing. Friday's own EFFR is not used at t.",
        release_lag="One New York business day (NY Fed published methodology).",
        vintage="Current NY Fed history. EFFR revisions are possible; this is not a vintage tape.",
        contemporaneous="No: Friday's EFFR prints Monday. This implementation uses the lagged print.",
        lookahead_risk="LOW",
        notes="Not the target range; not H.15 monthly effective funds.",
    )
    a.first_raw, a.last_raw, a.n_raw, a.n_raw_missing = raw_span(effr)
    AUDITS.append(a)

    # 3–4. Treasury 2Y / 10Y
    h15 = download_h15_yields()
    out["US2Y"] = asof_friday(h15.rename(columns={"us2y": "value"}), weeks).values
    out["US10Y"] = asof_friday(h15.rename(columns={"us10y": "value"}), weeks).values
    for col, ident, label in (
        ("US2Y", "H15/H15/RIFLGFCY02_N.B", "2-year"),
        ("US10Y", "H15/H15/RIFLGFCY10_N.B", "10-year"),
    ):
        raw_col = "us2y" if col == "US2Y" else "us10y"
        tmp = h15[["date", raw_col]].rename(columns={raw_col: "value"})
        a = SeriesAudit(
            name=f"US Treasury {label} CMT yield",
            output_level_col=col,
            source="Board of Governors, H.15 Selected Interest Rates, Data Download Program",
            identifier=ident,
            raw_frequency="daily (business day)",
            weekly_alignment="Last non-missing yield on or before Friday; drop if older than 7 calendar days. No interpolation. ND codes treated as missing.",
            release_lag="H.15 daily yields are released on the same business day (afternoon). Implementation uses observation date.",
            vintage="Current Board DDP history, not ALFRED vintage.",
            contemporaneous="Yes at daily close for a business-day Friday; holiday Fridays use prior session.",
            lookahead_risk="LOW",
        )
        a.first_raw, a.last_raw, a.n_raw, a.n_raw_missing = raw_span(tmp)
        AUDITS.append(a)

    # 5. 10Y real yield
    tips = download_tips_10y()
    out["REAL10Y"] = asof_friday(tips, weeks).values
    a = SeriesAudit(
        name="US 10-year real yield (TIPS curve)",
        output_level_col="REAL10Y",
        source="U.S. Treasury, Daily Treasury Par Real Yield Curve Rates",
        identifier="daily_treasury_real_yield_curve column 10 YR; yearly CSV 2014–2023",
        raw_frequency="daily (business day)",
        weekly_alignment="Last non-missing 10Y real par yield on or before Friday; drop if older than 7 calendar days.",
        release_lag="Treasury publishes daily real par yields on the same business day. Implementation uses observation date.",
        vintage="Current Treasury historical files (revised history), not a locked vintage.",
        contemporaneous="Approximately yes on a business-day Friday.",
        lookahead_risk="LOW",
        notes="Par real yield from the TIPS curve, not TIPS ETF price.",
    )
    a.first_raw, a.last_raw, a.n_raw, a.n_raw_missing = raw_span(tips)
    AUDITS.append(a)

    # 6. VIX
    vix = download_yahoo_daily("^VIX", "yahoo_vix")
    out["VIX"] = asof_friday(vix, weeks).values
    a = SeriesAudit(
        name="VIX",
        output_level_col="VIX",
        source="Yahoo Finance chart API (CBOE Volatility Index close)",
        identifier="^VIX daily close; period1/period2 unix bounds 2014-10-01 .. 2023-12-31",
        raw_frequency="daily (session close)",
        weekly_alignment="Last non-missing close on or before Friday; drop if older than 7 calendar days.",
        release_lag="Index close is known at the cash close. Vendor timestamp converted America/New_York calendar date.",
        vintage="Vendor historical closes, not CBOE official CSV. Not a vintage tape.",
        contemporaneous="Yes for Friday close, subject to vendor completeness.",
        lookahead_risk="LOW",
        fallback="CBOE's single-file VIX_History.csv extends past 2023; it was not used so 2024–2026 rows would never be requested.",
        notes="Public market source with a hard period2 cutoff. Not claimed as exchange-official.",
    )
    a.first_raw, a.last_raw, a.n_raw, a.n_raw_missing = raw_span(vix)
    AUDITS.append(a)

    # 7. HY OAS — include only if a date-bounded download succeeds
    hy = try_hy_spread()
    hy_included = hy is not None
    if hy_included:
        out["HY_SPREAD"] = asof_friday(hy, weeks).values
        a = SeriesAudit(
            name="US high-yield option-adjusted spread",
            output_level_col="HY_SPREAD",
            source="ICE BofA US High Yield Index OAS via FRED graph CSV",
            identifier="BAMLH0A0HYM2",
            raw_frequency="daily (business day)",
            weekly_alignment="Last non-missing OAS on or before Friday; drop if older than 7 calendar days.",
            release_lag="Market OAS; FRED republishes ICE. Observation date used; not a verified same-day timestamp.",
            vintage="FRED current history (ICE/FRED revisions possible). Not ALFRED vintage.",
            contemporaneous="Approximately yes for a business-day Friday close.",
            lookahead_risk="LOW",
            notes="Percent (OAS). Changes are percentage points.",
        )
        a.first_raw, a.last_raw, a.n_raw, a.n_raw_missing = raw_span(hy)
        AUDITS.append(a)

    # 8. Nasdaq
    nasdaq = download_yahoo_daily("^IXIC", "yahoo_ixic")
    out["NASDAQ"] = asof_friday(nasdaq, weeks).values
    a = SeriesAudit(
        name="Nasdaq Composite (risk-asset proxy)",
        output_level_col="NASDAQ",
        source="Yahoo Finance chart API (NASDAQ Composite close)",
        identifier="^IXIC daily close; period1/period2 unix bounds 2014-10-01 .. 2023-12-31",
        raw_frequency="daily (session close)",
        weekly_alignment="Last non-missing close on or before Friday; drop if older than 7 calendar days.",
        release_lag="Cash close known at session end. Vendor timestamp converted America/New_York calendar date.",
        vintage="Vendor historical closes. Not CRSP. Not a vintage tape.",
        contemporaneous="Yes for Friday close, subject to vendor completeness.",
        lookahead_risk="LOW",
        notes="Price level; 4w/12w columns are simple returns, not point changes.",
    )
    a.first_raw, a.last_raw, a.n_raw, a.n_raw_missing = raw_span(nasdaq)
    AUDITS.append(a)

    # 9. Fed balance sheet proxy
    h41 = download_h41_reserve_bank_credit()
    out["FED_BALANCE_SHEET"] = asof_friday(
        h41, weeks, asof_col="asof", max_staleness_days=12
    ).values
    a = SeriesAudit(
        name="Federal Reserve balance-sheet proxy",
        output_level_col="FED_BALANCE_SHEET",
        source="Board of Governors, H.4.1 Factors Affecting Reserve Balances, Data Download Program (single-series package)",
        identifier="H41/H41/RESH4SC_N.WW — Reserve Bank credit, Wednesday level (USD millions)",
        raw_frequency="weekly (Wednesday level)",
        weekly_alignment="Wednesday level treated as available the next business day (typical Thursday H.4.1 release). Friday uses the last Wednesday print whose as-of date is on or before Friday. Stale >12 calendar days → missing. No interpolation.",
        release_lag="H.4.1 is released Thursday for the prior Wednesday. Friday of the same week can know that Wednesday level.",
        vintage="Current Board DDP history. H.4.1 is occasionally revised. Not WALCL vintage from ALFRED.",
        contemporaneous="Wednesday level is not a Friday market print; it is known by Friday under the Thursday-release convention used here.",
        lookahead_risk="LOW",
        fallback="FRED WALCL (Total Assets less eliminations) was not used: FRED CSV timed out. The wide H.4.1 Table 1 DDP package was empty on multi-year pulls, so RESH4S (total factors supplying) was not taken. This series is Reserve Bank credit, the main H.4.1 asset stock, not identical to WALCL.",
        notes="Units: millions of USD, as published (multiplier 1e6). Do not treat as FRED WALCL or as total assets including gold/SDR/Treasury currency.",
    )
    tmp = h41.rename(columns={"date": "date"})[["date", "value"]]
    a.first_raw, a.last_raw, a.n_raw, a.n_raw_missing = raw_span(tmp)
    AUDITS.append(a)

    # 10. M2
    m2 = download_h6_m2()
    m2_asof = m2.rename(columns={"period_end": "date"})[["date", "asof", "value"]]
    out["M2"] = asof_friday(
        m2_asof, weeks, asof_col="asof", max_staleness_days=None
    ).values
    a = SeriesAudit(
        name="US M2 money stock (seasonally adjusted)",
        output_level_col="M2",
        source="Board of Governors, H.6 Money Stock Measures, Data Download Program",
        identifier="H6/H6_M2/M2.M (seasonally adjusted monthly; multiplier 1e9 USD)",
        raw_frequency="monthly",
        weekly_alignment=(
            f"Month M is dated at month-end. Conservative availability = month-end + {M2_LAG_DAYS} calendar days. "
            "Friday receives the last monthly observation whose availability date is on or before Friday. "
            "The weekly series is a step function (held until the next conservatively dated release). "
            "Not interpolated. December 2023 M2 has availability in January 2024 and is therefore "
            "NOT assigned to any 2023 Friday."
        ),
        release_lag=(
            f"Assumed {M2_LAG_DAYS} days after month-end. This is an approximation of H.6 publication, "
            "not the actual historical release calendar and not ALFRED vintage."
        ),
        vintage="Current H.6 history (benchmark revisions). NOT true vintage/as-of money stock.",
        contemporaneous="No. Monthly, lagged, and revised.",
        lookahead_risk="HIGH",
        notes="Units: billions of USD as published. Do not claim real-time M2.",
    )
    raw_m2 = pd.DataFrame({"date": m2["period_end"], "value": m2["value"]})
    a.first_raw, a.last_raw, a.n_raw, a.n_raw_missing = raw_span(raw_m2)
    a.extra["n_months_with_asof_after_hard_end"] = int((m2["asof"] > HARD_END).sum())
    AUDITS.append(a)

    # Changes — only on the Friday panel (no intra-week interpolation).
    # Computed on the lookback grid, then sliced to 2015–2023 so early-2015
    # 4w/12w changes use 2014 Fridays rather than becoming missing.

    out["DXY_CHG_4W"] = pct_change_weeks(out["DXY_LEVEL"], 4)
    out["DXY_CHG_12W"] = pct_change_weeks(out["DXY_LEVEL"], 12)
    out["FED_FUNDS_CHG_4W"] = pp_change_weeks(out["FED_FUNDS"], 4)
    out["FED_FUNDS_CHG_12W"] = pp_change_weeks(out["FED_FUNDS"], 12)
    out["US2Y_CHG_4W"] = pp_change_weeks(out["US2Y"], 4)
    out["US2Y_CHG_12W"] = pp_change_weeks(out["US2Y"], 12)
    out["US10Y_CHG_4W"] = pp_change_weeks(out["US10Y"], 4)
    out["US10Y_CHG_12W"] = pp_change_weeks(out["US10Y"], 12)
    out["REAL10Y_CHG_4W"] = pp_change_weeks(out["REAL10Y"], 4)
    out["REAL10Y_CHG_12W"] = pp_change_weeks(out["REAL10Y"], 12)
    out["VIX_CHG_4W"] = pct_change_weeks(out["VIX"], 4)
    out["VIX_CHG_12W"] = pct_change_weeks(out["VIX"], 12)
    if hy_included:
        out["HY_SPREAD_CHG_4W"] = pp_change_weeks(out["HY_SPREAD"], 4)
        out["HY_SPREAD_CHG_12W"] = pp_change_weeks(out["HY_SPREAD"], 12)
    out["NASDAQ_RET_4W"] = pct_change_weeks(out["NASDAQ"], 4)
    out["NASDAQ_RET_12W"] = pct_change_weeks(out["NASDAQ"], 12)
    out["FED_BALANCE_CHG_4W"] = pct_change_weeks(out["FED_BALANCE_SHEET"], 4)
    out["FED_BALANCE_CHG_12W"] = pct_change_weeks(out["FED_BALANCE_SHEET"], 12)
    out["M2_CHG_4W"] = pct_change_weeks(out["M2"], 4)
    out["M2_CHG_12W"] = pct_change_weeks(out["M2"], 12)

    out = out[pd.to_datetime(out["week"]) >= SAMPLE_START].reset_index(drop=True)
    if not (pd.to_datetime(out["week"]).values == weeks_out.values).all():
        raise RuntimeError("output Friday grid mismatch after lookback slice")

    cols = [
        "week",
        "DXY_LEVEL",
        "DXY_CHG_4W",
        "DXY_CHG_12W",
        "FED_FUNDS",
        "FED_FUNDS_CHG_4W",
        "FED_FUNDS_CHG_12W",
        "US2Y",
        "US2Y_CHG_4W",
        "US2Y_CHG_12W",
        "US10Y",
        "US10Y_CHG_4W",
        "US10Y_CHG_12W",
        "REAL10Y",
        "REAL10Y_CHG_4W",
        "REAL10Y_CHG_12W",
        "VIX",
        "VIX_CHG_4W",
        "VIX_CHG_12W",
        *(
            ["HY_SPREAD", "HY_SPREAD_CHG_4W", "HY_SPREAD_CHG_12W"]
            if hy_included
            else []
        ),
        "NASDAQ",
        "NASDAQ_RET_4W",
        "NASDAQ_RET_12W",
        "FED_BALANCE_SHEET",
        "FED_BALANCE_CHG_4W",
        "FED_BALANCE_CHG_12W",
        "M2",
        "M2_CHG_4W",
        "M2_CHG_12W",
    ]
    out = out[cols]
    out["week"] = pd.to_datetime(out["week"]).dt.strftime("%Y-%m-%d")

    if pd.to_datetime(out["week"]).max() > HARD_END:
        raise RuntimeError("weekly panel exceeded hard end")
    if (pd.to_datetime(out["week"]).dt.year >= 2024).any():
        raise RuntimeError("weekly panel includes 2024+")

    for a in AUDITS:
        if not a.included:
            continue
        col = a.output_level_col
        if col not in out.columns:
            continue
        s = pd.to_numeric(out[col], errors="coerce")
        (
            a.weekly_first,
            a.weekly_last,
            a.weekly_n,
            a.weekly_missing,
            a.weekly_missing_pct,
        ) = weekly_stats(out["week"], s)

    return out


def md_escape(s: str) -> str:
    return s.replace("|", "\\|")


def fmt_num(x, nd=4) -> str:
    if x is None or (isinstance(x, float) and not np.isfinite(x)) or pd.isna(x):
        return ""
    if isinstance(x, (int, np.integer)):
        return str(int(x))
    return f"{float(x):.{nd}f}".rstrip("0").rstrip(".")


def write_audit(weekly: pd.DataFrame) -> None:
    n_weeks = len(weekly)
    lines: list[str] = []
    lines.append("# Phase 6A — Macro data audit")
    lines.append("")
    lines.append("Sample: Fridays **2015-01-02** through **2023-12-29** (calendar window 2015-01-01 … 2023-12-31).")
    lines.append("")
    lines.append("Question answered: *Do we have a clean, temporally defensible macro dataset that could have been known week by week?*")
    lines.append("")
    lines.append("This file is **not** a model, score, or crypto comparison. 2024–2026 was not downloaded or used.")
    lines.append("")
    lines.append("## Hard cutoff")
    lines.append("")
    lines.append("| bound | value |")
    lines.append("|---|---|")
    lines.append("| output first Friday | 2015-01-02 |")
    lines.append("| output last Friday | 2023-12-29 |")
    lines.append("| last raw observation allowed | 2023-12-31 |")
    lines.append("| lookback raw start (daily/weekly) | 2014-10-01 |")
    lines.append("| lookback Friday grid (not in output) | 2014-10-03 … 2014-12-26 |")
    lines.append("| M2 raw start | 2014-01 |")
    lines.append(f"| rows in `macro_weekly.csv` | {n_weeks} |")
    lines.append("")
    lines.append("Pre-2015 observations are used **only** as lookback for 4-week / 12-week changes. They are not output rows.")
    lines.append("")
    lines.append("## Lookahead scale")
    lines.append("")
    lines.append("| rating | meaning in this file |")
    lines.append("|---|---|")
    lines.append("| LOW | Friday alignment uses a market or same-week official print; residual risk is vendor/revision, not month-scale lag. |")
    lines.append("| MEDIUM | Timing is plausible but lag or revision is material. |")
    lines.append("| HIGH | Monthly / delayed / revised history. Not true vintage. Do not treat as known in real time. |")
    lines.append("")
    lines.append("No series is claimed as real-time unless the release convention was verified. None of these series are ALFRED vintages.")
    lines.append("")

    lines.append("## Series")
    lines.append("")
    for a in AUDITS:
        lines.append(f"### {a.output_level_col} — {a.name}")
        lines.append("")
        if not a.included:
            lines.append(f"**OMITTED.** {a.omit_reason}")
            lines.append("")
            lines.append(f"- Intended source: {a.source}")
            lines.append(f"- Identifier: `{a.identifier}`")
            lines.append(f"- Fallback used: {a.fallback}")
            lines.append(f"- Notes: {a.notes}")
            lines.append("")
            continue
        lines.append("| field | value |")
        lines.append("|---|---|")
        lines.append(f"| source | {md_escape(a.source)} |")
        lines.append(f"| identifier | `{a.identifier}` |")
        lines.append(f"| raw frequency | {a.raw_frequency} |")
        lines.append(f"| raw first date | {a.first_raw} |")
        lines.append(f"| raw last date | {a.last_raw} |")
        lines.append(f"| raw observations (non-missing) | {a.n_raw} |")
        lines.append(f"| raw missing (parsed rows) | {a.n_raw_missing} |")
        lines.append(f"| weekly alignment | {md_escape(a.weekly_alignment)} |")
        lines.append(f"| publication / release lag | {md_escape(a.release_lag)} |")
        lines.append(f"| contemporaneously observable? | {md_escape(a.contemporaneous)} |")
        lines.append(f"| revision / vintage | {md_escape(a.vintage)} |")
        lines.append(f"| lookahead_risk | **{a.lookahead_risk}** |")
        lines.append(f"| fallback | {md_escape(a.fallback)} |")
        lines.append(f"| weekly first non-missing | {a.weekly_first} |")
        lines.append(f"| weekly last non-missing | {a.weekly_last} |")
        lines.append(f"| weekly non-missing | {a.weekly_n} / {n_weeks} |")
        lines.append(f"| weekly missing | {a.weekly_missing} ({a.weekly_missing_pct:.2f}%) |")
        lines.append(f"| notes | {md_escape(a.notes)} |")
        lines.append("")

    lines.append("## A. Coverage")
    lines.append("")
    lines.append("| series | included | source | identifier | raw freq | raw first | raw last | lookahead |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for a in AUDITS:
        inc = "yes" if a.included else "NO"
        lines.append(
            f"| {a.output_level_col} | {inc} | {md_escape(a.source)} | `{a.identifier}` | "
            f"{a.raw_frequency} | {a.first_raw} | {a.last_raw} | {a.lookahead_risk} |"
        )
    lines.append("")

    lines.append("## B. Missingness (weekly output)")
    lines.append("")
    lines.append("| column | n missing | pct missing | first non-missing | last non-missing |")
    lines.append("|---|---|---|---|---|")
    for col in weekly.columns:
        if col == "week":
            continue
        s = pd.to_numeric(weekly[col], errors="coerce")
        first, last, n, miss, pct = weekly_stats(weekly["week"], s)
        lines.append(f"| {col} | {miss} | {pct:.2f}% | {first} | {last} |")
    lines.append("")

    show_cols = [
        "week",
        "DXY_LEVEL",
        "FED_FUNDS",
        "US2Y",
        "US10Y",
        "REAL10Y",
        "VIX",
        *(["HY_SPREAD"] if "HY_SPREAD" in weekly.columns else []),
        "NASDAQ",
        "FED_BALANCE_SHEET",
        "M2",
    ]
    lines.append("## C. First 5 weekly rows")
    lines.append("")
    lines.append("| " + " | ".join(show_cols) + " |")
    lines.append("|" + "|".join(["---"] * len(show_cols)) + "|")
    for _, row in weekly.head(5).iterrows():
        cells = [str(row["week"])] + [fmt_num(row[c], 4) for c in show_cols[1:]]
        lines.append("| " + " | ".join(cells) + " |")
    lines.append("")

    lines.append("## D. Last 5 weekly rows")
    lines.append("")
    lines.append("| " + " | ".join(show_cols) + " |")
    lines.append("|" + "|".join(["---"] * len(show_cols)) + "|")
    for _, row in weekly.tail(5).iterrows():
        cells = [str(row["week"])] + [fmt_num(row[c], 4) for c in show_cols[1:]]
        lines.append("| " + " | ".join(cells) + " |")
    lines.append("")

    lines.append("## E. Warnings")
    lines.append("")
    WARNINGS.append(
        "DXY_LEVEL is the Fed Nominal Broad Dollar Index, not ICE DXY. "
        "Do not compare levels to DXY futures quotes."
    )
    WARNINGS.append(
        "FED_BALANCE_SHEET is H.4.1 Reserve Bank credit (Wednesday), not FRED WALCL total assets."
    )
    WARNINGS.append(
        "M2 lookahead_risk is HIGH: monthly SA, assumed 21-day lag, revised history, not vintage."
    )
    WARNINGS.append(
        "VIX and NASDAQ closes come from Yahoo Finance with a unix period2 cutoff at 2023-12-31. "
        "Vendor data, not exchange official files."
    )
    WARNINGS.append(
        "4-week and 12-week changes at the start of 2015 use 2014 lookback. "
        "They are not out-of-sample relative to 2014 data; they are in-sample transformations."
    )
    WARNINGS.append("No interpolation. Daily holiday gaps use last-on-or-before with a short staleness cap.")
    WARNINGS.append("No 2024–2026 observations were requested from Fed DDP, NY Fed, Treasury year files, or Yahoo period2.")
    for w in WARNINGS:
        lines.append(f"- {w}")
    lines.append("")
    lines.append("## Transformations")
    lines.append("")
    lines.append("| group | columns | change definition |")
    lines.append("|---|---|---|")
    lines.append("| dollar index, VIX, Nasdaq, Fed BS, M2 | `*_CHG_*` / `NASDAQ_RET_*` | simple percent: `x_t / x_{t-n} - 1` on the Friday series |")
    lines.append("| funds, 2Y, 10Y, real 10Y | `*_CHG_*` | percentage-point difference: `x_t - x_{t-n}` |")
    lines.append("")
    lines.append("`n` is 4 or 12 **calendar weeks** on the Friday grid (`shift(4)` / `shift(12)`). No PCA, z-scores, or regimes.")
    lines.append("")
    lines.append("## What this phase did not do")
    lines.append("")
    lines.append("- logistic / any regression")
    lines.append("- merge onto crypto outcomes")
    lines.append("- inspect 2024–2026")
    lines.append("- variable selection on returns")
    lines.append("- macro score or Bull/Bear macro labels")
    lines.append("- modify Phase 3 / 4 / 5 or V1")
    lines.append("")

    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "MACRO_DATA_AUDIT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    weekly = build_weekly()
    out_csv = RESULTS / "macro_weekly.csv"
    weekly.to_csv(out_csv, index=False)
    write_audit(weekly)
    log(f"wrote {out_csv} rows={len(weekly)} cols={len(weekly.columns)}")
    log(f"wrote {RESULTS / 'MACRO_DATA_AUDIT.md'}")
    years = pd.to_datetime(weekly["week"]).dt.year
    log(f"week year min={years.min()} max={years.max()}")


if __name__ == "__main__":
    main()
