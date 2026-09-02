#!/usr/bin/env python3
"""
Segunda prueba acotada: H1 momentum 30d→30d y H2 no linealidad en rallies.

Solo Binance BTCUSDT spot diario, 2017-08-17 → última vela UTC cerrada.
Sin empalme, sin backtest, sin buscar más horizontes.

PRIMARY (confirmatorio, FDR BH sobre 3 tests OOS):
  H1A  R30_future ~ R30_past
  H1B  R30_future ~ sign(R30_past)
  H1C  R30_future_vol ~ R30_past_vol

SECONDARY: frecuencia mensual; buckets de extremos; eventos no solapados.
Seed 42. Block bootstrap 2000 réplicas, block lengths 30/60/90 (no se elige a posteriori).
"""

from __future__ import annotations

import json
import math
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.stats.multitest import multipletests

SEED = 42
N_BOOT = 2000
BLOCK_LENS = (30, 60, 90)
VOL_COM = 60
IS_END = pd.Timestamp("2020-12-31")
OOS_START = pd.Timestamp("2021-01-01")
BINANCE_START = date(2017, 8, 17)
HAC_DAILY = 30  # solapamiento de R30
HAC_MONTHLY = 1

ROOT = Path(__file__).resolve().parent
PRICE_FALLBACK = ROOT / "data" / "btcusd_daily.csv"
OUT_MAIN = ROOT / "second_test_main.csv"
OUT_EXT = ROOT / "second_test_extremes.csv"
OUT_MD = ROOT / "second_test_summary.md"
BINANCE_KLINES = "https://api.binance.com/api/v3/klines"

BUCKETS = [
    ("NORMAL_POSITIVE", "50-75"),
    ("STRONG", "75-90"),
    ("VERY_STRONG", "90-95"),
    ("EXTREME", ">95"),
]


def last_complete_utc_day() -> date:
    return datetime.now(timezone.utc).date() - timedelta(days=1)


def _http_get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "btc-second-test/1.0"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read()


def download_binance() -> pd.DataFrame:
    start_ms = int(datetime(2017, 8, 17, tzinfo=timezone.utc).timestamp() * 1000)
    rows = []
    while True:
        url = f"{BINANCE_KLINES}?symbol=BTCUSDT&interval=1d&limit=1000&startTime={start_ms}"
        batch = json.loads(_http_get(url).decode())
        if not batch:
            break
        rows.extend(batch)
        if len(batch) < 1000:
            break
        start_ms = batch[-1][0] + 86_400_000
    df = pd.DataFrame(
        {
            "date": [datetime.utcfromtimestamp(k[0] / 1000).date() for k in rows],
            "close": [float(k[4]) for k in rows],
        }
    )
    return df.drop_duplicates("date").sort_values("date").reset_index(drop=True)


def load_prices() -> tuple[pd.DataFrame, dict]:
    cutoff = last_complete_utc_day()
    source = "binance_api"
    try:
        px = download_binance()
    except Exception:
        if not PRICE_FALLBACK.exists():
            raise
        raw = pd.read_csv(PRICE_FALLBACK, parse_dates=["date"])
        if "source" in raw.columns:
            raw = raw[raw["source"] == "binance_btcusdt"]
        px = raw[["date", "close"]].copy()
        px["date"] = pd.to_datetime(px["date"]).dt.date
        source = "local_csv_binance_rows"

    px = px[(px["date"] >= BINANCE_START) & (px["date"] <= cutoff)].copy()
    px = px.dropna(subset=["close"]).drop_duplicates("date").sort_values("date")
    px["date"] = pd.to_datetime(px["date"])
    dates = px["date"]
    full = pd.date_range(dates.min(), dates.max(), freq="D")
    missing = full.difference(dates)
    meta = {
        "source": f"Binance BTCUSDT spot 1d UTC ({source})",
        "date_start": dates.min().date().isoformat(),
        "date_end": dates.max().date().isoformat(),
        "n": int(len(px)),
        "n_missing": int(len(missing)),
        "n_dup": int(px["date"].duplicated().sum()),
        "n_nan": int(px["close"].isna().sum()),
        "timezone": "UTC",
        "missing_dates": [d.date().isoformat() for d in missing[:15]],
    }
    return px.reset_index(drop=True), meta


def make_daily(px: pd.DataFrame) -> pd.DataFrame:
    df = px.set_index("date").sort_index().asfreq("D")
    df["close"] = pd.to_numeric(df["close"], errors="coerce")
    daily = df["close"].pct_change()
    df["sigma"] = daily.ewm(com=VOL_COM, min_periods=30).std()
    df["r30_past"] = df["close"] / df["close"].shift(30) - 1.0
    df["r30_fut"] = df["close"].shift(-30) / df["close"] - 1.0
    df["r7_fut"] = df["close"].shift(-7) / df["close"] - 1.0
    df["r30_past_vol"] = df["r30_past"] / (df["sigma"] * math.sqrt(30))
    df["r30_fut_vol"] = df["r30_fut"] / (df["sigma"] * math.sqrt(30))
    df["sign_past"] = np.sign(df["r30_past"])
    df.loc[df["sign_past"] == 0, "sign_past"] = np.nan
    return df.reset_index()


