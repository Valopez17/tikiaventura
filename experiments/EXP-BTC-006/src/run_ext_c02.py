#!/usr/bin/env python3
"""EXP-BTC-006 / EXT-C02: isolated positional vs exact-timestamp lookback.

Not a new search. Not a trading edge. Does not close E-02.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
import re
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[3]
EXP_DIR = Path(__file__).resolve().parents[1]
SPEC_PATH = EXP_DIR / "SPEC.md"
sys.path.insert(0, str(REPO))

from temporal.exact_timestamp import as_utc_index, lookback_index  # noqa: E402

LOOKBACK_MODE_A = "LEGACY_POSITIONAL"
LOOKBACK_MODE_B = "EXACT_TIMESTAMP"
EXPERIMENT_ID = "EXP-BTC-006"
HYPOTHESIS_ID = "HYP-BTC-002"
ERROR_ID = "E-02"
TASK_ID = "EXT-C02"
L6_CANDIDATE_ID = "L6_down_p1_rebound_long_H6"
EXPECTED_DATASET_SHA256 = "77948c076a07790739e6072e8c62316a672a389e80c6693be10a18c5461cc103"
EXPECTED_RECTOR_SHA256 = "799cbfa8575ca5147a658bd85a5fab66d4a0c7ed4539296639d14cea88137778"
CODE_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
HOUR_NS = 3_600_000_000_000
AUDIT_EXPANDING_N = 24
PERIODS = ("discovery", "validation", "recent")

FROZEN_TOP10_REL = (
    "research/market_state_observatory/trade_signal_research/strategy_lab/"
    "phase4_extreme_move_reversal/results/TOP_CANDIDATES.csv"
)
FROZEN_VAL_REL = (
    "research/market_state_observatory/trade_signal_research/strategy_lab/"
    "phase4_extreme_move_reversal/results/VALIDATION_RESULTS.csv"
)
DATASET_REL = "btc_tsmom_replication/btcusdt_1h.csv"
PHASE4_DIR_REL = (
    "research/market_state_observatory/trade_signal_research/strategy_lab/"
    "phase4_extreme_move_reversal"
)
PHASE4B_DIR_REL = (
    "research/market_state_observatory/trade_signal_research/strategy_lab/"
    "phase4b_extreme_move_audit_fix"
)

REQUIRED_HARNESS_PATHS = (
    "experiments/EXP-BTC-006/src/run_ext_c02.py",
    "experiments/EXP-BTC-006/SPEC.md",
    "tests/test_ext_c02_isolation.py",
    "tests/test_ext_c02_reproducibility.py",
    "tests/fixtures/e02_gap_hours.csv",
    "tests/fixtures/ext_c02_regular_hours.csv",
)

HASH_CONTRACT_FILES = (
    "outputs/SIGNAL_IMPACT.csv",
    "outputs/RULE_IMPACT.csv",
    "outputs/FROZEN_TOP10_IMPACT.csv",
    "result/RESULT.json",
    "report/EXT_C02_E02_IMPACT.md",
)

REGULAR_FIXTURE_REL = "tests/fixtures/ext_c02_regular_hours.csv"
GAP_FIXTURE_REL = "tests/fixtures/e02_gap_hours.csv"


@dataclass(frozen=True)
class FrozenConfig:
    lookback_mode: str
    lookbacks_h: tuple[int, ...] = (6, 12, 24, 72)
    down_percentiles: tuple[float, ...] = (0.01, 0.025, 0.05)
    up_percentiles: tuple[float, ...] = (0.95, 0.975, 0.99)
    holds_h: tuple[int, ...] = (6, 12, 24, 48, 72, 168)
    fee_round_trip: float = 0.0010
    min_history_calendar_days: int = 365
    disc_end_utc: str = "2022-01-01T00:00:00+00:00"
    val_end_utc: str = "2025-01-01T00:00:00+00:00"
    start_cap: float = 10_000.0
    crypto_days: float = 365.0
    entry_offset_h: int = 1
    frozen_top10_relpath: str = FROZEN_TOP10_REL
    dataset_relpath: str = DATASET_REL
    expected_dataset_sha256: str = EXPECTED_DATASET_SHA256
    l6_candidate_id: str = L6_CANDIDATE_ID
    reselect_top: bool = False
    use_mtm_primary: bool = False
    change_survivor_gate: bool = False
    materiality_signal_abs: int = 5
    materiality_signal_frac: float = 0.05
    materiality_mean_net_abs: float = 0.002
    audit_expanding_n: int = AUDIT_EXPANDING_N


def make_config(lookback_mode: str) -> FrozenConfig:
    if lookback_mode not in (LOOKBACK_MODE_A, LOOKBACK_MODE_B):
        raise ValueError(f"unknown lookback_mode={lookback_mode!r}")
    return FrozenConfig(lookback_mode=lookback_mode)


def arm_configs() -> tuple[FrozenConfig, FrozenConfig]:
    return make_config(LOOKBACK_MODE_A), make_config(LOOKBACK_MODE_B)


def configs_identical_except_lookback_mode(a: FrozenConfig, b: FrozenConfig) -> bool:
    da, db = asdict(a), asdict(b)
    ma = da.pop("lookback_mode")
    mb = db.pop("lookback_mode")
    return da == db and ma != mb and {ma, mb} == {LOOKBACK_MODE_A, LOOKBACK_MODE_B}


def shared_config_dict(cfg: FrozenConfig) -> dict:
    d = asdict(cfg)
    d.pop("lookback_mode")
    d["lookbacks_h"] = list(d["lookbacks_h"])
    d["down_percentiles"] = list(d["down_percentiles"])
    d["up_percentiles"] = list(d["up_percentiles"])
    d["holds_h"] = list(d["holds_h"])
    return d


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def git_head() -> str:
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=REPO,
            stderr=subprocess.STDOUT,
            text=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError, OSError) as exc:
        raise RuntimeError(f"CODE_COMMIT requires git rev-parse HEAD: {exc}") from exc
    sha = out.strip()
    if not CODE_COMMIT_RE.fullmatch(sha):
        raise RuntimeError(f"CODE_COMMIT must be a 40-char lowercase hex SHA, got {sha!r}")
    return sha


def git_object_exists(sha: str) -> bool:
    proc = subprocess.run(
        ["git", "cat-file", "-e", sha],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    )
    return proc.returncode == 0


def commit_has_path(sha: str, relpath: str) -> bool:
    proc = subprocess.run(
        ["git", "cat-file", "-e", f"{sha}:{relpath}"],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    )
    return proc.returncode == 0


def paths_missing_from_commit(sha: str, relpaths: tuple[str, ...] | list[str]) -> list[str]:
    return [rel for rel in relpaths if not commit_has_path(sha, rel)]


def harness_worktree_dirty() -> list[str]:
    proc = subprocess.run(
        ["git", "status", "--porcelain", "--", *REQUIRED_HARNESS_PATHS],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"git status failed: {proc.stderr.strip()}")
    return [line for line in proc.stdout.splitlines() if line.strip()]


def resolve_code_commit() -> str:
    sha = git_head()
    if not git_object_exists(sha):
        raise RuntimeError(f"CODE_COMMIT {sha} is not a git object")
    missing = paths_missing_from_commit(sha, REQUIRED_HARNESS_PATHS)
    if missing:
        raise RuntimeError(
            "CODE_COMMIT does not contain executed harness code: "
            + f"{sha} missing {missing}. Commit runner/spec/tests before materializing a run."
        )
    dirty = harness_worktree_dirty()
    if dirty:
        raise RuntimeError(
            "refuse to materialize with uncommitted runner/spec/test/fixture changes: "
            + "; ".join(dirty)
        )
    return sha


def environment() -> dict:
    return {
        "python": sys.version.replace("\n", " "),
        "platform": platform.platform(),
        "executable": sys.executable,
    }


def log(msg: str) -> None:
    print(msg, flush=True)


def json_num(x):
    if x is None:
        return None
    if isinstance(x, (bool, np.bool_)):
        return bool(x)
    if isinstance(x, (np.integer, int)):
        return int(x)
    if isinstance(x, (np.floating, float)):
        xf = float(x)
        if not np.isfinite(xf):
            return None
        return xf
    return x


def csv_cell(v) -> str:
    if v is None:
        return ""
    if isinstance(v, (bool, np.bool_)):
        return "true" if bool(v) else "false"
    if isinstance(v, (np.integer, int)) and not isinstance(v, (bool, np.bool_)):
        return str(int(v))
    if isinstance(v, (np.floating, float)):
        xf = float(v)
        if not np.isfinite(xf):
            return ""
        return format(xf, ".16g")
    return str(v)


def write_csv(path: Path, rows: list[dict], fieldnames: tuple[str, ...]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        writer = csv.DictWriter(f, fieldnames=list(fieldnames), extrasaction="raise")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: csv_cell(row.get(k)) for k in fieldnames})


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def pct_label(p: float) -> str:
    mapping = {
        0.01: "p1",
        0.025: "p2.5",
        0.05: "p5",
        0.95: "p95",
        0.975: "p97.5",
        0.99: "p99",
    }
    for k, v in mapping.items():
        if abs(p - k) < 1e-12:
            return v
    return f"p{p}"


def thesis_name(tail: str, direction: str) -> str:
    if tail == "down" and direction == "long":
        return "rebound"
    if tail == "down" and direction == "short":
        return "continuation"
    if tail == "up" and direction == "long":
        return "continuation"
    return "reversal"


def rule_id(lookback: int, tail: str, p: float, direction: str, hold: int) -> str:
    return (
        f"L{lookback}_{tail}_{pct_label(p)}_{thesis_name(tail, direction)}"
        f"_{direction}_H{hold}"
    )


def net_from_gross(gross: np.ndarray, fee: float) -> np.ndarray:
    g = np.asarray(gross, dtype=float)
    return (1.0 + g) * (1.0 - fee) - 1.0


def sharpe_trades(nets: np.ndarray, span_days: float, crypto_days: float) -> float:
    x = np.asarray(nets, dtype=float)
    x = x[np.isfinite(x)]
    if x.size < 2 or span_days <= 0:
        return np.nan
    sd = float(x.std(ddof=1))
    if sd <= 0:
        return np.nan
    years = span_days / crypto_days
    if years <= 0:
        return np.nan
    return float(x.mean() / sd * np.sqrt(x.size / years))


def hours_ahead_index(ts: pd.DatetimeIndex, h: int) -> np.ndarray:
    mapper = pd.Series(np.arange(len(ts), dtype=np.int64), index=ts)
    loc = mapper.reindex(ts + pd.Timedelta(hours=h))
    arr = loc.to_numpy(dtype=float)
    out = np.full(len(ts), -1, dtype=np.int64)
    ok = np.isfinite(arr)
    out[ok] = arr[ok].astype(np.int64)
    return out


def take_idx(ahead: np.ndarray, src: np.ndarray) -> np.ndarray:
    out = np.full(len(src), -1, dtype=np.int64)
    ok = src >= 0
    if ok.any():
        out[ok] = ahead[src[ok]]
    return out


def behind_indices(ts: pd.DatetimeIndex, lookback_h: int, mode: str) -> np.ndarray:
    """Row index of the lookback bar, or -1 if ineligible.

    LEGACY_POSITIONAL: i - L (row offset; E-02 failure mode).
    EXACT_TIMESTAMP: vectorized temporal.exact_timestamp.lookup_exact(t − L hours).
    """
    n = len(ts)
    L = int(lookback_h)
    if mode == LOOKBACK_MODE_A:
        out = np.full(n, -1, dtype=np.int64)
        if 0 < L < n:
            out[L:] = np.arange(n - L, dtype=np.int64)
        return out
    if mode == LOOKBACK_MODE_B:
        ts_utc = as_utc_index(ts)
        loc = ts_utc.get_indexer(ts_utc - pd.Timedelta(hours=L))
        return np.asarray(loc, dtype=np.int64)
    raise ValueError(f"unknown lookback_mode={mode!r}")


def trailing_return_from_behind(closes: np.ndarray, behind: np.ndarray) -> np.ndarray:
    n = len(closes)
    ret = np.full(n, np.nan, dtype=float)
    ok = behind >= 0
    if not ok.any():
        return ret
    prev = closes[behind[ok]]
    cur = closes[ok]
    good = (prev > 0) & (cur > 0)
    idx = np.flatnonzero(ok)
    ret[idx[good]] = cur[good] / prev[good] - 1.0
    return ret


def exact_behind_matches_primitive(ts: pd.DatetimeIndex, lookback_h: int, behind: np.ndarray) -> bool:
    """True if vectorized exact behind agrees with lookback_index for every row."""
    ts_utc = as_utc_index(ts)
    delta = pd.Timedelta(hours=int(lookback_h))
    for i, t in enumerate(ts_utc):
        prim = lookback_index(ts_utc, t, delta)
        vec = int(behind[i])
        if prim is None:
            if vec != -1:
                return False
        elif vec != int(prim):
            return False
    return True


class FenwickOS:
    def __init__(self, n: int):
        self.n = int(n)
        self.bit = np.zeros(self.n + 1, dtype=np.int64)
        self.max_pow = 1 << (self.n.bit_length() - 1) if self.n else 1

    def add(self, rank: int, delta: int = 1) -> None:
        i = int(rank) + 1
        bit = self.bit
        n = self.n
        while i <= n:
            bit[i] += delta
            i += i & -i

    def kth(self, k: int) -> int:
        idx = 0
        bit = self.max_pow
        tree = self.bit
        n = self.n
        k = int(k)
        while bit:
            t = idx + bit
            if t <= n and tree[t] < k:
                idx = t
                k -= int(tree[t])
            bit >>= 1
        return idx


def expanding_quantiles(
    ret: np.ndarray,
    ts: pd.DatetimeIndex,
    probs: tuple[float, ...],
    min_cal_days: int,
) -> dict[float, np.ndarray]:
    """Percentile of {ret_s : timestamp s < t}, after min_cal_days from first valid ret."""
    n = len(ret)
    out = {p: np.full(n, np.nan, dtype=float) for p in probs}
    valid = np.isfinite(ret)
    idx = np.flatnonzero(valid)
    m = int(idx.size)
    if m < 2:
        return out
    vals = ret[idx]
    order = np.argsort(vals, kind="mergesort")
    rank = np.empty(m, dtype=np.int64)
    rank[order] = np.arange(m, dtype=np.int64)
    sorted_vals = vals[order]
    first_ts = ts[int(idx[0])]
    min_ts = first_ts + pd.Timedelta(days=int(min_cal_days))
    min_i = int(ts.searchsorted(min_ts))
    bit = FenwickOS(m)
    inserted = 0
    j = 0
    for i in range(n):
        if inserted >= 2 and i >= min_i:
            n_ins = inserted
            for p in probs:
                h = (n_ins - 1) * p
                lo = int(np.floor(h))
                hi = int(np.ceil(h))
                vlo = float(sorted_vals[bit.kth(lo + 1)])
                if lo == hi:
                    out[p][i] = vlo
                else:
                    vhi = float(sorted_vals[bit.kth(hi + 1)])
                    out[p][i] = vlo + (h - lo) * (vhi - vlo)
        if valid[i]:
            bit.add(int(rank[j]), 1)
            inserted += 1
            j += 1
    return out


def audit_expanding(
    ret: np.ndarray,
    ts: pd.DatetimeIndex,
    q: np.ndarray,
    p: float,
    n_check: int = AUDIT_EXPANDING_N,
) -> None:
    cand = np.flatnonzero(np.isfinite(q) & np.isfinite(ret))
    if cand.size == 0:
        raise RuntimeError(f"no expanding quantile observations for p={p}")
    rng = np.random.default_rng(0)
    pick = rng.choice(cand, size=min(n_check, int(cand.size)), replace=False)
    for i in pick:
        i = int(i)
        hist = ret[:i]
        hist = hist[np.isfinite(hist)]
        if hist.size < 2:
            raise RuntimeError("expanding audit hit too-short history")
        if np.any(ts[:i] >= ts[i]):
            raise RuntimeError("expanding audit: history timestamps not strictly before t")
        ref = float(np.quantile(hist, p, method="linear"))
        got = float(q[i])
        scale = max(1.0, abs(ref))
        if abs(ref - got) > 1e-10 * scale:
            raise RuntimeError(
                f"expanding percentile mismatch at t={i} p={p}: got={got} ref={ref}"
            )


def load_bars_csv(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    if "timestamp_utc" not in df.columns:
        raise RuntimeError(f"{path} missing timestamp_utc")
    df = df.copy()
    df["ts_utc"] = pd.to_datetime(df["timestamp_utc"], utc=True)
    for c in ("open", "high", "low", "close"):
        if c not in df.columns:
            raise RuntimeError(f"{path} missing {c}")
        df[c] = pd.to_numeric(df[c], errors="coerce")
    n_raw = len(df)
    df = df.dropna(subset=["ts_utc", "open", "high", "low", "close"]).copy()
    n_ohlc_drop = n_raw - len(df)
    dup = int(df["ts_utc"].duplicated().sum())
    df = df.sort_values("ts_utc").drop_duplicates("ts_utc", keep="first")
    if not bool(df["ts_utc"].is_monotonic_increasing) or not bool(df["ts_utc"].is_unique):
        raise RuntimeError("UTC timestamps are not unique/chronological after clean.")
    full = pd.date_range(df["ts_utc"].min(), df["ts_utc"].max(), freq="h", tz="UTC")
    missing = full.difference(pd.DatetimeIndex(df["ts_utc"]))
    df.attrs["meta"] = {
        "n_raw": n_raw,
        "n_bars": int(len(df)),
        "n_ohlc_drop": int(n_ohlc_drop),
        "n_dup_dropped": dup,
        "n_missing_hours": int(len(missing)),
        "start_utc": df["ts_utc"].min(),
        "end_utc": df["ts_utc"].max(),
        "path": str(path),
    }
    return df.reset_index(drop=True)


def load_hourly(cfg: FrozenConfig) -> pd.DataFrame:
    path = REPO / cfg.dataset_relpath
    if not path.exists():
        raise RuntimeError(f"No local 1h BTCUSDT file at {path}. Will not download a substitute.")
    return load_bars_csv(path)


def load_frozen_top10(path: Path | None = None) -> list[dict]:
    p = path if path is not None else REPO / FROZEN_TOP10_REL
    df = pd.read_csv(p)
    if "rule_id" not in df.columns:
        raise RuntimeError(f"{p} missing rule_id")
    if len(df) != 10:
        raise RuntimeError(f"frozen Top 10 must have 10 rows, got {len(df)}")
    ids = df["rule_id"].astype(str).tolist()
    if len(set(ids)) != 10:
        raise RuntimeError("duplicate rule_id in frozen Top 10")
    ranks = df["discovery_rank"].astype(int).tolist() if "discovery_rank" in df.columns else list(range(1, 11))
    out = []
    for i, rid in enumerate(ids):
        out.append({"discovery_rank": int(ranks[i]), "rule_id": rid})
    return out


def frozen_top10_ids(rows: list[dict] | None = None) -> list[str]:
    rows = rows if rows is not None else load_frozen_top10()
    return [r["rule_id"] for r in rows]


def period_of(ts: pd.DatetimeIndex, cfg: FrozenConfig) -> np.ndarray:
    out = np.empty(len(ts), dtype=object)
    ns = ts.asi8
    disc = pd.Timestamp(cfg.disc_end_utc).value
    val = pd.Timestamp(cfg.val_end_utc).value
    out[ns < disc] = "discovery"
    out[(ns >= disc) & (ns < val)] = "validation"
    out[ns >= val] = "recent"
    return out


def period_span_days(meta: dict, period: str, cfg: FrozenConfig) -> float:
    start = meta["start_utc"]
    end = meta["end_utc"]
    disc = pd.Timestamp(cfg.disc_end_utc)
    val = pd.Timestamp(cfg.val_end_utc)
    if period == "discovery":
        a, b = start, disc
    elif period == "validation":
        a, b = disc, val
    else:
        a, b = val, end + pd.Timedelta(hours=1)
    return max(float((b - a).total_seconds() / 86400.0), 1.0)


def dist_stats(cond: np.ndarray, uncond: np.ndarray) -> dict:
    c = np.asarray(cond, dtype=float)
    u = np.asarray(uncond, dtype=float)
    c = c[np.isfinite(c)]
    u = u[np.isfinite(u)]
    out = {
        "cond_mean": float(c.mean()) if c.size else np.nan,
        "uncond_mean": float(u.mean()) if u.size else np.nan,
        "n_cond": int(c.size),
        "n_uncond": int(u.size),
    }
    out["diff_mean"] = out["cond_mean"] - out["uncond_mean"]
    return out


def executable_take(valid: np.ndarray, entry_idx: np.ndarray, ts_ns: np.ndarray, hold_h: int) -> np.ndarray:
    take = np.zeros(len(valid), dtype=bool)
    busy_until = np.int64(-1)
    hold_ns = np.int64(hold_h) * np.int64(HOUR_NS)
    for t in np.flatnonzero(valid):
        e_i = int(entry_idx[t])
        e_ns = ts_ns[e_i]
        if e_ns < busy_until:
            continue
        take[t] = True
        busy_until = e_ns + hold_ns
    return take


def mean_net_sign(x) -> str:
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return "nan"
    if x > 0:
        return "pos"
    if x < 0:
        return "neg"
    return "zero"


def signal_material_threshold(n_legacy: int, cfg: FrozenConfig) -> int:
    return max(int(cfg.materiality_signal_abs), int(cfg.materiality_signal_frac * max(int(n_legacy), 1)))


def cell_signal_material(n_disappeared: int, n_appeared: int, n_legacy: int, cfg: FrozenConfig) -> bool:
    return (int(n_disappeared) + int(n_appeared)) >= signal_material_threshold(n_legacy, cfg)


def economic_material(delta_mean_net, cfg: FrozenConfig) -> bool:
    if delta_mean_net is None or (isinstance(delta_mean_net, float) and not np.isfinite(delta_mean_net)):
        return False
    return abs(float(delta_mean_net)) > float(cfg.materiality_mean_net_abs)


def load_historical_l6_label() -> dict:
    path = REPO / FROZEN_VAL_REL
    if not path.is_file():
        return {}
    df = pd.read_csv(path)
    hit = df.loc[df["rule_id"].astype(str) == L6_CANDIDATE_ID]
    if hit.empty:
        return {}
    r = hit.iloc[0]
    return {
        "source": FROZEN_VAL_REL,
        "note": "Phase 4 historical labels only. Causal contrast is A vs B in this pipeline.",
        "discovery_n_trades": json_num(r.get("disc_n_trades")),
        "discovery_mean_net_trade": json_num(r.get("disc_mean_net_trade")),
        "validation_n_trades": json_num(r.get("val_n_trades")),
        "validation_mean_net_trade": json_num(r.get("val_mean_net_trade")),
        "recent_n_trades": json_num(r.get("rec_n_trades")),
        "recent_mean_net_trade": json_num(r.get("rec_mean_net_trade")),
    }


def scan_arm(
    cfg: FrozenConfig,
    ts: pd.DatetimeIndex,
    closes: np.ndarray,
    opens: np.ndarray,
    periods: np.ndarray,
    entry_idx: np.ndarray,
    exit_for: dict[int, np.ndarray],
    fwd_long: dict[int, np.ndarray],
    fwd_short: dict[int, np.ndarray],
    uncond: dict,
    span: dict[str, float],
    ts_ns: np.ndarray,
) -> dict:
    if cfg.reselect_top:
        raise RuntimeError("reselect_top must remain False")
    if cfg.use_mtm_primary:
        raise RuntimeError("use_mtm_primary must remain False")
    if cfg.change_survivor_gate:
        raise RuntimeError("change_survivor_gate must remain False")

    n = len(closes)
    all_probs = tuple(sorted(set(cfg.down_percentiles + cfg.up_percentiles)))
    behind_map: dict[int, np.ndarray] = {}
    ret_map: dict[int, np.ndarray] = {}
    q_map: dict[int, dict[float, np.ndarray]] = {}
    for L in cfg.lookbacks_h:
        behind_map[L] = behind_indices(ts, L, cfg.lookback_mode)
        ret_map[L] = trailing_return_from_behind(closes, behind_map[L])
        q_map[L] = expanding_quantiles(ret_map[L], ts, all_probs, cfg.min_history_calendar_days)
        for p in all_probs:
            audit_expanding(ret_map[L], ts, q_map[L][p], p, cfg.audit_expanding_n)
        log(f"  arm {cfg.lookback_mode} L{L}h expanding quantiles audited")

    signals: dict[tuple[int, str, float], np.ndarray] = {}
    rules: dict[tuple[str, str], dict] = {}
    for L in cfg.lookbacks_h:
        ret = ret_map[L]
        for tail, pcts in (("down", cfg.down_percentiles), ("up", cfg.up_percentiles)):
            for p in pcts:
                q = q_map[L][p]
                finite = np.isfinite(ret) & np.isfinite(q)
                if tail == "down":
                    sig = finite & (ret <= q)
                else:
                    sig = finite & (ret >= q)
                signals[(int(L), tail, float(p))] = sig
                has_entry = sig & (entry_idx >= 0)
                for h in cfg.holds_h:
                    x = exit_for[h]
                    has_exit = has_entry & (x >= 0)
                    for direction in ("long", "short"):
                        rid = rule_id(int(L), tail, float(p), direction, int(h))
                        thesis = thesis_name(tail, direction)
                        fwd_s = fwd_long[h] if direction == "long" else fwd_short[h]
                        valid_event = has_exit & np.isfinite(fwd_s)
                        take_all = executable_take(valid_event, entry_idx, ts_ns, int(h))
                        for period in PERIODS:
                            ev = valid_event & (periods == period)
                            tk = take_all & (periods == period)
                            st = dist_stats(fwd_s[ev], uncond[h][period][direction])
                            g = fwd_s[tk]
                            g = g[np.isfinite(g)]
                            nets = net_from_gross(g, cfg.fee_round_trip) if g.size else g
                            rules[(rid, period)] = {
                                "rule_id": rid,
                                "period": period,
                                "lookback_h": int(L),
                                "tail": tail,
                                "percentile": float(p),
                                "percentile_label": pct_label(float(p)),
                                "direction": direction,
                                "thesis": thesis,
                                "hold_h": int(h),
                                "n_signals": int((sig & (periods == period)).sum()),
                                "n_events": int(ev.sum()),
                                "n_trades": int(g.size),
                                "mean_trade_gross": float(g.mean()) if g.size else np.nan,
                                "mean_net_trade": float(nets.mean()) if nets.size else np.nan,
                                "sharpe_trades": sharpe_trades(nets, span[period], cfg.crypto_days),
                                "uncond_mean": st["uncond_mean"],
                                "cond_mean": st["cond_mean"],
                                "cond_adv": st["diff_mean"],
                            }
                log(
                    f"  arm {cfg.lookback_mode} scanned L{L} {tail} {pct_label(float(p))} "
                    f"signals={int(sig.sum())}"
                )
    return {
        "mode": cfg.lookback_mode,
        "behind": behind_map,
        "ret": ret_map,
        "q": q_map,
        "signals": signals,
        "rules": rules,
        "n_bars": n,
    }


def build_shared_execution(df: pd.DataFrame, cfg: FrozenConfig) -> dict:
    ts = pd.DatetimeIndex(df["ts_utc"])
    n = len(df)
    opens = df["open"].to_numpy(dtype=float)
    closes = df["close"].to_numpy(dtype=float)
    ts_ns = ts.asi8
    periods = period_of(ts, cfg)
    meta = df.attrs["meta"]
    span = {p: period_span_days(meta, p, cfg) for p in PERIODS}
    needed_h = sorted(set(cfg.holds_h) | {cfg.entry_offset_h})
    ahead = {h: hours_ahead_index(ts, h) for h in needed_h}
    entry_idx = ahead[cfg.entry_offset_h]
    fwd_long = {}
    fwd_short = {}
    exit_for = {}
    for h in cfg.holds_h:
        x = take_idx(ahead[h], entry_idx)
        ok = (entry_idx >= 0) & (x >= 0)
        fl = np.full(n, np.nan)
        fs = np.full(n, np.nan)
        fl[ok] = opens[x[ok]] / opens[entry_idx[ok]] - 1.0
        fs[ok] = opens[entry_idx[ok]] / opens[x[ok]] - 1.0
        fwd_long[h] = fl
        fwd_short[h] = fs
        exit_for[h] = x
    uncond = {h: {} for h in cfg.holds_h}
    for h in cfg.holds_h:
        for p in PERIODS:
            m = (periods == p) & np.isfinite(fwd_long[h])
            uncond[h][p] = {"long": fwd_long[h][m], "short": fwd_short[h][m]}
    return {
        "ts": ts,
        "n": n,
        "opens": opens,
        "closes": closes,
        "ts_ns": ts_ns,
        "periods": periods,
        "span": span,
        "entry_idx": entry_idx,
        "exit_for": exit_for,
        "fwd_long": fwd_long,
        "fwd_short": fwd_short,
        "uncond": uncond,
        "meta": meta,
    }


SIGNAL_FIELDS = (
    "lookback_h",
    "tail",
    "percentile",
    "percentile_label",
    "period",
    "n_signals_A",
    "n_signals_B",
    "n_overlap",
    "n_disappeared",
    "n_appeared",
    "n_legacy_missing_exact_tl",
    "abs_diff",
    "pct_diff",
    "symmetric_diff",
    "materiality_threshold",
    "signal_material",
)

RULE_FIELDS = (
    "rule_id",
    "lookback_h",
    "tail",
    "percentile",
    "percentile_label",
    "direction",
    "thesis",
    "hold_h",
    "period",
    "is_frozen_top10",
    "n_events_A",
    "n_events_B",
    "n_trades_A",
    "n_trades_B",
    "mean_gross_A",
    "mean_gross_B",
    "delta_mean_gross",
    "mean_net_A",
    "mean_net_B",
    "delta_mean_net",
    "sharpe_A",
    "sharpe_B",
    "delta_sharpe",
    "uncond_mean_A",
    "uncond_mean_B",
    "cond_adv_A",
    "cond_adv_B",
    "delta_cond_adv",
    "mean_net_sign_A",
    "mean_net_sign_B",
    "sign_change",
    "economic_material",
)

TOP10_FIELDS = ("discovery_rank",) + RULE_FIELDS


def impact_tables(arm_a: dict, arm_b: dict, cfg: FrozenConfig, top_rows: list[dict], periods: np.ndarray) -> dict:
    top_ids = [r["rule_id"] for r in top_rows]
    rank_map = {r["rule_id"]: int(r["discovery_rank"]) for r in top_rows}
    signal_rows = []
    for L in cfg.lookbacks_h:
        for tail, pcts in (("down", cfg.down_percentiles), ("up", cfg.up_percentiles)):
            for p in pcts:
                sig_a = arm_a["signals"][(int(L), tail, float(p))]
                sig_b = arm_b["signals"][(int(L), tail, float(p))]
                behind_b = arm_b["behind"][int(L)]
                for period in ("all",) + PERIODS:
                    if period == "all":
                        mask = np.ones(len(sig_a), dtype=bool)
                    else:
                        mask = periods == period
                    a = sig_a & mask
                    b = sig_b & mask
                    n_a = int(a.sum())
                    n_b = int(b.sum())
                    n_overlap = int((a & b).sum())
                    n_dis = int((a & ~b).sum())
                    n_app = int((b & ~a).sum())
                    n_miss = int((a & (behind_b < 0)).sum())
                    abs_diff = abs(n_b - n_a)
                    pct_diff = (n_b - n_a) / n_a if n_a else np.nan
                    sym = n_dis + n_app
                    thr = signal_material_threshold(n_a, cfg)
                    signal_rows.append(
                        {
                            "lookback_h": int(L),
                            "tail": tail,
                            "percentile": float(p),
                            "percentile_label": pct_label(float(p)),
                            "period": period,
                            "n_signals_A": n_a,
                            "n_signals_B": n_b,
                            "n_overlap": n_overlap,
                            "n_disappeared": n_dis,
                            "n_appeared": n_app,
                            "n_legacy_missing_exact_tl": n_miss,
                            "abs_diff": abs_diff,
                            "pct_diff": pct_diff,
                            "symmetric_diff": sym,
                            "materiality_threshold": thr,
                            "signal_material": cell_signal_material(n_dis, n_app, n_a, cfg),
                        }
                    )

    rule_rows = []
    for key in sorted(arm_a["rules"].keys(), key=lambda k: (k[0], k[1])):
        ra = arm_a["rules"][key]
        rb = arm_b["rules"][key]
        if ra["uncond_mean"] != rb["uncond_mean"] and not (
            (not np.isfinite(ra["uncond_mean"])) and (not np.isfinite(rb["uncond_mean"]))
        ):
            # Unconditional control must be arm-independent.
            ua, ub = ra["uncond_mean"], rb["uncond_mean"]
            if np.isfinite(ua) and np.isfinite(ub) and abs(ua - ub) > 1e-15:
                raise RuntimeError(f"uncond control diverged for {key}: {ua} vs {ub}")
        delta_net = rb["mean_net_trade"] - ra["mean_net_trade"]
        econ = False
        if ra["period"] in ("discovery", "validation"):
            econ = economic_material(delta_net, cfg)
        sign_a = mean_net_sign(ra["mean_net_trade"])
        sign_b = mean_net_sign(rb["mean_net_trade"])
        rule_rows.append(
            {
                "rule_id": ra["rule_id"],
                "lookback_h": ra["lookback_h"],
                "tail": ra["tail"],
                "percentile": ra["percentile"],
                "percentile_label": ra["percentile_label"],
                "direction": ra["direction"],
                "thesis": ra["thesis"],
                "hold_h": ra["hold_h"],
                "period": ra["period"],
                "is_frozen_top10": ra["rule_id"] in top_ids,
                "n_events_A": ra["n_events"],
                "n_events_B": rb["n_events"],
                "n_trades_A": ra["n_trades"],
                "n_trades_B": rb["n_trades"],
                "mean_gross_A": ra["mean_trade_gross"],
                "mean_gross_B": rb["mean_trade_gross"],
                "delta_mean_gross": rb["mean_trade_gross"] - ra["mean_trade_gross"],
                "mean_net_A": ra["mean_net_trade"],
                "mean_net_B": rb["mean_net_trade"],
                "delta_mean_net": delta_net,
                "sharpe_A": ra["sharpe_trades"],
                "sharpe_B": rb["sharpe_trades"],
                "delta_sharpe": rb["sharpe_trades"] - ra["sharpe_trades"],
                "uncond_mean_A": ra["uncond_mean"],
                "uncond_mean_B": rb["uncond_mean"],
                "cond_adv_A": ra["cond_adv"],
                "cond_adv_B": rb["cond_adv"],
                "delta_cond_adv": rb["cond_adv"] - ra["cond_adv"],
                "mean_net_sign_A": sign_a,
                "mean_net_sign_B": sign_b,
                "sign_change": sign_a != sign_b,
                "economic_material": econ,
            }
        )

    top10_rows = []
    for tr in top_rows:
        rid = tr["rule_id"]
        for period in PERIODS:
            hits = [r for r in rule_rows if r["rule_id"] == rid and r["period"] == period]
            if not hits:
                raise RuntimeError(f"missing impact row for frozen Top 10 rule {rid} {period}")
            row = dict(hits[0])
            row["discovery_rank"] = int(tr["discovery_rank"])
            top10_rows.append(row)
    top10_rows.sort(key=lambda r: (r["discovery_rank"], PERIODS.index(r["period"])))

    pooled_signal = [r for r in signal_rows if r["period"] == "all"]
    n_signal_cells_material = sum(1 for r in pooled_signal if r["signal_material"])
    econ_dv = [r for r in rule_rows if r["period"] in ("discovery", "validation")]
    n_econ_material = sum(1 for r in econ_dv if r["economic_material"])
    val_sign_changes = [r for r in rule_rows if r["period"] == "validation" and r["sign_change"]]
    top10_econ_material = [
        r for r in top10_rows if r["period"] in ("discovery", "validation") and r["economic_material"]
    ]
    top10_val_sign = [r for r in top10_rows if r["period"] == "validation" and r["sign_change"]]

    material = bool(n_signal_cells_material or n_econ_material)
    materiality = "MATERIAL" if material else "NOT_MATERIAL"

    l6_rows = [r for r in rule_rows if r["rule_id"] == cfg.l6_candidate_id]
    l6_by_period = {r["period"]: r for r in l6_rows}

    return {
        "signal_rows": signal_rows,
        "rule_rows": rule_rows,
        "top10_rows": top10_rows,
        "materiality": materiality,
        "n_signal_cells": len(pooled_signal),
        "n_signal_cells_material": int(n_signal_cells_material),
        "n_rules": int(len({r["rule_id"] for r in rule_rows})),
        "n_econ_material_disc_or_val": int(n_econ_material),
        "n_validation_sign_changes": int(len(val_sign_changes)),
        "n_top10_econ_material_disc_or_val": int(len(top10_econ_material)),
        "n_top10_validation_sign_changes": int(len(top10_val_sign)),
        "material_signal_cells": [
            {
                "lookback_h": r["lookback_h"],
                "tail": r["tail"],
                "percentile_label": r["percentile_label"],
                "symmetric_diff": r["symmetric_diff"],
                "n_signals_A": r["n_signals_A"],
                "n_signals_B": r["n_signals_B"],
            }
            for r in pooled_signal
            if r["signal_material"]
        ],
        "material_rules_disc_or_val": [
            {
                "rule_id": r["rule_id"],
                "period": r["period"],
                "delta_mean_net": json_num(r["delta_mean_net"]),
                "mean_net_A": json_num(r["mean_net_A"]),
                "mean_net_B": json_num(r["mean_net_B"]),
            }
            for r in econ_dv
            if r["economic_material"]
        ],
        "validation_sign_change_rules": [
            {
                "rule_id": r["rule_id"],
                "mean_net_sign_A": r["mean_net_sign_A"],
                "mean_net_sign_B": r["mean_net_sign_B"],
                "mean_net_A": json_num(r["mean_net_A"]),
                "mean_net_B": json_num(r["mean_net_B"]),
            }
            for r in val_sign_changes
        ],
        "l6_by_period": l6_by_period,
        "rank_map": rank_map,
        "top_ids": top_ids,
    }


def fmt_pct(x, nd=3) -> str:
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return "NA"
    return f"{100.0 * float(x):.{nd}f}%"


def fmt_num(x, nd=4) -> str:
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return "NA"
    return f"{float(x):.{nd}f}"


def render_report(payload: dict, impact: dict, cfg: FrozenConfig) -> str:
    mat = payload["materiality"]
    g = payload["global_summary"]
    l6 = payload["l6_candidate_summary"]
    lines = [
        "# EXT-C02 — Isolated economic impact of E-02",
        "",
        "## Answer",
        "",
        (
            "Holding everything else identical, replacing positional lookback "
            f"(`close[i]/close[i-L]-1`) with exact calendar-timestamp lookback "
            f"(`close(t)/close(t-L hours)-1`, ineligible if exact t-L is missing) "
            f"is **{mat}** under the predeclared Phase 4b criterion "
            f"(symmetric signal difference >= max(5, int(5% of legacy N)), or "
            f"absolute mean-net change > 0.002 in Discovery or Validation)."
        ),
        "",
        (
            f"Pooled signal cells tripping the signal threshold: "
            f"{g['n_signal_cells_material']} / {g['n_signal_cells']}. "
            f"Frozen-rule Discovery/Validation mean-net cells tripping the economic threshold: "
            f"{g['n_econ_material_disc_or_val']}. "
            f"Validation mean-net sign changes (reported even if NOT_MATERIAL): "
            f"{g['n_validation_sign_changes']}."
        ),
        "",
        "Numeric truth is `outputs/*.csv` and `result/RESULT.json`. This markdown does not override them.",
        "",
        "This measurement is not a trading-edge claim, does not authorize capital, is not clean OOS, "
        "does not reselect, and does not close E-02. HYP-BTC-002 remains INVALIDATED. "
        "E-03 and E-04 remain OPEN. Mechanical_gate is separate from MATERIAL / NOT_MATERIAL.",
        "",
        "## Discrepancy vs Phase 4b report",
        "",
        "Phase 4b (`phase4b_extreme_move_audit_fix/`) mixed exact-timestamp lookback with a stricter "
        "survivor-gate rewrite and hourly mark-to-market equity, and it compared that mixed program "
        "to historical Phase 4 outputs. EXT-C02 does not do that. Both arms here walk the same Phase 4 "
        "design inside one shared config; the only allowed difference is `lookback_mode`. "
        "Survivor-gate classifications are not recomputed. Equity MTM is not a primary metric. "
        "Therefore Phase 4b's mixed L6 counts, MTM Sharpe/MaxDD, and classification changes are not "
        "the causal answer to this question, even when some trailing-return numbers are close.",
        "",
        "## Frozen design (shared)",
        "",
        f"- Dataset: `{payload['dataset_path']}` SHA-256 `{payload['dataset_sha256']}`",
        f"- Coverage: {payload['temporal_coverage']['start_utc']} → {payload['temporal_coverage']['end_utc']} "
        f"(n_bars={payload['temporal_coverage']['n_bars']}, missing_hours={payload['temporal_coverage']['n_missing_hours']})",
        f"- Lookbacks: {list(cfg.lookbacks_h)} h; percentiles down {list(cfg.down_percentiles)} / "
        f"up {list(cfg.up_percentiles)}; holds {list(cfg.holds_h)} h",
        f"- Fee: {cfg.fee_round_trip} round trip; expanding history {cfg.min_history_calendar_days} calendar days; "
        f"information strictly before t",
        f"- Frozen Top 10 source: `{cfg.frozen_top10_relpath}` (read-only; no reselection)",
        f"- only_lookback_mode_differs: {payload['only_lookback_mode_differs']}",
        "",
        "## Arm definitions",
        "",
        "- A LEGACY_POSITIONAL: close[i]/close[i-L]-1",
        "- B EXACT_TIMESTAMP: close(t)/close(t-L hours)-1; eligible only if exact t-L exists; "
        "semantics from temporal/exact_timestamp.py; no nearest-bar/fill/interpolation/substitution",
        "",
        "## Materiality criterion (predeclared)",
        "",
        json.dumps(payload["predeclared_materiality_criterion"], indent=2, sort_keys=True),
        "",
        f"Decision: **{mat}**",
        "",
        "## L6_down_p1_rebound_long_H6 (both arms in this pipeline)",
        "",
    ]
    hist = l6.get("historical_phase4_label_only") or {}
    if hist:
        lines.append(
            "Phase 4 historical labels (not the causal contrast): "
            f"discovery N={hist.get('discovery_n_trades')} mean net={fmt_pct(hist.get('discovery_mean_net_trade'))}; "
            f"validation N={hist.get('validation_n_trades')} mean net={fmt_pct(hist.get('validation_mean_net_trade'))}; "
            f"recent N={hist.get('recent_n_trades')} mean net={fmt_pct(hist.get('recent_mean_net_trade'))}."
        )
        lines.append("")
    lines.extend(
        [
            "| Period | N events A/B | N trades A/B | Mean net A | Mean net B | Delta B-A | Sign change | Economic material |",
            "|---|---:|---:|---:|---:|---:|---|---|",
        ]
    )
    for period in PERIODS:
        row = (l6.get("periods") or {}).get(period) or {}
        lines.append(
            f"| {period} | {row.get('n_events_A')}/{row.get('n_events_B')} | "
            f"{row.get('n_trades_A')}/{row.get('n_trades_B')} | "
            f"{fmt_pct(row.get('mean_net_A'))} | {fmt_pct(row.get('mean_net_B'))} | "
            f"{fmt_pct(row.get('delta_mean_net'))} | {row.get('sign_change')} | "
            f"{row.get('economic_material')} |"
        )
    lines.extend(
        [
            "",
            "## Frozen Top 10 (original discovery rank; no reselection)",
            "",
            f"Top 10 economic-material Discovery/Validation rows: {g['n_top10_econ_material_disc_or_val']}. "
            f"Top 10 Validation sign changes: {g['n_top10_validation_sign_changes']}.",
            "",
            "| Rank | Rule | Period | N trades A/B | Mean net A | Mean net B | Delta | Sign change |",
            "|---:|---|---|---:|---:|---:|---:|---|",
        ]
    )
    for row in impact["top10_rows"]:
        lines.append(
            f"| {row['discovery_rank']} | `{row['rule_id']}` | {row['period']} | "
            f"{row['n_trades_A']}/{row['n_trades_B']} | {fmt_pct(row['mean_net_A'])} | "
            f"{fmt_pct(row['mean_net_B'])} | {fmt_pct(row['delta_mean_net'])} | {row['sign_change']} |"
        )
    lines.extend(
        [
            "",
            "## Signal cells that trip the predeclared threshold (period=all)",
            "",
        ]
    )
    cells = payload["global_summary"]["material_signal_cells"]
    if not cells:
        lines.append("None.")
    else:
        for c in cells:
            lines.append(
                f"- L{c['lookback_h']} {c['tail']} {c['percentile_label']}: "
                f"A={c['n_signals_A']} B={c['n_signals_B']} symmetric_diff={c['symmetric_diff']}"
            )
    lines.extend(
        [
            "",
            "## Disclaimers",
            "",
            "- not_clean_oos: true",
            "- not_trading_edge: true",
            "- does_not_authorize_capital: true",
            "- E03_open: true",
            "- E04_open: true",
            "- E-02 remains FIXED_PENDING_VERIFICATION; EXT-H01 ChatGPT audit is not done in this task",
            "",
        ]
    )
    return "\n".join(lines)


def result_payload(
    run_id: str,
    computed: dict,
    cfg_a: FrozenConfig,
    cfg_b: FrozenConfig,
) -> dict:
    impact = computed["impact"]
    meta = computed["meta"]
    l6_by = impact["l6_by_period"]
    l6_periods = {}
    for period in PERIODS:
        r = l6_by.get(period, {})
        l6_periods[period] = {
            "n_events_A": json_num(r.get("n_events_A")),
            "n_events_B": json_num(r.get("n_events_B")),
            "n_trades_A": json_num(r.get("n_trades_A")),
            "n_trades_B": json_num(r.get("n_trades_B")),
            "mean_gross_A": json_num(r.get("mean_gross_A")),
            "mean_gross_B": json_num(r.get("mean_gross_B")),
            "mean_net_A": json_num(r.get("mean_net_A")),
            "mean_net_B": json_num(r.get("mean_net_B")),
            "delta_mean_net": json_num(r.get("delta_mean_net")),
            "sharpe_A": json_num(r.get("sharpe_A")),
            "sharpe_B": json_num(r.get("sharpe_B")),
            "cond_adv_A": json_num(r.get("cond_adv_A")),
            "cond_adv_B": json_num(r.get("cond_adv_B")),
            "uncond_mean_A": json_num(r.get("uncond_mean_A")),
            "uncond_mean_B": json_num(r.get("uncond_mean_B")),
            "mean_net_sign_A": r.get("mean_net_sign_A"),
            "mean_net_sign_B": r.get("mean_net_sign_B"),
            "sign_change": r.get("sign_change"),
            "economic_material": r.get("economic_material"),
        }
    top10_summary = []
    for tr in computed["top_rows"]:
        rid = tr["rule_id"]
        entry = {"discovery_rank": int(tr["discovery_rank"]), "rule_id": rid, "periods": {}}
        for period in PERIODS:
            r = next(x for x in impact["top10_rows"] if x["rule_id"] == rid and x["period"] == period)
            entry["periods"][period] = {
                "n_trades_A": json_num(r["n_trades_A"]),
                "n_trades_B": json_num(r["n_trades_B"]),
                "mean_net_A": json_num(r["mean_net_A"]),
                "mean_net_B": json_num(r["mean_net_B"]),
                "delta_mean_net": json_num(r["delta_mean_net"]),
                "sign_change": r["sign_change"],
                "economic_material": r["economic_material"],
            }
        top10_summary.append(entry)
    return {
        "objective": (
            "Holding everything else identical, measure how signals and economic results "
            "change when positional lookback is replaced by exact calendar-timestamp lookback."
        ),
        "task_id": TASK_ID,
        "experiment_id": EXPERIMENT_ID,
        "run_id": run_id,
        "hypothesis_id": HYPOTHESIS_ID,
        "hypothesis_version": "1",
        "hypothesis_lifecycle_unchanged": "INVALIDATED",
        "error_id": ERROR_ID,
        "error_e02_estado": "FIXED_PENDING_VERIFICATION",
        "e02_not_closed": True,
        "experiment_type": "ROBUSTNESS",
        "dataset_path": computed["data_path"],
        "dataset_sha256": computed["data_sha256"],
        "spec_path": computed["spec_path"],
        "spec_sha256": computed["spec_sha256"],
        "temporal_coverage": {
            "start_utc": str(meta["start_utc"]),
            "end_utc": str(meta["end_utc"]),
            "n_bars": int(meta["n_bars"]),
            "n_missing_hours": int(meta["n_missing_hours"]),
        },
        "frozen_config": shared_config_dict(cfg_a),
        "arm_definitions": {
            "A": {
                "lookback_mode": LOOKBACK_MODE_A,
                "formula": "close[i]/close[i-L]-1",
            },
            "B": {
                "lookback_mode": LOOKBACK_MODE_B,
                "formula": "close(t)/close(t-L hours)-1; eligible only if exact t-L exists; no nearest-bar/fill/interpolation/substitution",
                "semantics": "temporal.exact_timestamp.lookup_exact / DatetimeIndex.get_indexer",
            },
        },
        "only_lookback_mode_differs": configs_identical_except_lookback_mode(cfg_a, cfg_b),
        "frozen_top10_source": FROZEN_TOP10_REL,
        "frozen_top10_ids": impact["top_ids"],
        "reselect_top": False,
        "global_summary": {
            "n_signal_cells": impact["n_signal_cells"],
            "n_signal_cells_material": impact["n_signal_cells_material"],
            "n_rules": impact["n_rules"],
            "n_econ_material_disc_or_val": impact["n_econ_material_disc_or_val"],
            "n_validation_sign_changes": impact["n_validation_sign_changes"],
            "n_top10_econ_material_disc_or_val": impact["n_top10_econ_material_disc_or_val"],
            "n_top10_validation_sign_changes": impact["n_top10_validation_sign_changes"],
            "material_signal_cells": impact["material_signal_cells"],
            "material_rules_disc_or_val": impact["material_rules_disc_or_val"],
            "validation_sign_change_rules": impact["validation_sign_change_rules"],
        },
        "top10_summary": top10_summary,
        "l6_candidate_summary": {
            "rule_id": L6_CANDIDATE_ID,
            "historical_phase4_label_only": computed["historical_l6"],
            "periods": l6_periods,
        },
        "predeclared_materiality_criterion": {
            "source": "phase4b_extreme_move_audit_fix/src/audit_extreme_move_candidates.py (not retuned)",
            "signal": "n_disappeared + n_appeared >= max(5, int(0.05 * max(n_legacy, 1)))",
            "economic": "abs(mean_net_B - mean_net_A) > 0.002 in Discovery or Validation",
            "application": (
                "signal criterion on every lookback x tail x percentile cell (period=all); "
                "economic criterion on every frozen rule in Discovery and Validation; "
                "global MATERIAL if any of those trip; Validation sign changes reported even if NOT_MATERIAL"
            ),
            "signal_abs": cfg_a.materiality_signal_abs,
            "signal_frac": cfg_a.materiality_signal_frac,
            "mean_net_abs": cfg_a.materiality_mean_net_abs,
        },
        "materiality": impact["materiality"],
        "mechanical_gate": computed["mechanical_gate"],
        "mechanical_gate_is_separate_from_scientific_decision": True,
        "mechanical_gate_checks": computed["gates"],
        "disclaimers": {
            "not_clean_oos": True,
            "not_trading_edge": True,
            "does_not_authorize_capital": True,
            "E03_open": True,
            "E04_open": True,
        },
        "ext_h01_chatgpt_audit": "pending; not executed in EXT-C02",
    }


def compute(data_path: Path, spec_path: Path) -> dict:
    cfg_a, cfg_b = arm_configs()
    if not configs_identical_except_lookback_mode(cfg_a, cfg_b):
        raise RuntimeError("arm configs must differ only by lookback_mode")
    data_sha = sha256_file(data_path)
    spec_sha = sha256_file(spec_path)
    top_rows = load_frozen_top10(REPO / cfg_a.frozen_top10_relpath)
    if cfg_a.reselect_top or cfg_b.reselect_top:
        raise RuntimeError("reselection is forbidden")
    df = load_hourly(cfg_a)
    meta = df.attrs["meta"]
    shared = build_shared_execution(df, cfg_a)
    log("scanning arm A LEGACY_POSITIONAL")
    arm_a = scan_arm(
        cfg_a,
        shared["ts"],
        shared["closes"],
        shared["opens"],
        shared["periods"],
        shared["entry_idx"],
        shared["exit_for"],
        shared["fwd_long"],
        shared["fwd_short"],
        shared["uncond"],
        shared["span"],
        shared["ts_ns"],
    )
    log("scanning arm B EXACT_TIMESTAMP")
    arm_b = scan_arm(
        cfg_b,
        shared["ts"],
        shared["closes"],
        shared["opens"],
        shared["periods"],
        shared["entry_idx"],
        shared["exit_for"],
        shared["fwd_long"],
        shared["fwd_short"],
        shared["uncond"],
        shared["span"],
        shared["ts_ns"],
    )
    impact = impact_tables(arm_a, arm_b, cfg_a, top_rows, shared["periods"])
    historical_l6 = load_historical_l6_label()
    gates = {
        "dataset_sha256_match": data_sha == EXPECTED_DATASET_SHA256,
        "only_lookback_mode_differs": configs_identical_except_lookback_mode(cfg_a, cfg_b),
        "top10_count_is_10": len(top_rows) == 10,
        "reselect_top_false": (not cfg_a.reselect_top) and (not cfg_b.reselect_top),
        "mtm_not_primary": (not cfg_a.use_mtm_primary) and (not cfg_b.use_mtm_primary),
        "survivor_gate_unchanged": (not cfg_a.change_survivor_gate) and (not cfg_b.change_survivor_gate),
        "l6_present": cfg_a.l6_candidate_id in impact["top_ids"]
        or any(r["rule_id"] == cfg_a.l6_candidate_id for r in impact["rule_rows"]),
        "n_rules_288": impact["n_rules"] == 288,
    }
    warnings = []
    if not gates["dataset_sha256_match"]:
        warnings.append(f"dataset SHA mismatch: {data_sha}")
    mechanical_gate = "PASS" if all(gates.values()) else "FAIL"
    return {
        "cfg_a": cfg_a,
        "cfg_b": cfg_b,
        "data_path": str(data_path.relative_to(REPO)).replace("\\", "/"),
        "data_sha256": data_sha,
        "spec_path": str(spec_path.relative_to(REPO)).replace("\\", "/"),
        "spec_sha256": spec_sha,
        "meta": meta,
        "top_rows": top_rows,
        "impact": impact,
        "historical_l6": historical_l6,
        "gates": gates,
        "warnings": warnings,
        "mechanical_gate": mechanical_gate,
    }


def write_run_tree(run_dir: Path, run_id: str, computed: dict) -> dict[str, str]:
    cfg_a = computed["cfg_a"]
    cfg_b = computed["cfg_b"]
    impact = computed["impact"]
    payload = result_payload(run_id, computed, cfg_a, cfg_b)
    report = render_report(payload, impact, cfg_a)

    write_csv(run_dir / "outputs" / "SIGNAL_IMPACT.csv", impact["signal_rows"], SIGNAL_FIELDS)
    write_csv(run_dir / "outputs" / "RULE_IMPACT.csv", impact["rule_rows"], RULE_FIELDS)
    write_csv(run_dir / "outputs" / "FROZEN_TOP10_IMPACT.csv", impact["top10_rows"], TOP10_FIELDS)
    write_text(
        run_dir / "result" / "RESULT.json",
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False) + "\n",
    )
    write_text(run_dir / "report" / "EXT_C02_E02_IMPACT.md", report if report.endswith("\n") else report + "\n")
    return {rel: sha256_file(run_dir / rel) for rel in HASH_CONTRACT_FILES}


def write_manifest(
    run_dir: Path,
    run_id: str,
    command: str,
    computed: dict,
    output_hashes: dict[str, str],
    started_at: str,
    ended_at: str,
    code_commit: str,
) -> None:
    meta = computed["meta"]
    manifest = {
        "RUN_ID": run_id,
        "EXPERIMENT_ID": EXPERIMENT_ID,
        "STARTED_AT": started_at,
        "ENDED_AT": ended_at,
        "SPEC_HASH": computed["spec_sha256"],
        "CODE_COMMIT": code_commit,
        "COMMAND": command,
        "ENVIRONMENT": environment(),
        "RANDOM_SEED": None,
        "RAW_DATA_ID": computed["data_path"],
        "RAW_DATA_HASH": computed["data_sha256"],
        "PROCESSED_DATA_ID": None,
        "PROCESSED_DATA_HASH": None,
        "INPUT_ROWS": int(meta["n_bars"]),
        "GAPS": int(meta["n_missing_hours"]),
        "DUPLICATES": int(meta["n_dup_dropped"]),
        "OUTPUT_FILES": [{"path": rel, "sha256": digest} for rel, digest in output_hashes.items()],
        "TESTS": (
            "python3 -m unittest tests.test_e02_exact_timestamp tests.test_temporal_invariants "
            "tests.test_data_audit_nonfinite tests.test_r0c_synthetic_repro tests.test_r0c_legacy_ids "
            "tests.test_r0c_code_commit_contains_harness tests.test_r0c_commit_a_repro "
            "tests.test_ext_c02_isolation tests.test_ext_c02_reproducibility -v"
        ),
        "WARNINGS": computed["warnings"],
        "MECHANICAL_GATE": computed["mechanical_gate"],
        "TASK_ID": TASK_ID,
        "HYPOTHESIS_ID": HYPOTHESIS_ID,
        "ERROR_ID": ERROR_ID,
        "hash_contract_files": list(HASH_CONTRACT_FILES),
        "hash_contract_note": (
            "Byte-identical contract covers SIGNAL_IMPACT.csv, RULE_IMPACT.csv, "
            "FROZEN_TOP10_IMPACT.csv, RESULT.json, EXT_C02_E02_IMPACT.md. "
            "STARTED_AT/ENDED_AT, CODE_COMMIT, and ENVIRONMENT may differ across machines."
        ),
        "not_a_trading_edge": True,
        "does_not_authorize_capital": True,
        "materiality": computed["impact"]["materiality"],
        "mechanical_gate_is_separate_from_scientific_decision": True,
    }
    write_text(
        run_dir / "MANIFEST.json",
        json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
    )


def write_receipt(
    run_dir: Path,
    run_id: str,
    command: str,
    computed: dict,
    output_hashes: dict[str, str],
    code_commit: str,
) -> None:
    lines = [
        "# Run receipt — EXP-BTC-006 / EXT-C02",
        "",
        f"RUN_ID: {run_id}",
        "",
        "DELTA / OBJETIVO VERIFICABLE: Isolated A vs B lookback-mode contrast for E-02. Not a strategy selection.",
        "",
        "FILES CHANGED: this run folder only (spec/src live under EXP-BTC-006/).",
        "",
        f"COMMAND: `{command}`",
        "",
        f"CODE_COMMIT: `{code_commit}`",
        "",
        "TEST RESULT: see registries/runs.jsonl and EXT-C02 receipt after the unittest suite.",
        "",
        f"INPUT HASHES: {computed['data_path']} SHA-256 {computed['data_sha256']}",
        f"SPEC_HASH: {computed['spec_sha256']}",
        "",
        "OUTPUT HASHES:",
    ]
    for rel, digest in output_hashes.items():
        lines.append(f"- `{rel}` SHA-256 `{digest}`")
    lines.extend(
        [
            "",
            f"PRIMARY METRICS: materiality={computed['impact']['materiality']} "
            f"(separate from mechanical_gate={computed['mechanical_gate']}).",
            "",
            "CONTROL RESULT: unconditional same-horizon open-to-open return; identical across arms.",
            "",
            "UNCERTAINTY: not a new interval estimate; inherited trade Sharpe is comparative only.",
            "",
            "N/TRIALS: 2 arms x 288 frozen rules; no reselection.",
            "",
            f"MECHANICAL GATE: {computed['mechanical_gate']}",
            "",
            "SPEC DEVIATIONS: none.",
            "",
            "BLOCKERS: EXT-H01 ChatGPT audit not done. E-02 not CLOSED.",
            "",
            "REGISTERS UPDATED: recorded separately in COMMIT_B.",
            "",
            "not_a_trading_edge: true",
            "does_not_authorize_capital: true",
            "",
        ]
    )
    write_text(run_dir / "receipt.md", "\n".join(lines))


def run_dir_for(run_id: str) -> Path:
    return EXP_DIR / run_id


def output_hashes_from_run(run_id: str) -> dict[str, str]:
    manifest_path = run_dir_for(run_id) / "MANIFEST.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"run manifest missing: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    return {item["path"]: item["sha256"] for item in manifest["OUTPUT_FILES"]}


def observe_hash_contract() -> tuple[dict, dict[str, str]]:
    computed = compute(REPO / DATASET_REL, SPEC_PATH)
    tmp = Path("/tmp") / f"exp-btc-006-observe-{utc_now_iso().replace(':', '')}"
    tmp.mkdir(parents=True, exist_ok=False)
    try:
        hashes = write_run_tree(tmp, "OBSERVE", computed)
        return computed, hashes
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def verify(run_id: str) -> int:
    started = utc_now_iso()
    computed, hashes = observe_hash_contract()
    expected = output_hashes_from_run(run_id)
    mismatches = []
    for rel in HASH_CONTRACT_FILES:
        got = hashes.get(rel)
        want = expected.get(rel)
        if got != want:
            mismatches.append({"path": rel, "expected": want, "observed": got})
    ended = utc_now_iso()
    report = {
        "STARTED_AT": started,
        "ENDED_AT": ended,
        "RUN_ID": run_id,
        "MECHANICAL_GATE": "PASS" if not mismatches and computed["mechanical_gate"] == "PASS" else "FAIL",
        "mismatches": mismatches,
        "observed": hashes,
        "expected": expected,
        "spec_sha256": computed["spec_sha256"],
        "data_sha256": computed["data_sha256"],
        "canonical_run_unmodified": True,
    }
    print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=True))
    return 0 if report["MECHANICAL_GATE"] == "PASS" else 1


def materialize(run_id: str, command: str) -> int:
    run_dir = run_dir_for(run_id)
    if run_dir.exists():
        print(f"REFUSE overwrite of existing run folder: {run_dir}", file=sys.stderr)
        return 2
    try:
        code_commit = resolve_code_commit()
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    started = utc_now_iso()
    computed = compute(REPO / DATASET_REL, SPEC_PATH)
    run_dir.mkdir(parents=True, exist_ok=False)
    hashes = write_run_tree(run_dir, run_id, computed)
    ended = utc_now_iso()
    write_manifest(run_dir, run_id, command, computed, hashes, started, ended, code_commit)
    write_receipt(run_dir, run_id, command, computed, hashes, code_commit)
    print(
        json.dumps(
            {
                "run_dir": str(run_dir),
                "run_id": run_id,
                "CODE_COMMIT": code_commit,
                "hashes": hashes,
                "MECHANICAL_GATE": computed["mechanical_gate"],
                "materiality": computed["impact"]["materiality"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if computed["mechanical_gate"] == "PASS" else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="EXP-BTC-006 EXT-C02 isolated E-02 impact (not a strategy)")
    parser.add_argument(
        "--verify",
        action="store_true",
        help="recompute in temp dir and compare contracted hashes; does not modify the canonical run",
    )
    parser.add_argument(
        "--run-id",
        help="with --verify: which run to compare against; without --verify: write a new immutable run folder",
    )
    args = parser.parse_args(argv)

    if args.verify:
        if not args.run_id:
            print("--verify requires --run-id RUN-BTC-006-...", file=sys.stderr)
            return 2
        if not args.run_id.startswith("RUN-"):
            print("run-id must start with RUN-", file=sys.stderr)
            return 2
        return verify(args.run_id)
    if not args.run_id:
        print("required: --verify --run-id RUN-...  or  --run-id RUN-...", file=sys.stderr)
        return 2
    if not args.run_id.startswith("RUN-"):
        print("run-id must start with RUN-", file=sys.stderr)
        return 2
    command = "python3 experiments/EXP-BTC-006/src/run_ext_c02.py --run-id " + args.run_id
    return materialize(args.run_id, command)


if __name__ == "__main__":
    raise SystemExit(main())
