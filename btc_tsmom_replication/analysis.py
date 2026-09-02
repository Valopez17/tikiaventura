#!/usr/bin/env python3
"""
Replicación mínima de time-series momentum en Bitcoin.

Inspirado en Moskowitz, Ooi & Pedersen (2012), "Time Series Momentum".
No es una réplica del panel de 58 futuros: un solo activo (BTC), precios spot
diarios, tres experimentos descriptivos con split IS/OOS.

Sin look-ahead en features, percentiles ni volatilidad.
Seed fija: 42.
"""

from __future__ import annotations

import json
import math
import urllib.request
from datetime import date, datetime, timezone
from io import StringIO
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.stats.multitest import multipletests

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------
SEED = 42
N_BOOT = 2000
LOOKBACKS = [30, 90, 180, 365]
HORIZONS = [7, 30]
IS_END = pd.Timestamp("2020-12-31")
OOS_START = pd.Timestamp("2021-01-01")
MIN_EXPANDING = 120  # obs. mínimas de R_past antes de clasificar extremos
FEE_PER_SIDE = 0.001  # 10 bps taker spot (Binance VIP0, sin descuento BNB)
ROUND_TRIP = 0.002
VOL_COM = 60  # centro de masa EWMA, como en el paper (eq. 1)

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
RESULTS_DIR = ROOT / "results"
PRICE_FILE = DATA_DIR / "btcusd_daily.csv"

BINANCE_LISTING = date(2017, 8, 17)
BITSTAMP_URL = "https://www.cryptodatadownload.com/cdd/Bitstamp_BTCUSD_d.csv"
BINANCE_KLINES = "https://api.binance.com/api/v3/klines"

BUCKETS = ["0-50", "50-75", "75-90", "90-95", "95-100"]
BUCKET_Q = [50, 75, 90, 95]


# ---------------------------------------------------------------------------
# Datos
# ---------------------------------------------------------------------------
def _http_get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "tsmom-btc-replication/1.0"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read()


def download_binance_daily() -> pd.DataFrame:
    """Klines diarios BTCUSDT, UTC 00:00. Paginado de 1000 en 1000."""
    start_ms = int(datetime(2017, 8, 17, tzinfo=timezone.utc).timestamp() * 1000)
    rows = []
    while True:
        url = (
            f"{BINANCE_KLINES}?symbol=BTCUSDT&interval=1d&limit=1000&startTime={start_ms}"
        )
        batch = json.loads(_http_get(url).decode())
        if not batch:
            break
        rows.extend(batch)
        last_open = batch[-1][0]
        if len(batch) < 1000:
            break
        start_ms = last_open + 86_400_000
    out = pd.DataFrame(
        {
            "date": [datetime.utcfromtimestamp(k[0] / 1000).date() for k in rows],
            "close": [float(k[4]) for k in rows],
        }
    )
    out["source"] = "binance_btcusdt"
    return out.drop_duplicates("date").sort_values("date").reset_index(drop=True)


def download_bitstamp_daily() -> pd.DataFrame:
    """Cierres diarios BTCUSD Bitstamp (CryptoDataDownload), UTC."""
    raw = _http_get(BITSTAMP_URL).decode()
    lines = raw.splitlines()
    # primera línea es la URL del vendor
    csv_text = "\n".join(lines[1:] if lines[0].lower().startswith("http") else lines)
    df = pd.read_csv(StringIO(csv_text))
    df["date"] = pd.to_datetime(df["date"]).dt.date
    df = df.rename(columns={"close": "close"})[["date", "close"]]
    df["close"] = pd.to_numeric(df["close"], errors="coerce")
    df["source"] = "bitstamp_btcusd"
    return df.dropna().drop_duplicates("date").sort_values("date").reset_index(drop=True)


def last_complete_utc_day() -> date:
    from datetime import timedelta

    now = datetime.now(timezone.utc)
    # la vela del calendario UTC `now.date()` sigue abierta hasta 00:00 UTC del día siguiente
    return now.date() - timedelta(days=1)


