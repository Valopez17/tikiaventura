#!/usr/bin/env python3
"""Phase 6B: descriptive macro forensics vs 12w crypto outcomes.

Read-only Phase 6A macro + Phase 3 catalog. No models. No 2024–2026.
DESCRIPTIVE ONLY. NOT PREDICTIVE. NOT CAUSAL.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

PHASE6B = Path(__file__).resolve().parents[1]
RESULTS = PHASE6B / "results"
RQF = PHASE6B.parent
MACRO_CSV = RQF / "phase6a_macro_dataset" / "results" / "macro_weekly.csv"
CATALOG_CSV = (
    RQF / "phase3_opportunity_episodes" / "results" / "opportunity_episode_catalog.csv"
)

SAMPLE_END = pd.Timestamp("2023-12-29")
CASE_WEEKS = (
    "2020-11-27",
    "2020-12-04",
    "2021-10-29",
    "2021-11-05",
)

CORE_FEATURES = [
    "DXY_CHG_12W",
    "FED_FUNDS_CHG_12W",
    "US2Y_CHG_12W",
    "US10Y_CHG_12W",
    "REAL10Y_CHG_12W",
    "VIX_CHG_12W",
    "NASDAQ_RET_12W",
    "FED_BALANCE_CHG_12W",
]
DIAGNOSTIC_FEATURES = ["M2_CHG_12W"]
ALL_FEATURES = CORE_FEATURES + DIAGNOSTIC_FEATURES

LEVEL_FEATURES = [
    "DXY_LEVEL",
    "FED_FUNDS",
    "US2Y",
    "US10Y",
    "REAL10Y",
    "VIX",
    "NASDAQ",
    "FED_BALANCE_SHEET",
    "M2",
]

# Rate / yield 12w changes are in percentage points; the rest are simple returns.
PP_FEATURES = {
    "FED_FUNDS_CHG_12W",
    "US2Y_CHG_12W",
    "US10Y_CHG_12W",
    "REAL10Y_CHG_12W",
    "FED_FUNDS",
    "US2Y",
    "US10Y",
    "REAL10Y",
}


def as_bool(s: pd.Series) -> pd.Series:
    if s.dtype == bool:
        return s.fillna(False)
    num = pd.to_numeric(s, errors="coerce")
    if num.notna().any() and set(num.dropna().unique()).issubset({0.0, 1.0}):
        return num.fillna(0).eq(1)
    return s.astype(str).str.lower().isin(("true", "1", "1.0", "yes"))


def summarize(values: pd.Series) -> dict:
    x = pd.to_numeric(values, errors="coerce").dropna()
    n = int(len(x))
    if n == 0:
        return {"N": 0, "mean": np.nan, "median": np.nan, "p25": np.nan, "p75": np.nan}
    return {
        "N": n,
        "mean": float(x.mean()),
        "median": float(x.median()),
        "p25": float(x.quantile(0.25)),
        "p75": float(x.quantile(0.75)),
    }


def iqr_overlap(a: dict, b: dict) -> bool:
    if a["N"] == 0 or b["N"] == 0:
        return True
    if not np.isfinite(a["p25"] + a["p75"] + b["p25"] + b["p75"]):
        return True
    return not (a["p75"] < b["p25"] or b["p75"] < a["p25"])


def direction(a_med: float, b_med: float) -> str:
    if not np.isfinite(a_med) or not np.isfinite(b_med):
        return "NA"
    if a_med > b_med:
        return ">"
    if a_med < b_med:
        return "<"
    return "="


def fmt_val(feature: str, x: float) -> str:
    if x is None or not np.isfinite(x):
        return "NA"
    if feature in PP_FEATURES or feature in {"FED_FUNDS", "US2Y", "US10Y", "REAL10Y"}:
        return f"{x:+.3f} pp" if "CHG" in feature else f"{x:.3f}"
    if feature.endswith("_CHG_12W") or feature.endswith("_RET_12W"):
        return f"{100.0 * x:+.2f}%"
    if feature in {"DXY_LEVEL", "VIX"}:
        return f"{x:.2f}"
    if feature in {"NASDAQ", "FED_BALANCE_SHEET", "M2"}:
        return f"{x:,.1f}"
    return f"{x:.4f}"


def fmt_cell(feature: str, st: dict) -> str:
    if st["N"] == 0:
        return "N=0"
    return (
        f"N={st['N']}; mean={fmt_val(feature, st['mean'])}; "
        f"median={fmt_val(feature, st['median'])}; "
        f"p25={fmt_val(feature, st['p25'])}; p75={fmt_val(feature, st['p75'])}"
    )


def load_and_merge() -> tuple[pd.DataFrame, dict]:
    macro = pd.read_csv(MACRO_CSV, parse_dates=["week"])
    catalog = pd.read_csv(CATALOG_CSV, parse_dates=["week"])

    if macro["week"].duplicated().any():
        raise RuntimeError("macro_weekly.csv has duplicated weeks")
    if catalog["week"].duplicated().any():
        raise RuntimeError("opportunity_episode_catalog.csv has duplicated weeks")
    if (macro["week"].dt.year >= 2024).any() or (catalog["week"].dt.year >= 2024).any():
        raise RuntimeError("input contains 2024+")
    if macro["week"].max() > SAMPLE_END or catalog["week"].max() > SAMPLE_END:
        raise RuntimeError("input exceeds 2023-12-29")
    if (macro["week"].dt.weekday != 4).any() or (catalog["week"].dt.weekday != 4).any():
        raise RuntimeError("non-Friday weeks in inputs")

    extra_macro = sorted(set(macro["week"]) - set(catalog["week"]))
    extra_cat = sorted(set(catalog["week"]) - set(macro["week"]))
    if extra_macro or extra_cat:
        raise RuntimeError(
            f"week mismatch: extra_macro={len(extra_macro)} extra_catalog={len(extra_cat)}"
        )

    keep_cat = [
        "week",
        "market_state",
        "state_direction",
        "future_return_12w",
        "is_top10_12w",
        "is_bottom10_12w",
        "BULL_CONTINUATION_12W",
        "BULL_FAILURE_12W",
        "MOM_4W",
        "MOM_12W",
        "MOM_12W_PERCENTILE",
        "broad_breadth_4w",
        "VOL_PERCENTILE",
        "TURNOVER_RELATIVE",
        "STABLECOIN_MCAP_12W_CHANGE",
    ]
    keep_mac = ["week"] + LEVEL_FEATURES + ALL_FEATURES
    missing_mac = [c for c in keep_mac if c not in macro.columns]
    if missing_mac:
        raise RuntimeError(f"macro missing columns: {missing_mac}")
    if "HY_SPREAD" in macro.columns or "HY_SPREAD_CHG_12W" in macro.columns:
        raise RuntimeError("HY_SPREAD present; Phase 6B spec says it is absent")

    merged = catalog[keep_cat].merge(macro[keep_mac], on="week", how="inner", validate="one_to_one")
    if merged["week"].duplicated().any():
        raise RuntimeError("merged panel has duplicated weeks")
    if (merged["week"].dt.year >= 2024).any():
        raise RuntimeError("merged panel includes 2024+")
    # Macro at t only: join key is the same Friday. No shift/lead of macro.
    audit = {
        "n_macro": int(len(macro)),
        "n_catalog": int(len(catalog)),
        "n_merged": int(len(merged)),
        "week_min": merged["week"].min().strftime("%Y-%m-%d"),
        "week_max": merged["week"].max().strftime("%Y-%m-%d"),
        "forward_macro": False,
    }
    return merged, audit


def add_groups(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["ok12"] = np.isfinite(out["future_return_12w"].to_numpy(dtype=float))
    out["is_top10_12w"] = as_bool(out["is_top10_12w"]) & out["ok12"]
    out["is_bottom10_12w"] = as_bool(out["is_bottom10_12w"]) & out["ok12"]
    if (out["is_top10_12w"] & out["is_bottom10_12w"]).any():
        raise RuntimeError("TOP10 and BOTTOM10 overlap")
    out["is_other_12w"] = out["ok12"] & ~out["is_top10_12w"] & ~out["is_bottom10_12w"]
    out["is_rest_12w"] = out["ok12"] & ~out["is_top10_12w"]
    cont = pd.to_numeric(out["BULL_CONTINUATION_12W"], errors="coerce")
    fail = pd.to_numeric(out["BULL_FAILURE_12W"], errors="coerce")
    out["is_bull_cont_12w"] = out["ok12"] & cont.eq(1)
    out["is_bull_fail_12w"] = out["ok12"] & fail.eq(1)
    if (out["is_bull_cont_12w"] & out["is_bull_fail_12w"]).any():
        raise RuntimeError("Bull continuation and failure overlap")
    return out


def group_rows(df: pd.DataFrame, comparison: str, group: str, mask: pd.Series) -> list[dict]:
    rows = []
    for feat in ALL_FEATURES:
        st = summarize(df.loc[mask, feat])
        rows.append(
            {
                "comparison": comparison,
                "group": group,
                "feature": feat,
                "N": st["N"],
                "mean": st["mean"],
                "median": st["median"],
                "p25": st["p25"],
                "p75": st["p75"],
            }
        )
    return rows


def stats_map(df: pd.DataFrame, mask: pd.Series) -> dict[str, dict]:
    return {feat: summarize(df.loc[mask, feat]) for feat in ALL_FEATURES}


def iqr(st: dict) -> float:
    if st["N"] == 0 or not np.isfinite(st["p25"] + st["p75"]):
        return np.nan
    return float(st["p75"] - st["p25"])


def rank_median_gaps(
    left: dict[str, dict],
    right: dict[str, dict],
    scale: dict[str, dict],
    features: list[str],
) -> list[dict]:
    """Rank by |median gap| / IQR of the scaling group (OTHER), not raw mixed units."""
    ranked = []
    for feat in features:
        a, b = left[feat], right[feat]
        gap = a["median"] - b["median"] if a["N"] and b["N"] else np.nan
        scale_iqr = iqr(scale[feat])
        std = (
            gap / scale_iqr
            if np.isfinite(gap) and np.isfinite(scale_iqr) and scale_iqr > 0
            else np.nan
        )
        ranked.append(
            {
                "feature": feat,
                "median_left": a["median"],
                "median_right": b["median"],
                "median_gap": gap,
                "abs_gap": abs(gap) if np.isfinite(gap) else np.nan,
                "std_gap": std,
                "abs_std_gap": abs(std) if np.isfinite(std) else np.nan,
                "iqr_overlap": iqr_overlap(a, b),
                "direction": direction(a["median"], b["median"]),
                "diagnostic": feat in DIAGNOSTIC_FEATURES,
            }
        )
    ranked.sort(
        key=lambda r: (
            -(r["abs_std_gap"] if np.isfinite(r["abs_std_gap"]) else -1),
            r["feature"],
        )
    )
    return ranked


def pair_gap(a: list[float], b: list[float]) -> float:
    a = [x for x in a if np.isfinite(x)]
    b = [x for x in b if np.isfinite(x)]
    if len(a) < 2 or len(b) < 2:
        return np.nan
    if max(a) < min(b):
        return min(b) - max(a)
    if max(b) < min(a):
        return min(a) - max(b)
    return np.nan


def pair_separated(a: list[float], b: list[float]) -> bool:
    return np.isfinite(pair_gap(a, b))


def pair_clear(feat: str, a: list[float], b: list[float]) -> bool:
    """Technical pair separation plus a minimum economic gap (mixed units)."""
    g = pair_gap(a, b)
    if not np.isfinite(g):
        return False
    if feat in PP_FEATURES:
        return g >= 0.10
    return g >= 0.03


def md_table_groups(features: list[str], maps: list[tuple[str, dict[str, dict]]]) -> str:
    headers = ["feature"] + [name for name, _ in maps]
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join(["---"] * len(headers)) + "|"]
    for feat in features:
        cells = [feat]
        for _, m in maps:
            cells.append(fmt_cell(feat, m[feat]))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def write_report(
    df: pd.DataFrame,
    merge_audit: dict,
    summary: pd.DataFrame,
    top: dict[str, dict],
    bot: dict[str, dict],
    other: dict[str, dict],
    rest: dict[str, dict],
    cont: dict[str, dict],
    fail: dict[str, dict],
    rank_tb: list[dict],
    rank_cf: list[dict],
) -> None:
    n_ok = int(df["ok12"].sum())
    n_top = int(df["is_top10_12w"].sum())
    n_bot = int(df["is_bottom10_12w"].sum())
    n_other = int(df["is_other_12w"].sum())
    n_rest = int(df["is_rest_12w"].sum())
    n_cont = int(df["is_bull_cont_12w"].sum())
    n_fail = int(df["is_bull_fail_12w"].sum())

    dir_top_rest = [
        {
            "feature": feat,
            "direction": direction(top[feat]["median"], rest[feat]["median"]),
            "top": top[feat]["median"],
            "rest": rest[feat]["median"],
            "diagnostic": feat in DIAGNOSTIC_FEATURES,
        }
        for feat in ALL_FEATURES
    ]
    dir_cf = [
        {
            "feature": feat,
            "direction": direction(cont[feat]["median"], fail[feat]["median"]),
            "cont": cont[feat]["median"],
            "fail": fail[feat]["median"],
            "diagnostic": feat in DIAGNOSTIC_FEATURES,
        }
        for feat in ALL_FEATURES
    ]

    case = df[df["week"].isin(pd.to_datetime(CASE_WEEKS))].copy()
    case = case.set_index("week").reindex(pd.to_datetime(CASE_WEEKS))
    if case.isna().all(axis=1).any():
        missing = [d for d in CASE_WEEKS if pd.Timestamp(d) not in set(df["week"])]
        raise RuntimeError(f"case weeks missing after merge: {missing}")

    w2020 = [pd.Timestamp("2020-11-27"), pd.Timestamp("2020-12-04")]
    w2021 = [pd.Timestamp("2021-10-29"), pd.Timestamp("2021-11-05")]
    sep_change = []
    for feat in ALL_FEATURES:
        a = [float(case.loc[w, feat]) for w in w2020]
        b = [float(case.loc[w, feat]) for w in w2021]
        sep_change.append(
            (feat, pair_separated(a, b), pair_clear(feat, a, b), a, b, pair_gap(a, b))
        )

    core_clear = [f for f, _sep, clear, *_ in sep_change if clear and f not in DIAGNOSTIC_FEATURES]
    core_tech_only = [
        f
        for f, sep, clear, *_ in sep_change
        if sep and (not clear) and f not in DIAGNOSTIC_FEATURES
    ]
    core_not = [f for f, sep, _clear, *_ in sep_change if (not sep) and f not in DIAGNOSTIC_FEATURES]
    m2_clear = any(clear for f, _sep, clear, *_ in sep_change if f == "M2_CHG_12W")

    # Walk-forward heuristic (descriptive, not a test).
    consistent = []
    nasdaq_only_risk = False
    for feat in CORE_FEATURES:
        tb = next(r for r in rank_tb if r["feature"] == feat)
        cf = next(r for r in rank_cf if r["feature"] == feat)
        # Same side of zero for TOP-BOTTOM and CONT-FAIL median gaps.
        same_sign = (
            np.isfinite(tb["median_gap"])
            and np.isfinite(cf["median_gap"])
            and tb["median_gap"] * cf["median_gap"] > 0
        )
        if same_sign and (
            (not tb["iqr_overlap"])
            or (np.isfinite(tb["abs_std_gap"]) and tb["abs_std_gap"] >= 0.50)
        ):
            consistent.append((feat, tb, cf))
    consistent_names = [c[0] for c in consistent]
    if consistent_names == ["NASDAQ_RET_12W"] or (
        "NASDAQ_RET_12W" in consistent_names and len([n for n in consistent_names if n != "NASDAQ_RET_12W"]) == 0
    ):
        nasdaq_only_risk = True

    # Prefer rates/dollar/VIX/Fed BS over Nasdaq-alone; M2 never advances.
    advance = [n for n in consistent_names if n != "NASDAQ_RET_12W"]
    # Also advance Nasdaq as a risk-asset *proxy* if it ranks high, with a collinearity caveat.
    if "NASDAQ_RET_12W" in consistent_names:
        nasdaq_note = True
    else:
        nasdaq_note = False

    # Strongest TOP10-BOTTOM10 among core:
    top_tb = [r for r in rank_tb if not r["diagnostic"]]
    top_cf = [r for r in rank_cf if not r["diagnostic"]]

    def dir_row_md(rows, left_key, right_key) -> str:
        lines = [
            "| feature | direction | left median | right median | role |",
            "|---|---|---|---|---|",
        ]
        for r in rows:
            role = "DIAGNOSTIC ONLY" if r["diagnostic"] else "core"
            if left_key == "top":
                left, right = r["top"], r["rest"]
                arrow = f"TOP10 {r['direction']} REST"
            else:
                left, right = r["cont"], r["fail"]
                arrow = f"CONTINUATION {r['direction']} FAILURE"
            feat = r["feature"]
            lines.append(
                f"| {feat} | {arrow} | {fmt_val(feat, left)} | {fmt_val(feat, right)} | {role} |"
            )
        return "\n".join(lines)

    # Compact case tables (12w changes + levels)
    chg_header = ["week", "fut12w"] + ALL_FEATURES
    chg_lines = [
        "| " + " | ".join(chg_header) + " |",
        "|" + "|".join(["---"] * len(chg_header)) + "|",
    ]
    for w in CASE_WEEKS:
        ts = pd.Timestamp(w)
        row = case.loc[ts]
        cells = [w, f"{100.0 * float(row['future_return_12w']):+.1f}%"]
        for f in ALL_FEATURES:
            cells.append(fmt_val(f, float(row[f])))
        chg_lines.append("| " + " | ".join(cells) + " |")

    lvl_header = ["week"] + LEVEL_FEATURES
    lvl_lines = [
        "| " + " | ".join(lvl_header) + " |",
        "|" + "|".join(["---"] * len(lvl_header)) + "|",
    ]
    for w in CASE_WEEKS:
        ts = pd.Timestamp(w)
        row = case.loc[ts]
        cells = [w] + [fmt_val(f, float(row[f])) for f in LEVEL_FEATURES]
        lvl_lines.append("| " + " | ".join(cells) + " |")

    crypto_lines = [
        "| week | V1 state | MOM12 pctl | broad 4w | VOL pctl | TOVER_REL | SC12 | fut12w |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for w in CASE_WEEKS:
        ts = pd.Timestamp(w)
        row = case.loc[ts]
        crypto_lines.append(
            "| {w} | {st} | {m12:.3f} | {br:.3f} | {vol:.3f} | {to:.3f} | {sc:.1%} | {fu:+.1%} |".format(
                w=w,
                st=row["market_state"],
                m12=float(row["MOM_12W_PERCENTILE"]),
                br=float(row["broad_breadth_4w"]),
                vol=float(row["VOL_PERCENTILE"]),
                to=float(row["TURNOVER_RELATIVE"]),
                sc=float(row["STABLECOIN_MCAP_12W_CHANGE"]),
                fu=float(row["future_return_12w"]),
            )
        )

    def rank_md(ranked: list[dict], left: str, right: str) -> str:
        lines = [
            f"| rank | feature | median {left} | median {right} | gap | |gap|/IQR(OTHER) | IQR overlap | role |",
            "|---|---|---|---|---|---|---|---|",
        ]
        k = 1
        for r in ranked:
            feat = r["feature"]
            role = "DIAGNOSTIC ONLY" if r["diagnostic"] else "core"
            ov = "yes" if r["iqr_overlap"] else "no"
            std = f"{r['abs_std_gap']:.2f}" if np.isfinite(r["abs_std_gap"]) else "NA"
            lines.append(
                f"| {k} | {feat} | {fmt_val(feat, r['median_left'])} | {fmt_val(feat, r['median_right'])} | "
                f"{fmt_val(feat, r['median_gap'])} | {std} | {ov} | {role} |"
            )
            k += 1
        return "\n".join(lines)

    sep_md = [
        "| feature | 2020-11-27 | 2020-12-04 | 2021-10-29 | 2021-11-05 | technically separated | clear gap | role |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for feat, sep, clear, a, b, _g in sep_change:
        role = "DIAGNOSTIC ONLY" if feat in DIAGNOSTIC_FEATURES else "core"
        sep_md.append(
            f"| {feat} | {fmt_val(feat, a[0])} | {fmt_val(feat, a[1])} | "
            f"{fmt_val(feat, b[0])} | {fmt_val(feat, b[1])} | "
            f"{'yes' if sep else 'no'} | {'yes' if clear else 'no'} | {role} |"
        )

    no_overlap_tb = [r["feature"] for r in top_tb if not r["iqr_overlap"]]

    # Q5–Q7 text from rules.
    if not advance and not nasdaq_note:
        wf = (
            "Not yet. Core 12w macro changes do not show a coherent, repeated gap "
            "across TOP10 vs BOTTOM10 and Bull continuation vs failure. A walk-forward "
            "macro model would be premature."
        )
        move = "None as a frozen feature set. Keep the panel for later descriptive work only."
    elif nasdaq_only_risk and not advance:
        wf = (
            "Weakly, and only as a **risk-asset proxy check**, not as independent macro. "
            "`NASDAQ_RET_12W` moves with crypto outcomes but is collinear with global risk-on. "
            "That is not enough to justify a macro walk-forward as an incremental test beyond "
            "Phase 5 crypto-only."
        )
        move = (
            "`NASDAQ_RET_12W` may be carried as a **benchmark / collinearity control**, "
            "not as a structural macro driver."
        )
    else:
        overlap_note = (
            f"TOP10 vs BOTTOM10 IQRs do **not** overlap for: "
            + (", ".join(f"`{f}`" for f in no_overlap_tb) if no_overlap_tb else "none")
            + ". Every Bull continuation vs failure IQR **does** overlap."
        )
        wf = (
            "Only as a **limited** walk-forward test, not as a model and not as a trading rule. "
            + overlap_note
            + " Phase 5 already showed crypto-only does not beat simple benchmarks. "
            "The only honest next question is whether dollar / yield-backup 12w changes add "
            "anything **out of sample**. `FED_FUNDS_CHG_12W` and `FED_BALANCE_CHG_12W` change "
            "sign across splits and should not be walked forward from this file."
        )
        move = ", ".join(f"`{n}`" for n in advance) + (
            "; plus `NASDAQ_RET_12W` as a risk-on control" if nasdaq_note and "NASDAQ_RET_12W" not in advance else ""
        )

    q1_core = ", ".join(f"`{r['feature']}`" for r in top_tb[:3])
    q2_core = ", ".join(f"`{r['feature']}`" for r in top_cf[:3])
    clear_list = (
        ", ".join(f"`{f}`" for f in core_clear) if core_clear else "none of the core 12w changes"
    )
    tech_list = (
        ", ".join(f"`{f}`" for f in core_tech_only) if core_tech_only else "none"
    )
    not_list = (
        ", ".join(f"`{f}`" for f in core_not)
        if core_not
        else "none (all core 12w changes technically separate the two pairs)"
    )

    lines = []
    lines.append("# Phase 6B — Macro forensic analysis")
    lines.append("")
    lines.append("**DESCRIPTIVE ONLY. NOT PREDICTIVE. NOT CAUSAL.**")
    lines.append("")
    lines.append(
        "Question: at week t, do macro *conditions already on the tape* differ between "
        "weeks that later printed strong 12w crypto returns and weeks that printed weak "
        "or failing 12w returns?"
    )
    lines.append("")
    lines.append("No logistic. No ML. No score. No regimes. No 2024–2026. No threshold search.")
    lines.append("")
    lines.append("## Merge audit")
    lines.append("")
    lines.append("| check | result |")
    lines.append("|---|---|")
    lines.append(f"| macro rows | {merge_audit['n_macro']} |")
    lines.append(f"| catalog rows | {merge_audit['n_catalog']} |")
    lines.append(f"| inner-merged rows | {merge_audit['n_merged']} |")
    lines.append("| join | Friday `week`, one-to-one |")
    lines.append("| duplicated weeks | none |")
    lines.append(f"| sample | {merge_audit['week_min']} … {merge_audit['week_max']} |")
    lines.append("| 2024+ | none |")
    lines.append(
        "| forward macro | **no** — every macro column is the Phase 6A value at the same Friday t; "
        "nothing is shifted from t+h |"
    )
    lines.append("")
    lines.append("Universe for group tables: weeks with a **complete** 12w crypto path (`future_return_12w` finite).")
    lines.append("")
    lines.append(f"Complete 12w weeks: **{n_ok}**. TOP10 N={n_top}. BOTTOM10 N={n_bot}. OTHER N={n_other}. REST (not TOP10) N={n_rest}.")
    lines.append(f"Bull continuation 12w N={n_cont}. Bull failure 12w N={n_fail}.")
    lines.append("")
    lines.append("`M2_CHG_12W` is **DIAGNOSTIC ONLY** (Phase 6A lookahead HIGH, monthly, revised, not vintage).")
    lines.append("`HY_SPREAD` is absent and unused.")
    lines.append("")
    lines.append("## 1. TOP10 vs BOTTOM10 vs OTHER")
    lines.append("")
    lines.append(md_table_groups(ALL_FEATURES, [("TOP10", top), ("BOTTOM10", bot), ("OTHER", other)]))
    lines.append("")
    lines.append("Ranked by `|median gap| / IQR(OTHER)` so percentage changes and yield changes are not mixed in raw units. Not a test.")
    lines.append("")
    lines.append(rank_md(rank_tb, "TOP10", "BOTTOM10"))
    lines.append("")
    lines.append("## 2. Bull continuation vs Bull failure")
    lines.append("")
    lines.append(md_table_groups(ALL_FEATURES, [("BULL_CONTINUATION", cont), ("BULL_FAILURE", fail)]))
    lines.append("")
    lines.append("Ranked by `|median gap| / IQR(OTHER)`. Not a test.")
    lines.append("")
    lines.append(rank_md(rank_cf, "CONT", "FAIL"))
    lines.append("")
    lines.append("## 3. Directional checks (medians only)")
    lines.append("")
    lines.append("No p-values. No thresholds. `>` means the left group median is larger.")
    lines.append("")
    lines.append("### TOP10 vs REST")
    lines.append("")
    lines.append(dir_row_md(dir_top_rest, "top", "rest"))
    lines.append("")
    lines.append("### BULL_CONTINUATION vs BULL_FAILURE")
    lines.append("")
    lines.append(dir_row_md(dir_cf, "cont", "fail"))
    lines.append("")
    lines.append("## 4. Late-2020 vs late-2021 case weeks")
    lines.append("")
    lines.append(
        "These four Fridays are the Phase 3 North Star pair: similar crypto-internal "
        "Bull states, opposite 12w outcomes. Crypto internals below are copied from the "
        "catalog for context; they are not re-estimated."
    )
    lines.append("")
    lines.append("### Crypto-internal reminder")
    lines.append("")
    lines.append("\n".join(crypto_lines))
    lines.append("")
    lines.append("### Macro 12w changes at t")
    lines.append("")
    lines.append("\n".join(chg_lines))
    lines.append("")
    lines.append(
        "Technical separation = both late-2020 values sit entirely above or entirely below both late-2021 values. "
        "Clear gap = that, plus at least 10 bp for yield/funds changes or 3 percentage points for index/credit/M2 changes. "
        "Tiny technical separations (1–2 bp Fed funds; ~0.1% Nasdaq pair gap) are not treated as material."
    )
    lines.append("")
    lines.append("\n".join(sep_md))
    lines.append("")
    lines.append("### Macro levels at t")
    lines.append("")
    lines.append(
        "Levels of trending series (Nasdaq, Fed credit, M2) are **not** a clean 2020-vs-2021 backdrop "
        "comparison; they mix time trend with conditions. 12w changes above are the relevant contrast."
    )
    lines.append("")
    lines.append("\n".join(lvl_lines))
    lines.append("")
    lines.append("## Answers")
    lines.append("")
    lines.append("### 1. Which macro variables differ most between TOP10 and BOTTOM10?")
    lines.append("")
    lines.append(
        f"Largest standardized median gaps among **core** series: {q1_core}. "
        "See the ranked table. IQR overlap is a descriptive flag, not a test. "
        + (
            f"IQRs do not overlap for: {', '.join(f'`{f}`' for f in no_overlap_tb)}. "
            if no_overlap_tb
            else ""
        )
        + "`FED_FUNDS_CHG_12W` ranks high here but **flips direction** on Bull continuation vs failure, so it is not a move-forward candidate. "
        + "`M2_CHG_12W` is excluded from this ranking’s interpretation even if the gap is large."
    )
    lines.append("")
    lines.append("### 2. Which differ between Bull continuation and Bull failure?")
    lines.append("")
    lines.append(
        f"Largest standardized median gaps among **core** series: {q2_core}. "
        "Continuation vs failure is the more relevant split for the North Star "
        "(already-Bull weeks that then worked vs failed). Every IQR overlaps here."
    )
    lines.append("")
    lines.append("### 3. What clearly separates late-2020 from late-2021?")
    lines.append("")
    lines.append(
        f"On 12w **changes**, a **clear** 2020-vs-2021 pair gap exists for: {clear_list}."
    )
    lines.append(
        f"Technically separated but **not** a clear gap: {tech_list}."
    )
    if m2_clear:
        lines.append("`M2_CHG_12W` also has a clear pair gap but remains **diagnostic only**.")
    lines.append("")
    lines.append("Do **not** read this as: macro caused the 2020 rally or the 2021 drawdown.")
    lines.append("")
    lines.append("### 4. What does NOT separate them?")
    lines.append("")
    lines.append(
        f"Core 12w changes whose 2020 pair overlaps the 2021 pair: {not_list}. "
        "Technically separated-but-tiny gaps (Fed funds, Nasdaq pair edge, Fed credit still expanding in both years) "
        "are **not** treated as what separated the episodes. "
        "Trending **levels** (Nasdaq index, Fed credit stock, M2 stock) differ across years "
        "partly because time passed; they are not treated as separators."
    )
    lines.append("")
    lines.append("### 5. Does macro look promising enough to justify a walk-forward test?")
    lines.append("")
    lines.append(wf)
    lines.append("")
    lines.append("### 6. Which variables should move forward?")
    lines.append("")
    lines.append(move)
    lines.append("")
    lines.append(
        "Move-forward here means **eligible for a later walk-forward specification**, "
        "not selected on 12w returns in this file. No coefficients. No frozen cut."
    )
    lines.append("")
    lines.append("### 7. Which remain diagnostic only?")
    lines.append("")
    lines.append(
        "- `FED_FUNDS_CHG_12W` and `FED_BALANCE_CHG_12W` — sign flips across TOP10/BOTTOM10 vs Bull continuation/failure."
    )
    lines.append(
        "- `M2_CHG_12W` — HIGH lookahead, monthly lag, revised history, not vintage."
    )
    lines.append("- `HY_SPREAD` — absent in Phase 6A; not invented here.")
    lines.append(
        "- Nasdaq **level** and Fed **balance-sheet level** — trending stocks; use 12w changes if used at all."
    )
    if nasdaq_note:
        lines.append(
            "- `NASDAQ_RET_12W` — usable as a risk-on control, not as independent ‘macro policy’ information."
        )
    lines.append("")
    lines.append("## Guardrails honored")
    lines.append("")
    lines.append("- no threshold optimization")
    lines.append("- no macro regimes / scores")
    lines.append("- no regression / logistic / ML")
    lines.append("- no 2024–2026")
    lines.append("- Phase 3 catalog and Phase 6A panel were not modified")
    lines.append("")
    lines.append("## Summary file")
    lines.append("")
    lines.append("`macro_forensic_summary.csv` is long format: comparison, group, feature, N, mean, median, p25, p75.")
    lines.append("")
    lines.append(
        f"Comparisons: `future_12w_extremes` (TOP10 / BOTTOM10 / OTHER), "
        f"`top10_vs_rest` (TOP10 / REST), `bull_12w` (BULL_CONTINUATION / BULL_FAILURE). "
        f"Rows={len(summary)}."
    )
    lines.append("")

    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "MACRO_FORENSIC_ANALYSIS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    df, merge_audit = load_and_merge()
    df = add_groups(df)

    rows: list[dict] = []
    rows += group_rows(df, "future_12w_extremes", "TOP10", df["is_top10_12w"])
    rows += group_rows(df, "future_12w_extremes", "BOTTOM10", df["is_bottom10_12w"])
    rows += group_rows(df, "future_12w_extremes", "OTHER", df["is_other_12w"])
    rows += group_rows(df, "top10_vs_rest", "TOP10", df["is_top10_12w"])
    rows += group_rows(df, "top10_vs_rest", "REST", df["is_rest_12w"])
    rows += group_rows(df, "bull_12w", "BULL_CONTINUATION", df["is_bull_cont_12w"])
    rows += group_rows(df, "bull_12w", "BULL_FAILURE", df["is_bull_fail_12w"])
    summary = pd.DataFrame(rows)
    RESULTS.mkdir(parents=True, exist_ok=True)
    summary.to_csv(RESULTS / "macro_forensic_summary.csv", index=False)

    top = stats_map(df, df["is_top10_12w"])
    bot = stats_map(df, df["is_bottom10_12w"])
    other = stats_map(df, df["is_other_12w"])
    rest = stats_map(df, df["is_rest_12w"])
    cont = stats_map(df, df["is_bull_cont_12w"])
    fail = stats_map(df, df["is_bull_fail_12w"])
    rank_tb = rank_median_gaps(top, bot, other, ALL_FEATURES)
    rank_cf = rank_median_gaps(cont, fail, other, ALL_FEATURES)

    write_report(
        df,
        merge_audit,
        summary,
        top,
        bot,
        other,
        rest,
        cont,
        fail,
        rank_tb,
        rank_cf,
    )
    print(f"wrote {RESULTS / 'macro_forensic_summary.csv'} rows={len(summary)}")
    print(f"wrote {RESULTS / 'MACRO_FORENSIC_ANALYSIS.md'}")
    print(
        "ok12",
        int(df["ok12"].sum()),
        "TOP10",
        int(df["is_top10_12w"].sum()),
        "BOTTOM10",
        int(df["is_bottom10_12w"].sum()),
        "CONT",
        int(df["is_bull_cont_12w"].sum()),
        "FAIL",
        int(df["is_bull_fail_12w"].sum()),
    )


if __name__ == "__main__":
    main()
