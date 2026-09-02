#!/usr/bin/env python3
"""Phase 6C: limited macro-only expanding walk-forward.

Four frozen features. M0 vs M_MACRO. 12w targets only.
No crypto features. No search. No 2024–2026. No combined model.
"""

from __future__ import annotations

import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    balanced_accuracy_score,
    brier_score_loss,
    log_loss,
    roc_auc_score,
)
from sklearn.preprocessing import StandardScaler

PHASE6C = Path(__file__).resolve().parents[1]
RESULTS = PHASE6C / "results"
RQF = PHASE6C.parent
MACRO_CSV = RQF / "phase6a_macro_dataset" / "results" / "macro_weekly.csv"
CATALOG_CSV = (
    RQF / "phase3_opportunity_episodes" / "results" / "opportunity_episode_catalog.csv"
)

SAMPLE_END = pd.Timestamp("2023-12-29")
VAL_START = pd.Timestamp("2021-01-01")
HORIZON = 12
MIN_TRAIN = 100
LOGIT_C = 1.0
CLIP = 1e-6
STRONG = 0.20
SEVERE = -0.20

FEATURES = [
    "DXY_CHG_12W",
    "US2Y_CHG_12W",
    "REAL10Y_CHG_12W",
    "NASDAQ_RET_12W",
]


def load_frame() -> pd.DataFrame:
    cat = pd.read_csv(CATALOG_CSV, parse_dates=["week"])
    mac = pd.read_csv(MACRO_CSV, parse_dates=["week"])
    if cat["week"].duplicated().any() or mac["week"].duplicated().any():
        raise RuntimeError("duplicated weeks in inputs")
    if (cat["week"].dt.year >= 2024).any() or (mac["week"].dt.year >= 2024).any():
        raise RuntimeError("2024+ in inputs")
    cat = cat.loc[cat["week"] <= SAMPLE_END].copy()
    mac = mac.loc[mac["week"] <= SAMPLE_END].copy()
    keep_mac = ["week"] + FEATURES
    missing = [c for c in FEATURES if c not in mac.columns]
    if missing:
        raise RuntimeError(f"macro missing {missing}")
    df = cat.merge(mac[keep_mac], on="week", how="inner", validate="one_to_one")
    df = df.sort_values("week").reset_index(drop=True)
    if (df["week"].dt.year >= 2024).any() or df["week"].max() > SAMPLE_END:
        raise RuntimeError("merged frame exceeds sample")
    r = pd.to_numeric(df["future_return_12w"], errors="coerce")
    df["y_pos"] = np.where(np.isfinite(r), (r > 0).astype(float), np.nan)
    df["y_strong"] = np.where(np.isfinite(r), (r > STRONG).astype(float), np.nan)
    df["y_severe"] = np.where(np.isfinite(r), (r < SEVERE).astype(float), np.nan)
    df["is_bull"] = df["state_direction"].astype(str) == "BULL"
    df["ok12"] = np.isfinite(r)
    return df


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
    clf = LogisticRegression(
        penalty="l2",
        C=LOGIT_C,
        solver="lbfgs",
        max_iter=2000,
        random_state=0,
    )
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=ConvergenceWarning)
        warnings.filterwarnings("ignore", category=UserWarning)
        clf.fit(Xs, y)
    classes = list(clf.classes_)
    proba = clf.predict_proba(xts)[0]
    p = float(proba[classes.index(1)]) if 1 in classes else 0.0
    return float(np.clip(p, CLIP, 1.0 - CLIP))


def walkforward(df: pd.DataFrame, y: np.ndarray, u_mask: np.ndarray) -> dict[str, np.ndarray]:
    n = len(df)
    y_ok = np.isfinite(y)
    eval_mask = u_mask & y_ok
    X = df[FEATURES].to_numpy(dtype=float)
    p0 = np.full(n, np.nan)
    p1 = np.full(n, np.nan)
    ntr = np.full(n, np.nan)
    enough = np.zeros(n, dtype=bool)
    for t in range(n):
        if not eval_mask[t]:
            continue
        end = t - HORIZON
        if end < 0:
            continue
        train = np.zeros(n, dtype=bool)
        train[: end + 1] = True
        train &= y_ok & u_mask
        nt = int(train.sum())
        ntr[t] = nt
        if nt < MIN_TRAIN:
            continue
        ytr = y[train]
        p0[t] = float(ytr.mean())
        p1[t] = logit_fit_predict(X[train], ytr, X[t])
        enough[t] = True
    return {"p0": p0, "p1": p1, "n_train": ntr, "enough": enough, "eval": eval_mask}