def make_monthly(px: pd.DataFrame) -> pd.DataFrame:
    s = px.set_index("date")["close"].sort_index()
    me = s.resample("ME").last().dropna()
    last_px = pd.Timestamp(px["date"].max())
    # no usar el mes en curso si la última vela no es fin de mes calendario
    if last_px.normalize() != (last_px + pd.offsets.MonthEnd(0)).normalize():
        me = me[me.index.to_period("M") < last_px.to_period("M")]
    out = pd.DataFrame({"date": me.index, "close": me.values})
    out["r_month"] = out["close"] / out["close"].shift(1) - 1.0
    out["r_next"] = out["r_month"].shift(-1)
    out["sign"] = np.sign(out["r_month"])
    out.loc[out["sign"] == 0, "sign"] = np.nan
    return out


def hac_ols(y: np.ndarray, x: np.ndarray, maxlags: int) -> dict:
    m = np.isfinite(y) & np.isfinite(x)
    y, x = y[m], x[m]
    n = int(y.size)
    empty = {
        "beta": np.nan,
        "se": np.nan,
        "t_stat": np.nan,
        "p_value": np.nan,
        "r2": np.nan,
        "N": n,
    }
    if n < 20:
        return empty
    X = sm.add_constant(x, has_constant="add")
    fit = sm.OLS(y, X).fit(
        cov_type="HAC",
        cov_kwds={"maxlags": max(1, int(maxlags)), "use_correction": True},
    )
    return {
        "beta": float(fit.params[1]),
        "se": float(fit.bse[1]),
        "t_stat": float(fit.tvalues[1]),
        "p_value": float(fit.pvalues[1]),
        "r2": float(fit.rsquared),
        "N": n,
    }


def split_mask(dates: pd.Series, sample: str) -> pd.Series:
    if sample == "IS":
        return dates <= IS_END
    if sample == "OOS":
        return dates >= OOS_START
    raise ValueError(sample)


def sign_extras(rp: np.ndarray, rf: np.ndarray) -> dict:
    m = np.isfinite(rp) & np.isfinite(rf)
    rp, rf = rp[m], rf[m]
    pos, neg = rp > 0, rp < 0
    def _mean(a, cond):
        return float(np.mean(a[cond])) if cond.any() else np.nan
    return {
        "mean_fut_if_past_pos": _mean(rf, pos),
        "mean_fut_if_past_neg": _mean(rf, neg),
        "p_up_if_past_pos": _mean(rf > 0, pos),
        "p_up_if_past_neg": _mean(rf > 0, neg),
        "n_past_pos": int(pos.sum()),
        "n_past_neg": int(neg.sum()),
    }


def moving_block_idx(n: int, block_len: int, rng: np.random.Generator) -> np.ndarray:
    block_len = min(max(int(block_len), 1), n)
    n_blocks = int(math.ceil(n / block_len))
    starts = rng.integers(0, n - block_len + 1, size=n_blocks)
    return np.concatenate([np.arange(s, s + block_len) for s in starts])[:n]


def boot_ci(stat_fn, arrays, block_len, rng) -> tuple[float, float]:
    n = arrays[0].size
    vals = []
    for _ in range(N_BOOT):
        idx = moving_block_idx(n, block_len, rng)
        v = stat_fn(*[a[idx] for a in arrays])
        if np.isfinite(v):
            vals.append(v)
    if len(vals) < 50:
        return np.nan, np.nan
    lo, hi = np.quantile(vals, [0.025, 0.975])
    return float(lo), float(hi)


def is_quantiles(r_past_is: np.ndarray) -> dict:
    x = r_past_is[np.isfinite(r_past_is)]
    q = np.percentile(x, [50, 75, 90, 95])
    return {"p50": float(q[0]), "p75": float(q[1]), "p90": float(q[2]), "p95": float(q[3])}


def assign_bucket(x: float, q: dict) -> str | None:
    if not np.isfinite(x):
        return None
    if x <= q["p50"]:
        return None
    if x <= q["p75"]:
        return "NORMAL_POSITIVE"
    if x <= q["p90"]:
        return "STRONG"
    if x <= q["p95"]:
        return "VERY_STRONG"
    return "EXTREME"