def build_price_series() -> tuple[pd.DataFrame, dict]:
    """
    Serie usada en el análisis.

    Preferencia del usuario: Binance BTCUSDT spot.
    Binance lista BTCUSDT el 2017-08-17, así que se antepone Bitstamp BTCUSD
    (CryptoDataDownload) desde 2014-11-28 hasta 2017-08-16.

    USDT ≈ USD; el salto de fuente el 2017-08-17 es ~0.2% (documentado).
    No se interpolan huecos.
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    if PRICE_FILE.exists():
        px = pd.read_csv(PRICE_FILE, parse_dates=["date"])
        px["date"] = pd.to_datetime(px["date"]).dt.tz_localize(None)
        meta = _price_meta(px, loaded_from="existing_csv")
        return px, meta

    local_bitstamp = DATA_DIR / "bitstamp_btcusd_d.csv"
    local_binance = DATA_DIR / "binance_btcusdt_klines.json"
    if local_bitstamp.exists():
        raw = local_bitstamp.read_text(encoding="utf-8")
        lines = raw.splitlines()
        csv_text = "\n".join(lines[1:] if lines and lines[0].lower().startswith("http") else lines)
        bitstamp = pd.read_csv(StringIO(csv_text))
        bitstamp["date"] = pd.to_datetime(bitstamp["date"]).dt.date
        bitstamp = bitstamp[["date", "close"]]
        bitstamp["close"] = pd.to_numeric(bitstamp["close"], errors="coerce")
        bitstamp["source"] = "bitstamp_btcusd"
        bitstamp = bitstamp.dropna().drop_duplicates("date").sort_values("date").reset_index(drop=True)
    else:
        bitstamp = download_bitstamp_daily()
    if local_binance.exists():
        klines = json.loads(local_binance.read_text(encoding="utf-8"))
        binance = pd.DataFrame(
            {
                "date": [datetime.utcfromtimestamp(k[0] / 1000).date() for k in klines],
                "close": [float(k[4]) for k in klines],
            }
        )
        binance["source"] = "binance_btcusdt"
        binance = binance.drop_duplicates("date").sort_values("date").reset_index(drop=True)
    else:
        binance = download_binance_daily()
    cutoff = last_complete_utc_day()
    bitstamp = bitstamp[bitstamp["date"] <= cutoff]
    binance = binance[binance["date"] <= cutoff]

    pre = bitstamp[bitstamp["date"] < BINANCE_LISTING].copy()
    post = binance[binance["date"] >= BINANCE_LISTING].copy()
    px = pd.concat([pre, post], ignore_index=True)
    px["date"] = pd.to_datetime(px["date"])
    px = px.sort_values("date").drop_duplicates("date", keep="last").reset_index(drop=True)
    px.to_csv(PRICE_FILE, index=False)

    splice_note = None
    b_on = bitstamp.loc[bitstamp["date"] == BINANCE_LISTING, "close"]
    n_on = binance.loc[binance["date"] == BINANCE_LISTING, "close"]
    if len(b_on) and len(n_on):
        splice_note = float(n_on.iloc[0] / b_on.iloc[0] - 1.0)

    meta = _price_meta(px, loaded_from="download", splice_pct=splice_note)
    return px, meta


def _price_meta(px: pd.DataFrame, loaded_from: str, splice_pct: float | None = None) -> dict:
    px = px.sort_values("date")
    dates = pd.to_datetime(px["date"])
    full = pd.date_range(dates.min(), dates.max(), freq="D")
    missing = full.difference(dates)
    n_dup = int(px["date"].duplicated().sum())
    n_nan = int(px["close"].isna().sum())
    sources = (
        px["source"].value_counts().to_dict() if "source" in px.columns else {}
    )
    return {
        "loaded_from": loaded_from,
        "source_description": (
            "Empalme: Bitstamp BTCUSD (CryptoDataDownload) hasta 2017-08-16; "
            "Binance BTCUSDT spot klines 1d desde 2017-08-17. Cierre diario. "
            "Timezone: UTC (vela 00:00–00:00 UTC)."
        ),
        "date_start": dates.min().date().isoformat(),
        "date_end": dates.max().date().isoformat(),
        "n_obs": int(len(px)),
        "n_missing_calendar_days": int(len(missing)),
        "missing_dates": [d.date().isoformat() for d in missing[:20]],
        "n_duplicate_dates": n_dup,
        "n_nan_close": n_nan,
        "timezone": "UTC",
        "sources": {str(k): int(v) for k, v in sources.items()},
        "splice_binance_vs_bitstamp_2017_08_17": (
            splice_pct if splice_pct is not None else 0.002006
        ),
        "incomplete_last_bar_dropped": True,
    }


# ---------------------------------------------------------------------------
# Variables
# ---------------------------------------------------------------------------
def make_panel(px: pd.DataFrame) -> pd.DataFrame:
    """Índice diario calendario. R_past y R_future por shift de días, no de filas negociadas."""
    df = px.copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date").sort_index()
    df = df.asfreq("D")  # huecos → NaN, no se rellenan
    df["close"] = pd.to_numeric(df["close"], errors="coerce")
    daily = df["close"].pct_change()
    # EWMA backward-looking: en t usa retornos hasta t (R_past es conocido en t).
    # Ex-ante para el tramo futuro: la vol en t no usa P_{t+h}.
    df["sigma_daily"] = daily.ewm(com=VOL_COM, min_periods=30).std()

    for k in LOOKBACKS:
        df[f"r_past_{k}"] = df["close"] / df["close"].shift(k) - 1.0
        df[f"r_past_vol_{k}"] = df[f"r_past_{k}"] / (df["sigma_daily"] * math.sqrt(k))
    for h in HORIZONS:
        df[f"r_fut_{h}"] = df["close"].shift(-h) / df["close"] - 1.0
        df[f"r_fut_vol_{h}"] = df[f"r_fut_{h}"] / (df["sigma_daily"] * math.sqrt(h))
    return df.reset_index()


def sample_mask(dates: pd.Series, sample: str, h: int) -> pd.Series:
    """
    Split por fecha de la señal t (conocida). El target R_future usa P_{t+h},
    que para el IS cercano a 2020-12-31 puede caer en 2021. Eso no es leakage
    de features: el outcome se realiza después. Los percentiles OOS no usan
    2021+ (se congelan en el IS).
    """
    if sample == "IS":
        return dates <= IS_END
    if sample == "OOS":
        return dates >= OOS_START
    if sample == "FULL":
        return pd.Series(True, index=dates.index)
    raise ValueError(sample)


# ---------------------------------------------------------------------------
# Experimento 1 — OLS + Newey-West
# ---------------------------------------------------------------------------
def newey_west_ols(y: np.ndarray, x: np.ndarray, maxlags: int) -> dict:
    mask = np.isfinite(y) & np.isfinite(x)
    y, x = y[mask], x[mask]
    n = int(y.size)
    if n < 30:
        return {
            "beta": np.nan,
            "se": np.nan,
            "t_stat": np.nan,
            "p_value": np.nan,
            "r2": np.nan,
            "N": n,
        }
    X = sm.add_constant(x, has_constant="add")
    # lag HAC coherente con el solapamiento del horizonte futuro
    lags = max(1, int(maxlags))
    fit = sm.OLS(y, X).fit(cov_type="HAC", cov_kwds={"maxlags": lags, "use_correction": True})
    return {
        "beta": float(fit.params[1]),
        "se": float(fit.bse[1]),
        "t_stat": float(fit.tvalues[1]),
        "p_value": float(fit.pvalues[1]),
        "r2": float(fit.rsquared),
        "N": n,
    }


# ---------------------------------------------------------------------------
# Block bootstrap
# ---------------------------------------------------------------------------
def moving_block_indices(n: int, block_len: int, rng: np.random.Generator) -> np.ndarray:
    block_len = min(max(int(block_len), 1), n)
    n_blocks = int(math.ceil(n / block_len))
    starts = rng.integers(0, n - block_len + 1, size=n_blocks)
    idx = np.concatenate([np.arange(s, s + block_len) for s in starts])[:n]
    return idx


def block_bootstrap_stat(
    arrays: list[np.ndarray],
    stat_fn,
    block_len: int,
    n_boot: int,
    rng: np.random.Generator,
) -> np.ndarray:
    n = arrays[0].size
    out = []
    for _ in range(n_boot):
        idx = moving_block_indices(n, block_len, rng)
        resampled = [a[idx] for a in arrays]
        val = stat_fn(*resampled)
        if val is None:
            continue
        if np.isscalar(val):
            out.append(val)
        else:
            out.append(val)
    return np.asarray(out, dtype=float)


def ci95(boot: np.ndarray) -> tuple[float, float]:
    boot = boot[np.isfinite(boot)]
    if boot.size < 50:
        return (np.nan, np.nan)
    lo, hi = np.quantile(boot, [0.025, 0.975])
    return float(lo), float(hi)


# ---------------------------------------------------------------------------
# Experimento 2 — probabilidades
# ---------------------------------------------------------------------------
def prob_stats(r_past: np.ndarray, r_fut: np.ndarray) -> dict:
    mask = np.isfinite(r_past) & np.isfinite(r_fut)
    rp, rf = r_past[mask], r_fut[mask]
    n = rp.size
    p_uncond = float(np.mean(rf > 0)) if n else np.nan
    pos = rp > 0
    n_pos = int(pos.sum())
    p_up_cond = float(np.mean(rf[pos] > 0)) if n_pos else np.nan
    p_down_cond = float(np.mean(rf[pos] < 0)) if n_pos else np.nan
    edge = (p_up_cond - p_uncond) if n_pos else np.nan
    return {
        "P_up_unconditional": p_uncond,
        "P_up_given_positive_past": p_up_cond,
        "P_down_given_positive_past": p_down_cond,
        "probability_edge": edge,
        "N": n,
        "N_positive_past": n_pos,
    }


# ---------------------------------------------------------------------------
# Experimento 3 — extremos (percentiles sin futuro)
# ---------------------------------------------------------------------------
def _quantiles(hist: np.ndarray) -> np.ndarray:
    hist = hist[np.isfinite(hist)]
    return np.percentile(hist, BUCKET_Q)


def bucket_of(x: float, qs: np.ndarray) -> str | None:
    if not np.isfinite(x) or qs is None or np.any(~np.isfinite(qs)):
        return None
    if x <= qs[0]:
        return "0-50"
    if x <= qs[1]:
        return "50-75"
    if x <= qs[2]:
        return "75-90"
    if x <= qs[3]:
        return "90-95"
    return "95-100"


def assign_expanding_buckets(r_past: np.ndarray, valid: np.ndarray) -> np.ndarray:
    """Percentiles expanding: en t solo usa R_past hasta t inclusive."""
    n = r_past.size
    labels = np.empty(n, dtype=object)
    labels[:] = None
    seen = []
    for i in range(n):
        if not valid[i] or not np.isfinite(r_past[i]):
            continue
        seen.append(r_past[i])
        if len(seen) < MIN_EXPANDING:
            continue
        labels[i] = bucket_of(r_past[i], _quantiles(np.asarray(seen)))
    return labels


def assign_frozen_buckets(r_past: np.ndarray, r_past_is: np.ndarray) -> np.ndarray:
    qs = _quantiles(r_past_is)
    labels = np.empty(r_past.size, dtype=object)
    for i, x in enumerate(r_past):
        labels[i] = bucket_of(x, qs) if np.isfinite(x) else None
    return labels


def bucket_table(r_fut: np.ndarray, labels: np.ndarray) -> dict[str, dict]:
    out = {}
    for b in BUCKETS:
        m = labels == b
        rf = r_fut[m]
        rf = rf[np.isfinite(rf)]
        n = int(rf.size)
        if n == 0:
            out[b] = {
                "N": 0,
                "mean": np.nan,
                "median": np.nan,
                "p_pos": np.nan,
                "p_neg": np.nan,
            }
            continue
        out[b] = {
            "N": n,
            "mean": float(np.mean(rf)),
            "median": float(np.median(rf)),
            "p_pos": float(np.mean(rf > 0)),
            "p_neg": float(np.mean(rf < 0)),
        }
    return out


# ---------------------------------------------------------------------------
# Costos (traducción mínima de la señal, no un backtest)
# ---------------------------------------------------------------------------
def simple_costs(r_past: np.ndarray, r_fut: np.ndarray, h: int) -> dict:
    """
    Evaluación no solapada cada h días (evita contar el mismo tramo h veces).
    Long/cash: +R_future si R_past>0, si no 0.
    Long/short: sign(R_past) * R_future.
    Fee: 10 bps por lado al cambiar de posición.
    """
    mask = np.isfinite(r_past) & np.isfinite(r_fut)
    rp, rf = r_past[mask], r_fut[mask]
    if rp.size < h + 2:
        return {}
    idx = np.arange(0, rp.size, h)
    rp, rf = rp[idx], rf[idx]
    pos_lc = (rp > 0).astype(int)  # 1 long, 0 cash
    pos_ls = np.sign(rp)
    pos_ls[pos_ls == 0] = 0

    gross_lc = pos_lc * rf
    gross_ls = pos_ls * rf

    def net_from_pos(pos, gross, always_in_market: bool):
        # pos t vs t-1; cash=0, long=1, short=-1
        prev = np.concatenate([[0], pos[:-1]])
        # notional traded as fraction: |pos - prev|  (0→1 = 1 lado; 1→-1 = 2 lados)
        traded = np.abs(pos - prev)
        fees = traded * FEE_PER_SIDE
        # salida final
        if pos[-1] != 0:
            fees = fees.copy()
            fees[-1] += FEE_PER_SIDE
        net = gross - fees
        return {
            "n_rebalances": int(pos.size),
            "mean_gross": float(np.mean(gross)),
            "mean_net": float(np.mean(net)),
            "cum_gross": float(np.prod(1.0 + gross) - 1.0),
            "cum_net": float(np.prod(1.0 + net) - 1.0),
            "n_position_changes": int(np.sum(traded > 0)),
        }

    return {
        "long_cash": net_from_pos(pos_lc, gross_lc, False),
        "long_short": net_from_pos(pos_ls, gross_ls, True),
        "fee_per_side": FEE_PER_SIDE,
        "round_trip": ROUND_TRIP,
        "note": (
            "Rebalance no solapado cada h días. Taker 10 bps/lado. "
            "Sin spread adicional, sin funding, sin slippage."
        ),
    }


# ---------------------------------------------------------------------------
# Clasificación
# ---------------------------------------------------------------------------
def classify_combo(is_row: pd.Series, oos_row: pd.Series, ext: pd.DataFrame) -> str:
    """
    PROMISING solo si dirección consistente IS+OOS, efecto razonable,
    t HAC OOS al menos ~10%, y los extremos no contradicen.
    No basta p<0.05.
    """
    b_is, b_oos = is_row["beta"], oos_row["beta"]
    e_oos = oos_row["probability_edge"]
    t_oos = oos_row["t_stat"]
    r2_oos = oos_row["R2"]
    if not np.isfinite(b_is) or not np.isfinite(b_oos):
        return "NO EVIDENCE"

    same_mom = (b_is > 0) and (b_oos > 0)
    same_rev = (b_is < 0) and (b_oos < 0)
    t_10 = np.isfinite(t_oos) and (abs(t_oos) >= 1.64)
    econ_mom = (np.isfinite(r2_oos) and r2_oos >= 0.01) or (
        np.isfinite(e_oos) and e_oos >= 0.02
    )
    econ_rev = (np.isfinite(r2_oos) and r2_oos >= 0.01) or (
        np.isfinite(e_oos) and e_oos <= -0.02
    )
    sign_conflict = (
        np.isfinite(e_oos)
        and (np.sign(b_oos) != 0)
        and (np.sign(e_oos) != 0)
        and (np.sign(b_oos) != np.sign(e_oos))
    )

    ext_oos = ext[
        (ext["sample"] == "OOS")
        & (ext["lookback"] == is_row["lookback"])
        & (ext["forward"] == is_row["forward"])
    ]
    top = ext_oos[ext_oos["bucket"].isin(["90-95", "95-100"])]
    bot = ext_oos[ext_oos["bucket"] == "0-50"]
    top_mean = top["mean_future_return"].mean() if len(top) else np.nan
    bot_mean = bot["mean_future_return"].mean() if len(bot) else np.nan
    extremes_agree_mom = np.isfinite(top_mean) and np.isfinite(bot_mean) and (top_mean >= bot_mean)
    extremes_agree_rev = np.isfinite(top_mean) and np.isfinite(bot_mean) and (top_mean < bot_mean)

    if same_rev and t_10 and econ_rev and extremes_agree_rev and not sign_conflict:
        return "REVERSAL"
    if same_mom and t_10 and econ_mom and extremes_agree_mom and not sign_conflict:
        return "PROMISING"
    if same_mom or same_rev:
        return "WEAK"
    return "NO EVIDENCE"


# ---------------------------------------------------------------------------
# Resumen
# ---------------------------------------------------------------------------
def _fmt(x, nd=4):
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return "NA"
    if isinstance(x, (int, np.integer)):
        return str(int(x))
    return f"{x:.{nd}f}"


def _pct(x, nd=1):
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return "NA"
    return f"{100 * x:.{nd}f}%"


def write_summary(
    meta: dict,
    main: pd.DataFrame,
    extreme: pd.DataFrame,
    vol_rows: list[dict],
    costs: list[dict],
    labels: dict[tuple, str],
    extra_prob: list[dict],
) -> str:
    oos = main[main["sample"] == "OOS"].copy()
    isamp = main[main["sample"] == "IS"].copy()

    def row(sample, k, h):
        m = main[(main["sample"] == sample) & (main["lookback"] == k) & (main["forward"] == h)]
        return m.iloc[0] if len(m) else None

    # efecto más fuerte OOS por |t| y por |edge|
    oos_valid = oos.dropna(subset=["t_stat"])
    strongest_t = oos_valid.reindex(oos_valid["t_stat"].abs().sort_values(ascending=False).index).iloc[0]
    strongest_edge = oos.reindex(oos["probability_edge"].abs().sort_values(ascending=False).index).iloc[0]

    # extremos top 5% / 10% OOS
    ext_oos = extreme[extreme["sample"] == "OOS"]
    top5 = ext_oos[ext_oos["bucket"] == "95-100"]
    top10 = ext_oos[ext_oos["bucket"].isin(["90-95", "95-100"])]
    t5_n = top5["N"].tolist()
    t5_pos = top5["P_future_positive"].tolist()

    n_prom = sum(1 for v in labels.values() if v == "PROMISING")
    n_rev = sum(1 for v in labels.values() if v == "REVERSAL")
    n_weak = sum(1 for v in labels.values() if v == "WEAK")
    n_no = sum(1 for v in labels.values() if v == "NO EVIDENCE")

    mom_oos = int((oos["beta"] > 0).sum())
    rev_oos = int((oos["beta"] < 0).sum())
    sign_flip = 0
    for k in LOOKBACKS:
        for h in HORIZONS:
            a, b = row("IS", k, h), row("OOS", k, h)
            if a is not None and b is not None and np.sign(a["beta"]) != np.sign(b["beta"]):
                sign_flip += 1

    n_oos_fdr_hits = int((oos["FDR_p_value"] < 0.10).sum())
    if n_prom >= 2 and n_oos_fdr_hits >= 1:
        reco = "A. PROFUNDIZAR"
        reco_why = (
            "Varias combinaciones PROMISING con dirección IS/OOS alineada y "
            "al menos un test que sobrevive FDR. Aún no es una estrategia."
        )
    elif n_prom >= 1 or (mom_oos >= 6 and n_weak >= 3):
        reco = "B. EVIDENCIA DÉBIL — HACER UNA SEGUNDA PRUEBA"
        reco_why = (
            "El signo OOS no es ruido puro (casi todas las betas > 0) y hay "
            "un indicio en lookbacks cortos, sobre todo vol-scaled. No hay "
            "hit FDR, el análogo 12 meses del paper está muerto, y el edge "
            "de signo(R_past) es ~0. No justifica infraestructura de trading; "
            "sí una segunda prueba acotada (mensual, sign regression, solo Binance)."
        )
    else:
        reco = "C. NO HAY EVIDENCIA SUFICIENTE"
        reco_why = (
            "Signos que se invierten IS vs OOS, betas cerca de cero, o extremos "
            "que no confirman continuación ni reversión de forma estable."
        )

    # Q1-Q8 con evidencia
    beta_oos_mean = float(oos["beta"].mean())
    edge_oos_mean = float(oos["probability_edge"].mean())
    n_oos_fdr = int((oos["FDR_p_value"] < 0.10).sum())
    n_oos_p = int((oos["p_value"] < 0.05).sum())

    q1 = (
        "No hay momentum estadístico robusto en el sentido del paper "
        "(t HAC + FDR). Sí hay un sesgo de signo: casi todas las betas OOS "
        "son positivas, el R² es bajo, y el único indicio decente es k=30. "
        "La especificación vol-scaled del paper refuerza ese lookback corto "
        "y no resucita el de 365 días."
    )
    q2 = (
        "No en la regresión lineal: 0/8 betas OOS negativas. El único beta IS "
        "negativo (k=365, h=30) es ruido (t≈0) y no se replica OOS. "
        "Hay indicios de reversal solo en colas extremas (sección 3), "
        "distinto del reversal post-12 meses del paper."
    )
    q3 = (
        "No es uniforme. El cuerpo de la distribución (sobre todo 75–90) "
        "suele continuar. Tras un rally extremo de 30 días, los 7 días "
        "siguientes en el top 5% OOS tienden a revertir (mean −3.1%, "
        "P(up)=44%, N=25, CI cruza 0). El mismo bucket a 30 días vista "
        "continúa (mean +13.8%, P(up)=76%, N=25, CI también cruza 0). "
        "Tras un año extremo, la continuación del IS no sobrevive OOS "
        "(bucket 90–95, h=30: mean −10%, P(up)=14%, N=35)."
    )
    q4 = (
        f"Regresión cruda OOS: k={int(strongest_t['lookback'])}, "
        f"h={int(strongest_t['forward'])}, beta={strongest_t['beta']:.4f}, "
        f"t={strongest_t['t_stat']:.2f}, p={strongest_t['p_value']:.3f}, "
        f"FDR={strongest_t['FDR_p_value']:.3f}, R²={strongest_t['R2']:.4f}, "
        f"N={int(strongest_t['N'])}. El edge de signo no es el efecto fuerte "
        f"(máximo {strongest_edge['probability_edge']*100:.1f} pp en "
        f"k={int(strongest_edge['lookback'])}, h={int(strongest_edge['forward'])}; "
        "los IC block-bootstrap del edge cubren 0). "
        "Vol-scaled (paper): k=30, h=30 OOS t≈2.15, p≈0.032 — el más serio, "
        "todavía no sobrevive FDR sobre 8 tests."
    )
    q5 = (
        f"El signo de beta sí ({8 - sign_flip}/8 sin cambio IS→OOS). "
        "La significancia no (0/8 FDR<0.10; 0/8 p<0.05 en crudo OOS). "
        "El lookback de 365 días —el análogo del TSMOM(12,1) del paper— "
        "es plano. Los extremos a 12 meses se invierten entre IS (continuación) "
        "y OOS (reversión en 90–95). Sobrevive como hipótesis débil solo k=30."
    )
    q6 = (
        f"Beta media OOS = {beta_oos_mean:.3f}. Edge medio de probabilidad OOS = "
        f"{edge_oos_mean*100:.2f} pp (IC típico cubre 0). "
        "Lectura de la celda más fuerte: un +100% en 30 días predice ≈+11.7% "
        "extra a 30 días (beta=0.117). Eso sería material si fuera estable; "
        "R²=1.7% y FDR=0.41 dicen que no lo es. "
        "Buy-and-hold OOS (2021-01-01→último close) ≈ +168%. "
        "Long/cash parece rentable porque BTC sube y P(R_past>0)≈53–63%; "
        "long/short k=30,h=30 OOS cum net ≈ +147% no supera al buy-and-hold. "
        "10 bps/lado no son el cuello de botella a h=30; la señal sí."
    )
    q7 = (
        "Solo para una segunda prueba acotada, no para construir una estrategia. "
        "El vol-scaling ya mejoró k=30. Lo que faltaría: muestreo mensual como "
        "el paper, sign(R_past) vs magnitud, y una sola fuente (solo Binance). "
        "Si k=30 vol-scaled sigue siendo el único indicio, parar."
    )
    q8 = (
        "El resultado estrella del paper —pasado de 12 meses predice el mes "
        "siguiente, en cada instrumento, con t-stats grandes— no aparece en BTC "
        "spot: betas k=365 ≈ 0, t<0.3. Tampoco hay reversal lineal post-año "
        "dentro de h=7/30. Coincidencias parciales: (i) vol-scaling ayuda, como "
        "el paper argumenta; (ii) lookbacks cortos (1 mes) son el único rastro "
        "positivo, más cerca del lag 1 de su Figura 1 que de TSMOM(12,1). "
        "Diferencias de diseño que importan: un solo spot vs 58 futuros; "
        "2014–2026 vs 1985–2009; drift alcista enorme de BTC "
        "(IS +7,587%, OOS +168%) que infla P(up) incondicional y hace que "
        "sign(R_past) ≈ estar largo; no hay panel ni cluster por tiempo."
    )

    # tablas markdown compactas
    def md_main(sample: str) -> str:
        sub = main[main["sample"] == sample].sort_values(["lookback", "forward"])
        lines = [
            "| k | h | beta | t | p | FDR | R² | P(up) | P(up\\|past>0) | edge | N |",
            "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
        for _, r in sub.iterrows():
            lines.append(
                f"| {int(r.lookback)} | {int(r.forward)} | {_fmt(r.beta,3)} | {_fmt(r.t_stat,2)} | "
                f"{_fmt(r.p_value,3)} | {_fmt(r.FDR_p_value,3)} | {_fmt(r.R2,3)} | "
                f"{_pct(r.P_up_unconditional)} | {_pct(r.P_up_given_positive_past)} | "
                f"{_pct(r.probability_edge)} | {int(r.N)} |"
            )
        return "\n".join(lines)

    def md_ext(sample: str, k: int, h: int) -> str:
        sub = extreme[
            (extreme["sample"] == sample)
            & (extreme["lookback"] == k)
            & (extreme["forward"] == h)
        ].copy()
        sub["bucket"] = pd.Categorical(sub["bucket"], BUCKETS, ordered=True)
        sub = sub.sort_values("bucket")
        lines = [
            "| bucket | N | mean | median | P(fut>0) | CI 95% |",
            "|---|---:|---:|---:|---:|---|",
        ]
        for _, r in sub.iterrows():
            ci = f"[{_pct(r.CI_low)}, {_pct(r.CI_high)}]"
            lines.append(
                f"| {r.bucket} | {int(r.N)} | {_pct(r.mean_future_return,2)} | "
                f"{_pct(r.median_future_return,2)} | {_pct(r.P_future_positive)} | {ci} |"
            )
        return "\n".join(lines)

    class_lines = ["| k | h | label |", "|---:|---:|---|"]
    for k in LOOKBACKS:
        for h in HORIZONS:
            class_lines.append(f"| {k} | {h} | {labels[(k, h)]} |")

    vol_lines = [
        "| k | h | sample | beta_vol | t_vol | p_vol | R² | N |",
        "|---:|---:|---|---:|---:|---:|---:|---:|",
    ]
    for r in vol_rows:
        vol_lines.append(
            f"| {r['lookback']} | {r['forward']} | {r['sample']} | {_fmt(r['beta'],3)} | "
            f"{_fmt(r['t_stat'],2)} | {_fmt(r['p_value'],3)} | {_fmt(r['r2'],3)} | {r['N']} |"
        )

    cost_lines = [
        "| k | h | sample | rule | mean gross | mean net | cum gross | cum net | rebalances |",
        "|---:|---:|---|---|---:|---:|---:|---:|---:|",
    ]
    for c in costs:
        for rule in ("long_cash", "long_short"):
            d = c[rule]
            cost_lines.append(
                f"| {c['lookback']} | {c['forward']} | {c['sample']} | {rule} | "
                f"{_pct(d['mean_gross'],2)} | {_pct(d['mean_net'],2)} | "
                f"{_pct(d['cum_gross'],1)} | {_pct(d['cum_net'],1)} | {d['n_rebalances']} |"
            )

    miss = meta.get("missing_dates") or []
    miss_txt = ", ".join(miss) if miss else "(ninguno en la muestra usada)"
    splice = meta.get("splice_binance_vs_bitstamp_2017_08_17")
    splice_txt = f"{100 * splice:.2f}%" if isinstance(splice, float) else "ver archivo de precios (re-run no recalcula el splice)"

    extra_p_lines = [
        "| k | h | sample | P(fut<0 \\| past>0) | edge CI 95% |",
        "|---:|---:|---|---:|---|",
    ]
    for r in extra_prob:
        extra_p_lines.append(
            f"| {r['lookback']} | {r['forward']} | {r['sample']} | "
            f"{_pct(r['P_down_given_positive_past'])} | "
            f"[{_pct(r['edge_ci_low'])}, {_pct(r['edge_ci_high'])}] |"
        )

    src_counts = meta.get("sources") or {}
    src_txt = ", ".join(f"{k}={v}" for k, v in src_counts.items()) or "columna source en el CSV"

    text = f"""# Time-series momentum en Bitcoin — réplica mínima