def score_block(y: np.ndarray, p: np.ndarray) -> dict:
    m = np.isfinite(y) & np.isfinite(p)
    y = y[m].astype(int)
    p = np.clip(p[m].astype(float), CLIP, 1.0 - CLIP)
    n = int(len(y))
    out = {
        "N": n,
        "prevalence": np.nan,
        "brier": np.nan,
        "log_loss": np.nan,
        "auc": np.nan,
        "balanced_accuracy": np.nan,
    }
    if n == 0:
        return out
    yhat = (p >= 0.5).astype(int)
    n_pos = int(y.sum())
    out["prevalence"] = float(y.mean())
    out["brier"] = float(brier_score_loss(y, p))
    out["log_loss"] = float(log_loss(y, p, labels=[0, 1]))
    if 0 < n_pos < n:
        out["auc"] = float(roc_auc_score(y, p))
        out["balanced_accuracy"] = float(balanced_accuracy_score(y, yhat))
    return out


def bss(brier: float, base: float) -> float:
    if np.isfinite(brier) and np.isfinite(base) and base > 0:
        return 1.0 - brier / base
    return np.nan


def metric_row(universe, target, model, period, stats, base_brier) -> dict:
    return {
        "universe": universe,
        "target": target,
        "model": model,
        "period": period,
        "N": stats["N"],
        "prevalence": stats["prevalence"],
        "brier": stats["brier"],
        "log_loss": stats["log_loss"],
        "auc": stats["auc"],
        "balanced_accuracy": stats["balanced_accuracy"],
        "brier_skill_vs_M0": 0.0 if model == "M0" else bss(stats["brier"], base_brier),
        "brier_m0": np.nan if model == "M0" else base_brier,
        "bss_median": np.nan,
        "bss_min": np.nan,
        "bss_max": np.nan,
        "n_offsets_bss_gt0": np.nan,
        "n_offsets": np.nan,
    }


def period_mask(weeks: pd.Series, enough: np.ndarray, period: str) -> np.ndarray:
    ok = enough.copy()
    if period == "validation_2021_2023":
        ok &= weeks >= VAL_START
    elif period == "full_wf":
        pass
    else:
        raise ValueError(period)
    return ok


def nonoverlap_bss(y: np.ndarray, p_m: np.ndarray, p0: np.ndarray, enough: np.ndarray) -> dict:
    idx = np.arange(len(y))
    skills = []
    offset_rows = []
    for off in range(HORIZON):
        sel = enough & ((idx - off) % HORIZON == 0)
        if int(sel.sum()) < 10:
            continue
        st_m = score_block(y[sel], p_m[sel])
        st_0 = score_block(y[sel], p0[sel])
        skill = bss(st_m["brier"], st_0["brier"])
        skills.append(skill)
        offset_rows.append(
            {
                "offset": off,
                "N": st_m["N"],
                "brier_macro": st_m["brier"],
                "brier_m0": st_0["brier"],
                "bss": skill,
            }
        )
    if not skills:
        return {
            "bss_median": np.nan,
            "bss_min": np.nan,
            "bss_max": np.nan,
            "n_pos": 0,
            "n_off": 0,
            "offsets": offset_rows,
        }
    arr = np.array(skills, dtype=float)
    return {
        "bss_median": float(np.median(arr)),
        "bss_min": float(np.nanmin(arr)),
        "bss_max": float(np.nanmax(arr)),
        "n_pos": int(np.nansum(arr > 0)),
        "n_off": int(len(arr)),
        "offsets": offset_rows,
    }


def fmt(x, nd=3) -> str:
    if x is None or (isinstance(x, float) and not np.isfinite(x)) or pd.isna(x):
        return "NA"
    return f"{float(x):.{nd}f}"


def lookup(metrics: pd.DataFrame, universe, target, model, period) -> dict | None:
    q = metrics[
        (metrics["universe"] == universe)
        & (metrics["target"] == target)
        & (metrics["model"] == model)
        & (metrics["period"] == period)
    ]
    if q.empty:
        return None
    return q.iloc[0].to_dict()


def beats_m0(macro: dict | None, m0: dict | None) -> bool:
    if macro is None or m0 is None:
        return False
    if int(macro["N"]) == 0 or int(m0["N"]) == 0:
        return False
    skill = macro.get("brier_skill_vs_M0")
    return bool(np.isfinite(skill) and skill > 0)