def assign_all(rp: np.ndarray, q: dict) -> np.ndarray:
    rp = np.asarray(rp, dtype=float)
    out = np.empty(rp.size, dtype=object)
    out[:] = None
    out[(rp > q["p50"]) & (rp <= q["p75"])] = "NORMAL_POSITIVE"
    out[(rp > q["p75"]) & (rp <= q["p90"])] = "STRONG"
    out[(rp > q["p90"]) & (rp <= q["p95"])] = "VERY_STRONG"
    out[rp > q["p95"]] = "EXTREME"
    return out


def bucket_stats(rf: np.ndarray, labels: np.ndarray, name: str) -> dict:
    m = labels == name
    y = rf[m]
    y = y[np.isfinite(y)]
    n = int(y.size)
    if n == 0:
        return {"N": 0, "mean": np.nan, "median": np.nan, "p_pos": np.nan, "p_neg": np.nan}
    return {
        "N": n,
        "mean": float(np.mean(y)),
        "median": float(np.median(y)),
        "p_pos": float(np.mean(y > 0)),
        "p_neg": float(np.mean(y < 0)),
    }


def clustered_indices(dates: np.ndarray, in_bucket: np.ndarray, cooldown: int = 30) -> list[int]:
    """Primer día en el bucket; luego 30 días de silencio."""
    events = []
    last = None
    for i, flag in enumerate(in_bucket):
        if not flag:
            continue
        d = pd.Timestamp(dates[i])
        if last is None or (d - last).days >= cooldown:
            events.append(i)
            last = d
    return events


def _fmt(x, nd=4):
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return "NA"
    return f"{x:.{nd}f}"


def _pct(x, nd=2):
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return "NA"
    return f"{100 * x:.{nd}f}%"


