# Consolidated findings — crypto + macro diagnostic branch

Documentation only. No new models. No new metrics. Sample through
**2023-12-29**. **2024–2026 was not opened.**

2021–2023 was inspected in multiple earlier phases (descriptive and
model-comparison work). It is **TEMPORAL ROBUSTNESS / PSEUDO-OOS**, not
clean out-of-sample validation.

Sources: Phase 5, 6B, 6C, 6D (horizon), 6E, 6F. Prior files were not
rewritten.

---

## 1. CRYPTO-ONLY

Crypto-only predictive models did **not** beat simple expanding base-rate
benchmarks robustly (Phase 5 verdict **C**).

The reduced crypto block used later
(`MOM_12W_PERCENTILE`, `MOM4_CHANGE_4W`, `MOM12_CHANGE_4W`,
`BROAD_BREADTH_CHANGE_4W`, `TURNOVER_RELATIVE`, `VOL_PERCENTILE`)
also failed versus M0 at **4w, 8w, and 12w** (Phase 6D horizon: **NO EDGE**
at every horizon; full-sample and 2021–2023 BSS both ≤ 0). Non-overlapping
offsets: **0** offsets with BSS > 0 at 4w, 8w, and 12w.

Crypto internals remain useful for **descriptive** market-state diagnosis
(Phase 3–4 Observatory context: levels, dynamics, episodes). That is not
a probability forecast.

**Do not call crypto-only predictive.** Do not freeze a crypto Model A.

A side test that concatenated this crypto block with the frozen macro
set (Phase 6D incremental) did not beat macro-only. Combined is not a
candidate.

---

## 2. MACRO-ONLY

Frozen features (Phase 6B eligibility → 6C/6D/6E walk-forward):

- `DXY_CHG_12W`
- `US2Y_CHG_12W`
- `REAL10Y_CHG_12W`
- `NASDAQ_RET_12W`

Phase 6B was descriptive only (TOP10 vs BOTTOM10 IQR gaps on dollar and
2Y; Bull continuation vs failure IQRs all overlap). It did not validate
forecasts.

Walk-forward (logistic L2, C=1.0, mature labels, min train N=100):

- **Full-history expanding walk-forward does not beat M0 robustly.**
  Primary 12w sign: BSS **−0.077** (Phase 6C). Same pattern at 4w
  (**−0.027**) and 8w (**−0.051**) in Phase 6D.
- **2021–2023 shows materially better performance** (12w BSS **+0.170**;
  8w **+0.132**; 4w **+0.112**). That window is
  **TEMPORAL ROBUSTNESS / PSEUDO-OOS**, not clean OOS. It was already
  inspected in forensics and later comparisons.
- **Non-overlap mostly fails.** Macro median BSS < 0 at 4w, 8w, and 12w;
  **1** offset BSS > 0 at each horizon (Phase 6D). Phase 6C 12w:
  median BSS **−0.092**, **1/12** offsets BSS > 0.

Phase 6C verdict: **B — MACRO HAS WEAK / CONDITIONAL SIGNAL.**

Therefore the signal is **WEAK / CONDITIONAL / TEMPORALLY UNSTABLE**.

**Do not say macro robustly predicts crypto.**

---

## 3. HORIZON / LAG

The 4w / 8w / 12w diagnostic (Phase 6D, lag 0) did **not** reveal a
robust optimal horizon. Crypto is NO EDGE at all three. Macro is WEAK
at all three. Full-sample BSS gets worse as H lengthens; 2021–2023
macro BSS gets better as H lengthens. That disagreement is a **period
effect**, not a reason to pick 12w. No horizon is “best.”

Delayed crypto outcome windows L=4 and L=8 (Phase 6E) did **not**
improve over L=0. Full-sample BSS is worse at every delayed cell.
2021–2023 BSS is weaker at L=4 than L=0, and L=8 H=8 / H=12 is
**NO EDGE**. Lag 0 was consistently less bad / stronger than delayed
versions.

**Reject a fixed 4w or 8w macro-lead hypothesis for now.**

---

## 4. REGIME / TRANSITION

Phase 6F scored the **existing** L=0 macro forecast by catalog
`state_direction` (not new Bull/Bear models).

- **No general Bull vs Bear macro edge.** On the full walk-forward, no
  regime beats M0. On 2021–2023, BULL, NEUTRAL, and BEAR all show
  positive BSS. That is the same period effect, not a regime split.
- **No strong evidence that macro is irrelevant during Bear.** Persistent
  BEAR is somewhat weaker at 4w only (full BSS −0.061, N=56). At 8w and
  12w it is not a distinct extra-weak cell. 2021–2023 persistent BEAR
  N=28 is not a basis for “macro does not work in Bear.”
- **Transition vs persistent:** WEAK SUPPORT at **4w** only (TRANSITION
  BSS > PERSISTENT on both windows; full TRANSITION BSS only **+0.017**;
  non-overlap median BSS **−0.009**, 1/4 offsets). **NO SUPPORT** at 8w
  and 12w (persistent is better). Overall H3: **WEAK SUPPORT** — not
  established.

**Do not build a transition model from this evidence.** If 4w is mentioned
later, call it a candidate regime-conditional effect, not “macro predicts
regime transitions.”

---

## What is frozen vs what is not validated

Frozen for a later untouched evaluation: **MACRO_BASE_CANDIDATE_V1**
(see `CANDIDATE_MODEL_SPEC.md`). Status:
**CANDIDATE — NOT YET CLEAN-OOS VALIDATED.**

Not frozen as predictive: crypto-only models, crypto+macro concatenation,
delayed-window macros, regime-specific or transition models, a single
“best” horizon.