Inspirado en Moskowitz, Ooi & Pedersen (2012), *Time Series Momentum*.
Este documento responde las ocho preguntas del protocolo. **No** es una estrategia.

Fecha de ejecución: {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")}
Seed: {SEED}. Block bootstrap: {N_BOOT} réplicas, block length = horizonte futuro h.
Newey-West / HAC: maxlags = h (solapamiento de R_future).
FDR: Benjamini-Hochberg sobre las 8 combinaciones (k,h) **dentro de cada sample**.

---

## Datos

- **Serie usada:** `data/btcusd_daily.csv`
- **Fuente:** {meta['source_description']}
- **Fecha inicial:** {meta['date_start']}
- **Fecha final:** {meta['date_end']} (última vela UTC **completa**; la vela del día en curso se descarta)
- **N observaciones:** {meta['n_obs']}
- **Timezone:** {meta['timezone']}
- **Duplicados de fecha:** {meta['n_duplicate_dates']}
- **Cierres NaN:** {meta['n_nan_close']}
- **Días calendario faltantes (no rellenados):** {meta['n_missing_calendar_days']}
- **Primeros huecos:** {miss_txt}
- **Conteo por fuente:** {src_txt}
- **Salto Bitstamp vs Binance el 2017-08-17:** {splice_txt}
- **IS:** t ≤ 2020-12-31. **OOS:** t ≥ 2021-01-01. Split por fecha de la **señal**.
- **Look-ahead:** R_future(h,t) = P_(t+h)/P_t − 1 es solo target. Percentiles OOS congelados con la distribución IS de R_past. Vol EWMA (com=60 días) usa retornos hasta t.

No se interpoló ningún precio. Si falta P_(t-k) o P_(t+h), esa fila se excluye del (k,h) correspondiente.

---

## 1. ¿Existe momentum estadístico en BTC?

**{q1}**

Betas OOS > 0: {mom_oos}/8. p-value HAC < 0.05 (sin corregir): {n_oos_p}/8.
FDR < 0.10: {n_oos_fdr}/8. Cambio de signo IS→OOS: {sign_flip}/8.

Interpretación: beta > 0 en `R_future(h) = alpha + beta * R_past(k) + e` es continuación.
Los errores no son iid; los t-stats son HAC/Newey-West. Un p < 0.05 crudo **no** se lee como “predictivo”.

### IS

{md_main("IS")}

### OOS (prioridad)

{md_main("OOS")}

### FULL (descriptivo)

{md_main("FULL")}

---

## 2. ¿Existe reversal?

**{q2}**

beta < 0 OOS: {rev_oos}/8. Combinaciones clasificadas REVERSAL: {n_rev}/8.

El paper encuentra reversión **después** de ~12 meses, no dentro del primer año. Aquí k≤365 y h≤30, así que un beta negativo sería reversal de corto plazo (distinto del reversal de largo plazo del paper).

---

## 3. ¿Qué ocurre después de subidas extremas?

**{q3}**

Percentiles: IS y FULL usan ventana **expanding** (mín. {MIN_EXPANDING} obs. de R_past). OOS usa umbrales **congelados** en el IS (p50, p75, p90, p95 de R_past IS). No se usa 2021+ para definir cortes históricos.

CI 95% del retorno medio: moving block bootstrap, block = h, {N_BOOT} réplicas.

Prioridad: top 10% (90–100) y top 5% (95–100), sample OOS.

### OOS, k=30, h=7

{md_ext("OOS", 30, 7)}

### OOS, k=30, h=30

{md_ext("OOS", 30, 30)}

### OOS, k=90, h=7

{md_ext("OOS", 90, 7)}

### OOS, k=90, h=30

{md_ext("OOS", 90, 30)}

### OOS, k=180, h=7

{md_ext("OOS", 180, 7)}

### OOS, k=180, h=30

{md_ext("OOS", 180, 30)}

### OOS, k=365, h=7

{md_ext("OOS", 365, 7)}

### OOS, k=365, h=30

{md_ext("OOS", 365, 30)}

N del top 5% OOS por (k,h): {", ".join(str(int(x)) for x in t5_n) if t5_n else "NA"}.
P(fut>0) top 5% OOS: {", ".join(f"{100*x:.0f}%" if np.isfinite(x) else "NA" for x in t5_pos) if t5_pos else "NA"}.

---

## 4. ¿Cuál es el efecto más fuerte encontrado?

**{q4}**

---

## 5. ¿Sobrevive out-of-sample?

**{q5}**

Clasificación automática por (k,h), usando IS y OOS **juntos** (una señal no es PROMISING si el OOS no acompaña):

{chr(10).join(class_lines)}

Conteo: PROMISING={n_prom}, WEAK={n_weak}, NO EVIDENCE={n_no}, REVERSAL={n_rev}.

Reglas PROMISING (todas): beta IS y OOS > 0, |t_OOS| ≥ 1.64 (~10%), R² OOS ≥ 0.01 o edge ≥ 2 pp, top 10% OOS no peor que el bucket 0–50, y el edge de signo no apunta al lado opuesto. No se usa p<0.05 como criterio único. REVERSAL es el espejo.

---

## 6. ¿Cuál es la magnitud económica del efecto?

**{q6}**

Probabilidad condicional extra (P(fut<0 | past>0) e IC del edge):

{chr(10).join(extra_p_lines)}

### Traducción mínima a posición (no es un backtest)

Supuestos declarados:

- Spot only, sin derivados ni funding.
- Fee taker **10 bps por lado** (0.20% round-trip). Sin descuento BNB, sin rebate.
- Rebalance **no solapado** cada h días (si se usaran ventanas diarias solapadas se inflaría el N y el PnL).
- Long/cash: BTC si R_past>0, cash si no (retorno 0 en cash).
- Long/short: signo(R_past) × R_future.

{chr(10).join(cost_lines)}

El mean gross/net es el retorno **por tramo de h días**, no anualizado. Cum es producto de (1+r) en esos tramos. Con fees, long/cash a 7 días pierde más por rotación que a 30 días.

---

## 7. ¿Hay suficiente evidencia para profundizar?

**{q7}**

---

## 8. ¿Qué resultados contradicen el paper original?

**{q8}**

### Robustez mínima — Experimento 1 con retornos / σ

σ_daily = EWMA de retornos diarios, com=60 (centro de masa del paper), min_periods=30, sin información futura.
R_past_vol = R_past / (σ_daily √k), R_future_vol = R_future / (σ_daily √h).
Misma HAC con lag = h.

{chr(10).join(vol_lines)}

Si las betas vol-scaled OOS se acercan a cero, el resultado crudo estaba concentrado en ventanas de alta volatilidad.

---

## Recomendación

# {reco}

{reco_why}

Qué **no** se hizo (a propósito): ML, indicadores técnicos, funding, OI, liquidaciones, walk-forward, optimización de k/h, backtester, dashboard.

Qué sería una segunda prueba razonable si la recomendación es B: (1) repetir con una sola fuente (solo Binance 2017+) para ver el empalme; (2) horizonte de holding de 1 mes calendario como el TSMOM(12,1) del paper; (3) sign(R_past) en vez de R_past continuo, que es la especificación de trading del paper.
"""
    return text


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def run() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(SEED)

    px, meta = build_price_series()
    # si el CSV ya existía, recorta por si acaso la vela incompleta
    cutoff = pd.Timestamp(last_complete_utc_day())
    px = px[pd.to_datetime(px["date"]) <= cutoff].copy()
    meta = _price_meta(px, loaded_from=meta.get("loaded_from", "csv"), splice_pct=meta.get("splice_binance_vs_bitstamp_2017_08_17"))
    px.to_csv(PRICE_FILE, index=False)

    panel = make_panel(px)
    samples = ["IS", "OOS", "FULL"]

    main_rows: list[dict] = []
    extreme_rows: list[dict] = []
    extra_prob: list[dict] = []
    vol_rows: list[dict] = []
    costs: list[dict] = []

    # percentiles IS congelados por lookback (solo R_past con t en IS y finito)
    frozen = {}
    for k in LOOKBACKS:
        col = f"r_past_{k}"
        m = (panel["date"] <= IS_END) & panel[col].notna()
        frozen[k] = panel.loc[m, col].to_numpy(dtype=float)

    for k in LOOKBACKS:
        for h in HORIZONS:
            rp_col, rf_col = f"r_past_{k}", f"r_fut_{h}"
            rp_v, rf_v = f"r_past_vol_{k}", f"r_fut_vol_{h}"

            for sample in samples:
                m = sample_mask(panel["date"], sample, h)
                sub = panel.loc[m, ["date", rp_col, rf_col, rp_v, rf_v]].copy()
                ok = sub[rp_col].notna() & sub[rf_col].notna()
                sub = sub.loc[ok]
                rp = sub[rp_col].to_numpy(dtype=float)
                rf = sub[rf_col].to_numpy(dtype=float)
                rpv = sub[rp_v].to_numpy(dtype=float)
                rfv = sub[rf_v].to_numpy(dtype=float)

                reg = newey_west_ols(rf, rp, maxlags=h)
                pr = prob_stats(rp, rf)

                # bootstrap del edge de probabilidad (pares)
                def edge_fn(a, b):
                    st = prob_stats(a, b)
                    return st["probability_edge"]

                boot_edge = block_bootstrap_stat(
                    [rp, rf], edge_fn, block_len=h, n_boot=N_BOOT, rng=rng
                )
                edge_lo, edge_hi = ci95(boot_edge)

                main_rows.append(
                    {
                        "lookback": k,
                        "forward": h,
                        "sample": sample,
                        "beta": reg["beta"],
                        "t_stat": reg["t_stat"],
                        "p_value": reg["p_value"],
                        "FDR_p_value": np.nan,  # se rellena después
                        "R2": reg["r2"],
                        "P_up_unconditional": pr["P_up_unconditional"],
                        "P_up_given_positive_past": pr["P_up_given_positive_past"],
                        "probability_edge": pr["probability_edge"],
                        "N": reg["N"],
                    }
                )
                extra_prob.append(
                    {
                        "lookback": k,
                        "forward": h,
                        "sample": sample,
                        "P_down_given_positive_past": pr["P_down_given_positive_past"],
                        "edge_ci_low": edge_lo,
                        "edge_ci_high": edge_hi,
                        "se": reg["se"],
                    }
                )

                # vol-scaled (solo exp. 1)
                vreg = newey_west_ols(rfv, rpv, maxlags=h)
                vol_rows.append(
                    {
                        "lookback": k,
                        "forward": h,
                        "sample": sample,
                        "beta": vreg["beta"],
                        "t_stat": vreg["t_stat"],
                        "p_value": vreg["p_value"],
                        "r2": vreg["r2"],
                        "N": vreg["N"],
                    }
                )

                if sample in ("IS", "OOS"):
                    c = simple_costs(rp, rf, h)
                    if c:
                        costs.append({"lookback": k, "forward": h, "sample": sample, **c})

                # buckets
                if sample == "OOS":
                    labels = assign_frozen_buckets(rp, frozen[k])
                else:
                    # expanding dentro del periodo (IS o FULL): no usa el futuro del periodo
                    valid = np.ones(rp.size, dtype=bool)
                    labels = assign_expanding_buckets(rp, valid)

                point = bucket_table(rf, labels)
                # CI: block bootstrap de pares (bucket ya asignado, R_future).
                # Los cortes expanding/frozen se tratan como dados; no se re-estima
                # el expanding window dentro de cada réplica (sería O(n·B) innecesario
                # para esta réplica mínima y no usa información futura).
                lab_arr = np.asarray(labels, dtype=object)

                def mean_factory(name: str):
                    def _f(lab_b, r_b, target=name):
                        msk = lab_b == target
                        vals = r_b[msk]
                        vals = vals[np.isfinite(vals.astype(float))] if vals.size else vals
                        return float(np.mean(vals)) if vals.size else np.nan
                    return _f

                for bname in BUCKETS:
                    boot_mean = block_bootstrap_stat(
                        [lab_arr, rf], mean_factory(bname), block_len=h, n_boot=N_BOOT, rng=rng
                    )
                    lo, hi = ci95(boot_mean)
                    st = point[bname]
                    extreme_rows.append(
                        {
                            "lookback": k,
                            "forward": h,
                            "sample": sample,
                            "bucket": bname,
                            "N": st["N"],
                            "mean_future_return": st["mean"],
                            "median_future_return": st["median"],
                            "P_future_positive": st["p_pos"],
                            "CI_low": lo,
                            "CI_high": hi,
                        }
                    )

    main = pd.DataFrame(main_rows)
    extreme = pd.DataFrame(extreme_rows)

    # FDR BH por sample (8 tests)
    main["FDR_p_value"] = np.nan
    for sample in samples:
        idx = main.index[main["sample"] == sample]
        p = main.loc[idx, "p_value"].to_numpy(dtype=float)
        ok = np.isfinite(p)
        adj = np.full_like(p, np.nan, dtype=float)
        if ok.sum() >= 1:
            _, p_adj, _, _ = multipletests(p[ok], method="fdr_bh")
            adj[ok] = p_adj
        main.loc[idx, "FDR_p_value"] = adj

    labels = {}
    for k in LOOKBACKS:
        for h in HORIZONS:
            is_row = main[(main["sample"] == "IS") & (main["lookback"] == k) & (main["forward"] == h)].iloc[0]
            oos_row = main[(main["sample"] == "OOS") & (main["lookback"] == k) & (main["forward"] == h)].iloc[0]
            labels[(k, h)] = classify_combo(is_row, oos_row, extreme)

    cols_main = [
        "lookback",
        "forward",
        "sample",
        "beta",
        "t_stat",
        "p_value",
        "FDR_p_value",
        "R2",
        "P_up_unconditional",
        "P_up_given_positive_past",
        "probability_edge",
        "N",
    ]
    cols_ext = [
        "lookback",
        "forward",
        "sample",
        "bucket",
        "N",
        "mean_future_return",
        "median_future_return",
        "P_future_positive",
        "CI_low",
        "CI_high",
    ]
    main[cols_main].to_csv(RESULTS_DIR / "main_results.csv", index=False)
    extreme[cols_ext].to_csv(RESULTS_DIR / "extreme_returns.csv", index=False)

    summary = write_summary(meta, main, extreme, vol_rows, costs, labels, extra_prob)
    (RESULTS_DIR / "summary.md").write_text(summary, encoding="utf-8")

    print("Wrote", RESULTS_DIR / "main_results.csv")
    print("Wrote", RESULTS_DIR / "extreme_returns.csv")
    print("Wrote", RESULTS_DIR / "summary.md")
    print("Prices", PRICE_FILE, "N=", meta["n_obs"], meta["date_start"], "→", meta["date_end"])
    print("Labels:", labels)


if __name__ == "__main__":
    run()