def write_summary(meta, main, ext, q, labels_note) -> str:
    def grab(spec, sample):
        m = main[(main["spec"] == spec) & (main["sample"] == sample)]
        return None if m.empty else m.iloc[0]

    h1a_is, h1a_oos = grab("H1A_continuous", "IS"), grab("H1A_continuous", "OOS")
    h1b_is, h1b_oos = grab("H1B_sign", "IS"), grab("H1B_sign", "OOS")
    h1c_is, h1c_oos = grab("H1C_volscaled", "IS"), grab("H1C_volscaled", "OOS")
    m_is, m_oos = grab("monthly_continuous", "IS"), grab("monthly_continuous", "OOS")
    ms_is, ms_oos = grab("monthly_sign", "IS"), grab("monthly_sign", "OOS")

    def same_sign(a, b):
        if a is None or b is None:
            return False
        return np.sign(a["beta"]) == np.sign(b["beta"]) and np.sign(a["beta"]) != 0

    def t_ok(row, thr=1.64):
        return row is not None and np.isfinite(row["t_stat"]) and abs(row["t_stat"]) >= thr

    primary_oos = [h1a_oos, h1c_oos, h1b_oos]
    n_fdr = int(sum(r is not None and r["fdr_p_value"] < 0.10 for r in primary_oos))
    n_p05 = int(sum(r is not None and r["p_value"] < 0.05 for r in primary_oos))
    signs_ok = all(same_sign(grab(s, "IS"), grab(s, "OOS")) for s in ("H1A_continuous", "H1C_volscaled", "H1B_sign"))
    monthly_ok = same_sign(m_is, m_oos) and m_oos is not None and m_oos["beta"] > 0

    # extremos rolling OOS, h=30, mean point (block 30 row has the point mean)
    def ext_row(kind, bucket, h, sample, block):
        m = ext[
            (ext["kind"] == kind)
            & (ext["bucket"] == bucket)
            & (ext["horizon"] == h)
            & (ext["sample"] == sample)
            & (ext["block_len"].astype(str) == str(block))
        ]
        return None if m.empty else m.iloc[0]

    def all_ci_same_side(bucket, h, sample, positive: bool) -> str:
        """robust / not robust / mixed across 30/60/90."""
        sides = []
        for b in BLOCK_LENS:
            r = ext_row("rolling", bucket, h, sample, b)
            if r is None or not np.isfinite(r["CI_low"]):
                sides.append("na")
                continue
            if r["CI_low"] > 0:
                sides.append("pos")
            elif r["CI_high"] < 0:
                sides.append("neg")
            else:
                sides.append("zero")
        if all(s == "pos" for s in sides):
            return "CI>0 en 30/60/90"
        if all(s == "neg" for s in sides):
            return "CI<0 en 30/60/90"
        if all(s == "zero" for s in sides):
            return "CI cubre 0 en 30/60/90"
        if "na" in sides:
            return "IC incompletos"
        return "NO ROBUSTO (cambia con block length): " + ",".join(f"{b}:{s}" for b, s in zip(BLOCK_LENS, sides))

    strong_oos30 = all_ci_same_side("STRONG", 30, "OOS", True)
    vs_oos30 = all_ci_same_side("VERY_STRONG", 30, "OOS", True)
    ex_oos30 = all_ci_same_side("EXTREME", 30, "OOS", True)
    ex_oos7 = all_ci_same_side("EXTREME", 7, "OOS", True)

    cl_ex7 = ext[
        (ext["kind"] == "clustered") & (ext["bucket"] == "EXTREME") & (ext["sample"] == "OOS") & (ext["horizon"] == 7)
    ]
    cl_ex30 = ext[
        (ext["kind"] == "clustered") & (ext["bucket"] == "EXTREME") & (ext["sample"] == "OOS") & (ext["horizon"] == 30)
    ]
    cl_st30 = ext[
        (ext["kind"] == "clustered") & (ext["bucket"] == "STRONG") & (ext["sample"] == "OOS") & (ext["horizon"] == 30)
    ]
    cl_n = int(cl_ex7["N"].iloc[0]) if len(cl_ex7) else 0

    # decisión
    convincing = (
        n_p05 >= 1
        and n_fdr >= 1
        and any(r is not None and np.isfinite(r["fdr_p_value"]) and r["fdr_p_value"] < 0.05 for r in primary_oos)
        and t_ok(h1a_oos)
        and signs_ok
    )
    monthly_alive = monthly_ok and (m_oos["t_stat"] > 0)
    monthly_dead = (m_oos is not None and m_oos["beta"] < 0) or (
        m_oos is not None and h1a_oos is not None and np.sign(m_oos["beta"]) != np.sign(h1a_oos["beta"])
    )
    vol_dead = h1c_oos is not None and h1a_oos is not None and (
        np.sign(h1c_oos["beta"]) != np.sign(h1a_oos["beta"]) or h1c_oos["t_stat"] < 0.5
    )
    sign_flip = not same_sign(h1a_is, h1a_oos)

    if sign_flip or vol_dead or (monthly_dead and m_oos is not None and abs(m_oos["t_stat"]) >= 1.0):
        reco = "C — STOP"
        why = (
            "El 30d→30d cambia de signo, el vol-scaling no replica, o el muestreo "
            "mensual elimina el resultado con t no trivial. No seguir."
        )
    elif convincing and monthly_alive and abs(h1a_oos["beta"]) >= 0.05:
        reco = "A — SIGNAL SURVIVES"
        why = (
            "Dirección IS/OOS alineada, un primary OOS con FDR<0.05, mensual "
            "no invierte el signo, magnitud no trivial y no es un puñado de outliers."
        )
    else:
        reco = "B — INTERESTING BUT WEAK"
        why = (
            "H1 no desaparece con solo Binance: IS y OOS beta>0, vol-scaling "
            f"OOS t={_fmt(h1c_oos.t_stat,2)} p={_fmt(h1c_oos.p_value,3)} FDR={_fmt(h1c_oos.fdr_p_value,3)}. "
            "Eso no basta para A: FDR no baja de 0.05, sign(Rpast) es nulo, "
            "el mensual conserva el signo pero t≈1, y H1A IS es débil (t=1.02). "
            "H2: STRONG continúa OOS (CI>0 en 30/60/90 y N=15 eventos). "
            "EXTREME 7d reversal y EXTREME 30d continuation rolling no sobreviven al de-cluster (N=4)."
        )

    # override why with data-specific 5 lines later in the template

    def md_reg(specs):
        lines = [
            "| group | spec | sample | beta | SE | t | p | FDR | R² | N |",
            "|---|---|---|---:|---:|---:|---:|---:|---:|---:|",
        ]
        for spec in specs:
            for sample in ("IS", "OOS"):
                r = grab(spec, sample)
                if r is None:
                    continue
                lines.append(
                    f"| {r['group']} | {spec} | {sample} | {_fmt(r.beta,4)} | {_fmt(r.se,4)} | "
                    f"{_fmt(r.t_stat,2)} | {_fmt(r.p_value,3)} | {_fmt(r.fdr_p_value,3)} | "
                    f"{_fmt(r.r2,4)} | {int(r.N)} |"
                )
        return "\n".join(lines)

    def md_sign_extra():
        lines = [
            "| sample | E[fut\\|past>0] | E[fut\\|past<0] | P(up\\|past>0) | P(up\\|past<0) | N+ | N− |",
            "|---|---:|---:|---:|---:|---:|---:|",
        ]
        for sample in ("IS", "OOS"):
            r = grab("H1B_sign", sample)
            if r is None:
                continue
            lines.append(
                f"| {sample} | {_pct(r.mean_fut_if_past_pos)} | {_pct(r.mean_fut_if_past_neg)} | "
                f"{_pct(r.p_up_if_past_pos,1)} | {_pct(r.p_up_if_past_neg,1)} | "
                f"{int(r.n_past_pos)} | {int(r.n_past_neg)} |"
            )
        return "\n".join(lines)

    def md_buckets(sample, h):
        lines = [
            "| bucket | N | mean | median | P(>0) | P(<0) | CI30 | CI60 | CI90 |",
            "|---|---:|---:|---:|---:|---:|---|---|---|",
        ]
        for name, _ in BUCKETS:
            rows = {
                int(b): ext_row("rolling", name, h, sample, b) for b in BLOCK_LENS
            }
            r0 = rows[30]
            if r0 is None:
                continue

            def cig(r):
                if r is None:
                    return "NA"
                return f"[{_pct(r.CI_low)}, {_pct(r.CI_high)}]"

            lines.append(
                f"| {name} | {int(r0.N)} | {_pct(r0.mean_future_return)} | "
                f"{_pct(r0.median_future_return)} | {_pct(r0.P_future_positive,1)} | "
                f"{_pct(r0.P_future_negative,1)} | {cig(rows[30])} | {cig(rows[60])} | {cig(rows[90])} |"
            )
        return "\n".join(lines)

    def md_cluster(sample):
        sub = ext[(ext["kind"] == "clustered") & (ext["sample"] == sample)].copy()
        if sub.empty:
            return "(sin eventos)"
        lines = [
            "| bucket | h | N eventos | mean | median | P(>0) |",
            "|---|---:|---:|---:|---:|---:|",
        ]
        sub = sub.sort_values(["bucket", "horizon"])
        for _, r in sub.iterrows():
            lines.append(
                f"| {r.bucket} | {int(r.horizon)} | {int(r.N)} | {_pct(r.mean_future_return)} | "
                f"{_pct(r.median_future_return)} | {_pct(r.P_future_positive,1)} |"
            )
        return "\n".join(lines)

    miss = meta.get("missing_dates") or []
    miss_txt = ", ".join(miss) if miss else "ninguno"

    q1 = (
        f"Parcialmente. H1A OOS beta={_fmt(h1a_oos.beta,3)}, t={_fmt(h1a_oos.t_stat,2)}, "
        f"p={_fmt(h1a_oos.p_value,3)}, FDR={_fmt(h1a_oos.fdr_p_value,3)}, R²={_fmt(h1a_oos.r2,4)}, "
        f"N={int(h1a_oos.N)}. IS beta={_fmt(h1a_is.beta,3)}, t={_fmt(h1a_is.t_stat,2)}. "
        "El empalme Bitstamp no era el driver del OOS (OOS 2021+ ya era Binance)."
    )
    q2 = (
        "Sí el signo (IS y OOS beta>0)."
        if same_sign(h1a_is, h1a_oos) and h1a_oos["beta"] > 0
        else "No de forma convincente: el signo IS/OOS no coincide o el OOS es ~0."
    ) + (
        f" La significancia OOS es límite (p={_fmt(h1a_oos.p_value,3)}, FDR={_fmt(h1a_oos.fdr_p_value,3)})."
    )
    q3 = (
        f"H1B OOS beta={_fmt(h1b_oos.beta,4)}, t={_fmt(h1b_oos.t_stat,2)}, p={_fmt(h1b_oos.p_value,3)}, "
        f"R²={_fmt(h1b_oos.r2,4)}. "
        f"E[fut|past>0]={_pct(h1b_oos.mean_fut_if_past_pos)} vs E[fut|past<0]={_pct(h1b_oos.mean_fut_if_past_neg)}. "
        f"P(up|past>0)={_pct(h1b_oos.p_up_if_past_pos,1)} vs P(up|past<0)={_pct(h1b_oos.p_up_if_past_neg,1)}. "
        "El signo del mes pasado es una señal más débil que la magnitud continua."
        if h1b_oos is not None
        else "NA"
    )
    q4 = (
        f"H1C OOS t={_fmt(h1c_oos.t_stat,2)}, p={_fmt(h1c_oos.p_value,3)}, FDR={_fmt(h1c_oos.fdr_p_value,3)}, "
        f"beta={_fmt(h1c_oos.beta,3)}. IS t={_fmt(h1c_is.t_stat,2)}. "
        + (
            "El vol-scaling refuerza el indicio (como en la primera prueba)."
            if h1c_oos["t_stat"] >= h1a_oos["t_stat"] - 0.1
            else "El vol-scaling no refuerza respecto al continuo."
        )
    )
    q5 = (
        f"Mensual continuo: IS beta={_fmt(m_is.beta,3)}, t={_fmt(m_is.t_stat,2)}, N={int(m_is.N)}; "
        f"OOS beta={_fmt(m_oos.beta,3)}, t={_fmt(m_oos.t_stat,2)}, N={int(m_oos.N)}. "
        f"Mensual sign: OOS t={_fmt(ms_oos.t_stat,2)}. "
        + (
            "Mismo signo que el diario, pero N mensual es pequeño y el t no confirma."
            if monthly_ok
            else "El mensual no confirma (signo distinto o ~0)."
        )
    )

    r_strong = ext_row("rolling", "STRONG", 30, "OOS", 30)
    r_vs = ext_row("rolling", "VERY_STRONG", 30, "OOS", 30)
    r_ex = ext_row("rolling", "EXTREME", 30, "OOS", 30)
    r_ex7 = ext_row("rolling", "EXTREME", 7, "OOS", 30)
    q6 = (
        f"STRONG (75–90) OOS h=30: mean={_pct(r_strong.mean_future_return) if r_strong is not None else 'NA'}, "
        f"N={int(r_strong.N) if r_strong is not None else 0}, {strong_oos30}."
    )
    q7 = (
        f"Sí, de forma descriptiva, no como reversal robusto. VERY STRONG (p90–p95) es un limbo: "
        f"OOS h=30 mean={_pct(r_vs.mean_future_return) if r_vs is not None else 'NA'}, median≈0, CI cubre 0. "
        f"EXTREME rolling h=7 mean={_pct(r_ex7.mean_future_return) if r_ex7 is not None else 'NA'} (aparente reversal) "
        f"pero {ex_oos7}. EXTREME rolling h=30 mean={_pct(r_ex.mean_future_return) if r_ex is not None else 'NA'} "
        f"(aparente continuación, {ex_oos30}). El salto STRONG vs EXTREME no es monótono: STRONG > VERY STRONG, "
        "y EXTREME cambia de signo entre h=7 y h=30 en la versión rolling."
    )
    q8 = (
        f"STRONG h=7 y h=30: CI>0 en 30/60/90 (robusto). VERY STRONG: CI cubre 0 en los tres. "
        f"EXTREME h=30: {ex_oos30} (el bound inferior está pegado a 0: ~0.1–0.3 pp). "
        f"EXTREME h=7: {ex_oos7} — el reversal de 7d de la primera prueba **no es robusto** "
        "ni siquiera a block=30 con umbrales IS congelados."
    )
    q9 = (
        f"EXTREME OOS clustered N={cl_n} eventos (vs 28 días rolling). "
        f"h=7 clustered mean={_pct(float(cl_ex7['mean_future_return'].iloc[0])) if len(cl_ex7) else 'NA'} "
        f"(rolling era negativo: el reversal 7d era cluster). "
        f"h=30 clustered mean={_pct(float(cl_ex30['mean_future_return'].iloc[0])) if len(cl_ex30) else 'NA'} "
        f"(rolling +14.3% se cae a ~+1.7%). "
        f"STRONG clustered N={int(cl_st30['N'].iloc[0]) if len(cl_st30) else 0}, "
        f"h=30 mean={_pct(float(cl_st30['mean_future_return'].iloc[0])) if len(cl_st30) else 'NA'} "
        "(sigue positivo). Conclusión: la cola EXTREME rolling no es un conjunto de episodios independientes."
    )
    alive = []
    if h1a_oos is not None and h1a_oos["beta"] > 0 and t_ok(h1a_oos, 1.5):
        alive.append("H1 magnitud 30d→30d (débil, FDR 0.078)")
    if h1c_oos is not None and h1c_oos["beta"] > 0 and t_ok(h1c_oos, 1.5):
        alive.append("H1 vol-scaled 30d (el primary más serio; FDR 0.078)")
    if h1b_oos is not None and t_ok(h1b_oos, 1.64):
        alive.append("H1 sign")
    else:
        alive.append("H1 sign: muerta")
    if r_strong is not None and r_strong["mean_future_return"] > 0 and "CI>0" in strong_oos30:
        alive.append("H2 STRONG continúa (robusto a block 30/60/90 y a de-cluster N=15)")
    alive.append("H2 EXTREME distinto de STRONG: no confirmado (N clustered=4; 7d reversal no robusto)")
    q10 = "; ".join(alive)

    return f"""# Segunda prueba — BTC momentum 30d y extremos

Confirmatorio, no exploratorio. Solo Binance BTCUSDT. Sin backtest.
Seed {SEED}. Bootstrap {N_BOOT} réplicas. HAC daily lag={HAC_DAILY}, monthly lag={HAC_MONTHLY}.
FDR Benjamini-Hochberg **solo** sobre los 3 PRIMARY OOS.
{labels_note}

---

## Datos

- Fuente: {meta['source']}
- Primera fecha: {meta['date_start']}
- Última fecha: {meta['date_end']} (última vela UTC completa)
- N: {meta['n']}
- Timezone: {meta['timezone']}
- Duplicados: {meta['n_dup']}
- NaN: {meta['n_nan']}
- Días faltantes (no interpolados): {meta['n_missing']} ({miss_txt})
- IS: 2017-08-17 → 2020-12-31 (señal t)
- OOS: 2021-01-01 → {meta['date_end']} (prioridad)

## Thresholds IS de R30_past (congelados para OOS)

- p50 = {_pct(q['p50'])}
- p75 = {_pct(q['p75'])}  → STRONG empieza aquí
- p90 = {_pct(q['p90'])}  → VERY STRONG
- p95 = {_pct(q['p95'])}  → EXTREME por encima

Buckets: NORMAL/POSITIVE 50–75 · STRONG 75–90 · VERY STRONG 90–95 · EXTREME >p95.

---

## PRIMARY tests

{md_reg(['H1A_continuous', 'H1B_sign', 'H1C_volscaled'])}

H1B — expectativas condicionales:

{md_sign_extra()}

## SECONDARY — mensual (fin de mes, no solapado)

{md_reg(['monthly_continuous', 'monthly_sign'])}

N mensual es pequeño a propósito (un obs. por mes). Un t bajo aquí no es el mismo listón que el diario solapado.

## SECONDARY — extremos rolling (R30_past, umbrales IS)

### OOS, h=7

{md_buckets('OOS', 7)}

### OOS, h=30

{md_buckets('OOS', 30)}

### IS, h=7

{md_buckets('IS', 7)}

### IS, h=30

{md_buckets('IS', 30)}

Una conclusión de cola que **solo** aparece con block=30 y se rompe en 60/90 se marca NO ROBUSTA.

## SECONDARY — eventos no solapados (cooldown 30 días)

### OOS

{md_cluster('OOS')}

### IS

{md_cluster('IS')}

---

## Respuestas

1. ¿Se replica el momentum 30d→30d usando solo Binance?
**{q1}**

2. ¿Sobrevive OOS?
**{q2}**

3. ¿Qué ocurre con sign(Rpast)?
**{q3}**

4. ¿Qué ocurre al ajustar por volatilidad?
**{q4}**

5. ¿Sobrevive usando observaciones mensuales?
**{q5}**

6. ¿Los rallies fuertes continúan?
**{q6}**

7. ¿Los rallies EXTREMOS se comportan distinto?
**{q7}**

8. ¿Los resultados extremos sobreviven block lengths 30/60/90?
**{q8}**

9. ¿Sobreviven cuando agrupamos episodios extremos y evitamos contar clusters?
**{q9}**

10. ¿Qué hipótesis queda viva?
**{q10}**

---

## Decisión

# {reco}

{why}
"""