def write_report(
    df: pd.DataFrame,
    metrics: pd.DataFrame,
    jobs: list[dict],
    bull_note: str,
) -> None:
    def L(u, t, m, p):
        return lookup(metrics, u, t, m, p)

    def line(u, t, m, p) -> str:
        r = L(u, t, m, p)
        if r is None:
            return f"| {m} | — |"
        return (
            f"| {m} | {int(r['N'])} | {fmt(r['prevalence'], 3)} | {fmt(r['brier'], 4)} | "
            f"{fmt(r['brier_skill_vs_M0'], 3)} | {fmt(r['log_loss'], 4)} | "
            f"{fmt(r['auc'], 3)} | {fmt(r['balanced_accuracy'], 3)} |"
        )

    hdr = "| model | N | prevalence | brier | BSS vs M0 | logloss | AUC | bal_acc |"
    sep = "|---|---:|---:|---:|---:|---:|---:|---:|"

    def table(u, t, p):
        return "\n".join([hdr, sep, line(u, t, "M0", p), line(u, t, "M_MACRO", p)])

    pri = "pos_12w"
    full_ok = beats_m0(L("ALL_MARKET", pri, "M_MACRO", "full_wf"), L("ALL_MARKET", pri, "M0", "full_wf"))
    val_ok = beats_m0(
        L("ALL_MARKET", pri, "M_MACRO", "validation_2021_2023"),
        L("ALL_MARKET", pri, "M0", "validation_2021_2023"),
    )
    nov = L("ALL_MARKET", pri, "M_MACRO", "nonoverlap_summary")
    nov_ok = (
        nov is not None
        and np.isfinite(nov.get("bss_median", np.nan))
        and nov["bss_median"] > 0
        and int(nov.get("n_offsets_bss_gt0") or 0) >= 7
    )
    nov_any = (
        nov is not None
        and np.isfinite(nov.get("bss_median", np.nan))
        and (nov["bss_median"] > 0 or int(nov.get("n_offsets_bss_gt0") or 0) >= 1)
    )
    sec_hits = []
    for tgt in ("strong_12w", "severe_12w"):
        for p in ("full_wf", "validation_2021_2023"):
            if beats_m0(L("ALL_MARKET", tgt, "M_MACRO", p), L("ALL_MARKET", tgt, "M0", p)):
                sec_hits.append(f"{tgt}/{p}")
    bull_ok = beats_m0(L("BULL", pri, "M_MACRO", "full_wf"), L("BULL", pri, "M0", "full_wf"))

    if full_ok and val_ok and nov_ok:
        verdict = "A"
        verdict_txt = "MACRO HAS CLEAR WALK-FORWARD SIGNAL"
    elif full_ok or val_ok or nov_any or sec_hits or bull_ok:
        verdict = "B"
        verdict_txt = "MACRO HAS WEAK / CONDITIONAL SIGNAL"
    else:
        verdict = "C"
        verdict_txt = "MACRO DOES NOT BEAT BASE RATE"

    n_ok = int(df["ok12"].sum())
    n_bull = int((df["is_bull"] & df["ok12"]).sum())

    lines = []
    lines.append("# Phase 6C — Macro walk-forward analysis")
    lines.append("")
    lines.append("Question: does a **frozen four-feature macro set, alone**, improve 12w crypto probability forecasts versus an expanding base rate?")
    lines.append("")
    lines.append("No crypto features. No search. No combined model. No 2024–2026. Not a trading backtest.")
    lines.append("")
    lines.append("Mature labels: at week t, training uses only weeks `s <= t - 12`. Logistic L2 `C=1.0`. Train-only median imputation and standardization. Min train N=100.")
    lines.append("")
    lines.append("Features: `DXY_CHG_12W`, `US2Y_CHG_12W`, `REAL10Y_CHG_12W`, `NASDAQ_RET_12W`.")
    lines.append("")
    lines.append("## Sample")
    lines.append("")
    lines.append("| item | value |")
    lines.append("|---|---|")
    lines.append(f"| merged weeks | {len(df)} |")
    lines.append(f"| last week | {df['week'].max().strftime('%Y-%m-%d')} |")
    lines.append("| 2024+ | none |")
    lines.append(f"| complete 12w outcomes | {n_ok} |")
    lines.append(f"| Bull weeks with complete 12w | {n_bull} |")
    lines.append(f"| min train N | {MIN_TRAIN} |")
    lines.append("")
    lines.append("## ALL_MARKET — primary `future_return_12w > 0`")
    lines.append("")
    lines.append("### Full expanding walk-forward")
    lines.append("")
    lines.append(table("ALL_MARKET", pri, "full_wf"))
    lines.append("")
    lines.append("### 2021–2023 validation")
    lines.append("")
    lines.append(table("ALL_MARKET", pri, "validation_2021_2023"))
    lines.append("")
    lines.append("### Non-overlapping 12-week offsets (primary, full walk-forward)")
    lines.append("")
    if nov is None or int(nov.get("n_offsets") or 0) == 0:
        lines.append("Fewer than 10 evaluation weeks on every offset. Non-overlapping BSS not reported.")
    else:
        lines.append(
            f"Offsets used: {int(nov['n_offsets'])}/12. "
            f"Median BSS={fmt(nov['bss_median'], 3)}; "
            f"min={fmt(nov['bss_min'], 3)}; max={fmt(nov['bss_max'], 3)}; "
            f"offsets with BSS>0: {int(nov['n_offsets_bss_gt0'])}/{int(nov['n_offsets'])}."
        )
        lines.append("")
        lines.append("| offset | N | brier M_MACRO | brier M0 | BSS |")
        lines.append("|---:|---:|---:|---:|---:|")
        off_rows = metrics[
            (metrics["universe"] == "ALL_MARKET")
            & (metrics["target"] == pri)
            & (metrics["model"] == "M_MACRO")
            & metrics["period"].astype(str).str.startswith("nonoverlap_off")
        ].sort_values("period")
        for _, r in off_rows.iterrows():
            lines.append(
                f"| {r['period'].replace('nonoverlap_off', '')} | {int(r['N'])} | "
                f"{fmt(r['brier'], 4)} | {fmt(r['brier_m0'], 4)} | {fmt(r['brier_skill_vs_M0'], 3)} |"
            )
        lines.append("")
    lines.append("## ALL_MARKET — secondary targets")
    lines.append("")
    lines.append("### `future_return_12w > +20%`")
    lines.append("")
    lines.append("Full:")
    lines.append("")
    lines.append(table("ALL_MARKET", "strong_12w", "full_wf"))
    lines.append("")
    lines.append("2021–2023:")
    lines.append("")
    lines.append(table("ALL_MARKET", "strong_12w", "validation_2021_2023"))
    lines.append("")
    lines.append("### `future_return_12w < -20%`")
    lines.append("")
    lines.append("Full:")
    lines.append("")
    lines.append(table("ALL_MARKET", "severe_12w", "full_wf"))
    lines.append("")
    lines.append("2021–2023:")
    lines.append("")
    lines.append(table("ALL_MARKET", "severe_12w", "validation_2021_2023"))
    lines.append("")
    lines.append("## BULL-only — primary `future_return_12w > 0`")
    lines.append("")
    lines.append(bull_note)
    lines.append("")
    if L("BULL", pri, "M0", "full_wf") is not None:
        lines.append("Full:")
        lines.append("")
        lines.append(table("BULL", pri, "full_wf"))
        lines.append("")
        lines.append("2021–2023:")
        lines.append("")
        lines.append(table("BULL", pri, "validation_2021_2023"))
        lines.append("")
    lines.append("## Decision")
    lines.append("")
    lines.append(f"**{verdict} — {verdict_txt}**")
    lines.append("")
    lines.append("Rule (not softened):")
    lines.append("")
    lines.append("- A if M_MACRO beats M0 on Brier for the primary target on **both** full walk-forward and 2021–2023, **and** non-overlapping median BSS>0 with at least 7 offsets BSS>0.")
    lines.append("- B if it beats M0 on some but not all of those primary checks, or only on a secondary / Bull slice.")
    lines.append("- C if it does not beat M0 on the primary target in the expanding and validation windows.")
    lines.append("")
    lines.append(
        f"Primary full BSS>0: {full_ok}. Primary 2021–2023 BSS>0: {val_ok}. "
        f"Nonoverlap median>0 and ≥7 offsets>0: {nov_ok}. "
        f"Secondary BSS>0 slices: {sec_hits if sec_hits else 'none'}. "
        f"Bull primary BSS>0: {bull_ok}."
    )
    lines.append("")
    lines.append("Macro was not combined with crypto. Verdict B is not a license to build a large Crypto+Macro model. A later Crypto vs Macro vs Crypto+Macro test is optional and must stay restricted; this file does not support A.")
    lines.append("")
    lines.append("## Guardrails")
    lines.append("")
    lines.append("- no feature search / no extra macros")
    lines.append("- no threshold optimization")
    lines.append("- no logistic C search")
    lines.append("- no 2024–2026")
    lines.append("- min train N not lowered")
    lines.append("- Phase 3 / 6A not modified")
    lines.append("")

    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "MACRO_WALKFORWARD_ANALYSIS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return verdict


def main() -> None:
    df = load_frame()
    weeks = df["week"]
    jobs = [
        ("ALL_MARKET", "pos_12w", df["y_pos"].to_numpy(dtype=float), np.ones(len(df), dtype=bool)),
        ("ALL_MARKET", "strong_12w", df["y_strong"].to_numpy(dtype=float), np.ones(len(df), dtype=bool)),
        ("ALL_MARKET", "severe_12w", df["y_severe"].to_numpy(dtype=float), np.ones(len(df), dtype=bool)),
        ("BULL", "pos_12w", df["y_pos"].to_numpy(dtype=float), df["is_bull"].to_numpy(dtype=bool)),
    ]

    rows: list[dict] = []
    wf_store: dict[tuple[str, str], dict] = {}
    bull_note = ""

    for universe, target, y, u_mask in jobs:
        wf = walkforward(df, y, u_mask)
        wf_store[(universe, target)] = wf
        n_enough = int(wf["enough"].sum())
        if universe == "BULL":
            if n_enough == 0:
                bull_note = (
                    f"Insufficient sample: no Bull evaluation week reached min train N={MIN_TRAIN} "
                    f"with a mature 12w label. Mature Bull 12w weeks in the panel: "
                    f"{int((u_mask & np.isfinite(y)).sum())}. Minimum N was **not** lowered."
                )
                continue
            bull_note = (
                f"Bull walk-forward ran with min train N={MIN_TRAIN} (not lowered). "
                f"Evaluation weeks with enough history: {n_enough}."
            )
        for period in ("full_wf", "validation_2021_2023"):
            sel = period_mask(weeks, wf["enough"], period)
            st0 = score_block(y[sel], wf["p0"][sel])
            stm = score_block(y[sel], wf["p1"][sel])
            rows.append(metric_row(universe, target, "M0", period, st0, st0["brier"]))
            rows.append(metric_row(universe, target, "M_MACRO", period, stm, st0["brier"]))

        if universe == "ALL_MARKET":
            nov = nonoverlap_bss(y, wf["p1"], wf["p0"], wf["enough"])
            for off in nov["offsets"]:
                rows.append(
                    {
                        "universe": universe,
                        "target": target,
                        "model": "M_MACRO",
                        "period": f"nonoverlap_off{off['offset']:02d}",
                        "N": off["N"],
                        "prevalence": np.nan,
                        "brier": off["brier_macro"],
                        "log_loss": np.nan,
                        "auc": np.nan,
                        "balanced_accuracy": np.nan,
                        "brier_skill_vs_M0": off["bss"],
                        "brier_m0": off["brier_m0"],
                        "bss_median": np.nan,
                        "bss_min": np.nan,
                        "bss_max": np.nan,
                        "n_offsets_bss_gt0": np.nan,
                        "n_offsets": np.nan,
                    }
                )
            rows.append(
                {
                    "universe": universe,
                    "target": target,
                    "model": "M_MACRO",
                    "period": "nonoverlap_summary",
                    "N": nov["n_off"],
                    "prevalence": np.nan,
                    "brier": np.nan,
                    "log_loss": np.nan,
                    "auc": np.nan,
                    "balanced_accuracy": np.nan,
                    "brier_skill_vs_M0": nov["bss_median"],
                    "brier_m0": np.nan,
                    "bss_median": nov["bss_median"],
                    "bss_min": nov["bss_min"],
                    "bss_max": nov["bss_max"],
                    "n_offsets_bss_gt0": nov["n_pos"],
                    "n_offsets": nov["n_off"],
                }
            )

    if not bull_note:
        bull_note = "Bull slice was not evaluated."

    metrics = pd.DataFrame(rows)
    RESULTS.mkdir(parents=True, exist_ok=True)
    metrics.to_csv(RESULTS / "macro_walkforward_metrics.csv", index=False)
    verdict = write_report(df, metrics, jobs, bull_note)
    print(f"wrote {RESULTS / 'macro_walkforward_metrics.csv'} rows={len(metrics)}")
    print(f"wrote {RESULTS / 'MACRO_WALKFORWARD_ANALYSIS.md'}")
    print("verdict", verdict)


if __name__ == "__main__":
    main()