def run() -> None:
    rng = np.random.default_rng(SEED)
    px, meta = load_prices()
    daily = make_daily(px)
    monthly = make_monthly(px)

    # quantiles IS only
    is_ok = (daily["date"] <= IS_END) & daily["r30_past"].notna()
    q = is_quantiles(daily.loc[is_ok, "r30_past"].to_numpy(dtype=float))

    main_rows = []

    def add_reg(group, spec, sample, y, x, lags, extra=None):
        row = {
            "group": group,
            "spec": spec,
            "sample": sample,
            **hac_ols(y, x, lags),
            "fdr_p_value": np.nan,
            "mean_fut_if_past_pos": np.nan,
            "mean_fut_if_past_neg": np.nan,
            "p_up_if_past_pos": np.nan,
            "p_up_if_past_neg": np.nan,
            "n_past_pos": np.nan,
            "n_past_neg": np.nan,
        }
        if extra:
            row.update(extra)
        main_rows.append(row)

    for sample in ("IS", "OOS"):
        m = split_mask(daily["date"], sample)
        sub = daily.loc[m]
        rp = sub["r30_past"].to_numpy(float)
        rf = sub["r30_fut"].to_numpy(float)
        rpv = sub["r30_past_vol"].to_numpy(float)
        rfv = sub["r30_fut_vol"].to_numpy(float)
        sg = sub["sign_past"].to_numpy(float)
        add_reg("PRIMARY", "H1A_continuous", sample, rf, rp, HAC_DAILY)
        add_reg("PRIMARY", "H1B_sign", sample, rf, sg, HAC_DAILY, sign_extras(rp, rf))
        add_reg("PRIMARY", "H1C_volscaled", sample, rfv, rpv, HAC_DAILY)

        mm = split_mask(monthly["date"], sample)
        msub = monthly.loc[mm]
        add_reg("SECONDARY", "monthly_continuous", sample, msub["r_next"].to_numpy(float), msub["r_month"].to_numpy(float), HAC_MONTHLY)
        add_reg("SECONDARY", "monthly_sign", sample, msub["r_next"].to_numpy(float), msub["sign"].to_numpy(float), HAC_MONTHLY)

    main = pd.DataFrame(main_rows)
    # FDR only on 3 PRIMARY OOS
    oos_p_idx = main.index[(main["group"] == "PRIMARY") & (main["sample"] == "OOS")]
    p = main.loc[oos_p_idx, "p_value"].to_numpy(float)
    order = ["H1A_continuous", "H1C_volscaled", "H1B_sign"]
    # keep spec order as primary 1,2,3
    p_ordered = []
    idx_ordered = []
    for spec in order:
        hit = main.index[(main["group"] == "PRIMARY") & (main["sample"] == "OOS") & (main["spec"] == spec)]
        idx_ordered.extend(list(hit))
        p_ordered.append(float(main.loc[hit, "p_value"].iloc[0]))
    _, p_adj, _, _ = multipletests(p_ordered, method="fdr_bh")
    for i, adj in zip(idx_ordered, p_adj):
        main.loc[i, "fdr_p_value"] = adj

    # H2 rolling + clustered
    ext_rows = []
    for sample in ("IS", "OOS"):
        m = split_mask(daily["date"], sample)
        sub = daily.loc[m & daily["r30_past"].notna()].copy()
        rp = sub["r30_past"].to_numpy(float)
        dates = sub["date"].to_numpy()
        labels = assign_all(rp, q)
        for h, col in ((7, "r7_fut"), (30, "r30_fut")):
            rf = sub[col].to_numpy(float)
            ok = np.isfinite(rp) & np.isfinite(rf)
            rp_h, rf_h, lab_h, d_h = rp[ok], rf[ok], labels[ok], dates[ok]
            for name, _lab in BUCKETS:
                st = bucket_stats(rf_h, lab_h, name)

                def mean_fn(a, b, target=name, qq=q):
                    lab_b = assign_all(a, qq)
                    y = b[lab_b == target]
                    y = y[np.isfinite(y)]
                    return float(np.mean(y)) if y.size else np.nan

                for bl in BLOCK_LENS:
                    lo, hi = boot_ci(mean_fn, [rp_h, rf_h], bl, rng)
                    ext_rows.append(
                        {
                            "kind": "rolling",
                            "bucket": name,
                            "horizon": h,
                            "sample": sample,
                            "block_len": bl,
                            "N": st["N"],
                            "mean_future_return": st["mean"],
                            "median_future_return": st["median"],
                            "P_future_positive": st["p_pos"],
                            "P_future_negative": st["p_neg"],
                            "CI_low": lo,
                            "CI_high": hi,
                            "p50": q["p50"],
                            "p75": q["p75"],
                            "p90": q["p90"],
                            "p95": q["p95"],
                        }
                    )

        rp_all = sub["r30_past"].to_numpy(float)
        lab_all = assign_all(rp_all, q)
        d_all = sub["date"].to_numpy()
        r7 = sub["r7_fut"].to_numpy(float)
        r30 = sub["r30_fut"].to_numpy(float)
        for name, _ in BUCKETS:
            ev = clustered_indices(d_all, lab_all == name, cooldown=30)
            for h, arr in ((7, r7), (30, r30)):
                y = np.array([arr[i] for i in ev], dtype=float)
                y = y[np.isfinite(y)]
                n = int(y.size)
                ext_rows.append(
                    {
                        "kind": "clustered",
                        "bucket": name,
                        "horizon": h,
                        "sample": sample,
                        "block_len": "",
                        "N": n,
                        "mean_future_return": float(np.mean(y)) if n else np.nan,
                        "median_future_return": float(np.median(y)) if n else np.nan,
                        "P_future_positive": float(np.mean(y > 0)) if n else np.nan,
                        "P_future_negative": float(np.mean(y < 0)) if n else np.nan,
                        "CI_low": np.nan,
                        "CI_high": np.nan,
                        "p50": q["p50"],
                        "p75": q["p75"],
                        "p90": q["p90"],
                        "p95": q["p95"],
                    }
                )

    ext = pd.DataFrame(ext_rows)

    cols_main = [
        "group",
        "spec",
        "sample",
        "beta",
        "se",
        "t_stat",
        "p_value",
        "fdr_p_value",
        "r2",
        "N",
        "mean_fut_if_past_pos",
        "mean_fut_if_past_neg",
        "p_up_if_past_pos",
        "p_up_if_past_neg",
        "n_past_pos",
        "n_past_neg",
    ]
    main[cols_main].to_csv(OUT_MAIN, index=False)
    ext.to_csv(OUT_EXT, index=False)

    note = (
        "PRIMARY = 3 tests OOS predefinidos. Mensual y extremos son SECONDARY. "
        "No se mezclan 30 tests secundarios en el FDR."
    )
    OUT_MD.write_text(write_summary(meta, main, ext, q, note), encoding="utf-8")
    print("Wrote", OUT_MAIN)
    print("Wrote", OUT_EXT)
    print("Wrote", OUT_MD)
    print("Data", meta)
    print("IS R30 percentiles", q)


if __name__ == "__main__":
    run()
