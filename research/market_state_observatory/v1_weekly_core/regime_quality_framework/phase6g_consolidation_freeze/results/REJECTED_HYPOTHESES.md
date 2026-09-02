# Rejected hypotheses — closed for now

These hypotheses are **CLOSED FOR NOW** on the 2015–2023 diagnostic
branch. Reopening any of them requires a **new research branch**, a
pre-specified protocol, and evidence that is not a re-read of the same
inspected 2021–2023 window.

2021–2023 is **PSEUDO-OOS / TEMPORAL ROBUSTNESS**, not a license to
retry variants until it looks better.

---

## H1

**"Crypto-only reliably predicts market direction at 4–12 weeks"**

**STATUS: NOT SUPPORTED**

### What was tested

Phase 5: expanding walk-forward of V1 state frequencies and crypto
level/dynamics logistics vs expanding mature base rate (M0), 4w and 12w
sign targets, plus secondaries. Phase 6D horizon diagnostic: frozen
reduced crypto set vs M0 at 4w, 8w, 12w.

### What failed

Phase 5 verdict **C**. Primary sign cells: M1/M2/M3 did not improve Brier
and log loss vs M0. Phase 6D: CRYPTO **NO EDGE** at 4w, 8w, and 12w
(full and 2021–2023 BSS ≤ 0; non-overlap 0 offsets BSS > 0).

### Why we stop

Repeated frozen specs lost to the base rate. Further crypto feature
search on the same sample would be mining.

### What would be needed to reopen

A **new** pre-specified crypto block, not tuned on 2015–2023 walk-forward
results, evaluated on an untouched period (2024–2026 remains sealed until
the macro candidate is frozen and left unchanged). Beating M0 on Brier
on full expanding history **and** a period that was not used for
specification, plus non-overlapping BSS consistency.

---

## H2

**"Macro works better with a fixed 4–8 week delay"**

**STATUS: NOT SUPPORTED**

### What was tested

Phase 6E: frozen four-feature macro at t, crypto outcome over
`t+L+1 … t+L+H`, L ∈ {0, 4, 8}, H ∈ {4, 8, 12}. Train
`s <= t - (L+H)`. Same logistic as L=0.

### What failed

L=4 and L=8 did not beat L=0. Full-sample BSS worsened at every delayed
cell. 2021–2023 BSS declined with lag; L=8 at H=8 and H=12 is **NO EDGE**.
Non-overlap failed throughout.

### Why we stop

The pre-specified lag grid is complete. Picking another delay from the
same sample would be a lag search.

### What would be needed to reopen

A different, pre-registered lag (not 4 or 8) **or** a new data period,
with L=0 as the frozen comparator, without adding lags after seeing
results.

---

## H3

**"Macro is robustly more useful near regime transitions"**

**STATUS: WEAK / NOT ESTABLISHED**

### What was tested

Phase 6F: existing L=0 M_MACRO probabilities, sliced by catalog
`state_direction` and a backward-looking t vs t−4 TRANSITION /
PERSISTENT flag. No new model. Horizons 4/8/12.

### What failed

SUPPORTS H3 (including non-overlap) was **not** met at any horizon.
4w: TRANSITION BSS > PERSISTENT on full and 2021–2023, but full
TRANSITION BSS is only +0.017 and non-overlap median BSS is negative
(WEAK SUPPORT). 8w and 12w: **NO SUPPORT** (persistent better).
Directional transition cells include LOW SAMPLE; no conclusions from
N < 15.

### Why we stop

Building a transition model, interactions, or Bull/Bear logistics would
overfit a 4w-only, non-overlap-failing contrast.

### What would be needed to reopen

Pre-specified transition definition, adequate N, TRANSITION BSS > M0
and > PERSISTENT on expanding history **and** an untouched period, with
non-overlapping consistency. Not a re-slice of 2015–2023.

---

## H4

**"Macro is clearly irrelevant during persistent Bear regimes"**

**STATUS: NOT SUPPORTED**

### What was tested

Phase 6F: BEAR and BEAR_PERSISTENT slices of the same L=0 forecast vs
slice-matched M0.

### What failed

The claim is too strong for the numbers. Full walk-forward: BEAR BSS
near zero / slightly negative, similar to other regimes (none beat M0).
Persistent BEAR is weaker at 4w only. At 8w persistent BEAR full BSS is
slightly positive; at 12w 2021–2023 persistent BEAR BSS is positive
(N=28 — not a “clear irrelevance” result). 2021–2023 **all** regimes
including BEAR show positive BSS.

### Why we stop

Dropping Bear weeks or adding a Bear-off switch would be a regime rule
fit to a non-finding.

### What would be needed to reopen

Pre-specified Bear (or persistent-Bear) exclusion **before** seeing
slice BSS, then confirmation on an untouched period that macro skill
is absent there while present elsewhere — not the current mixed, small-N
pattern.

---

## H5

**"There is an optimal predictive horizon among 4/8/12 weeks"**

**STATUS: NOT ESTABLISHED**

### What was tested

Phase 6D: same frozen crypto and macro specs at H = 4, 8, 12. Phase 6E:
same H grid with lags.

### What failed

No horizon is PROMISING. Crypto is NO EDGE at all three. Macro is WEAK
at all three. Full-sample BSS and 2021–2023 BSS move in opposite
directions for macro as H increases. Non-overlap fails at every H.
Choosing 12w because 2021–2023 BSS is largest would be post-hoc.

### Why we stop

The three horizons were pre-specified. Ranking them after inspection is
horizon tuning.

### What would be needed to reopen

A new study that **commits to one H before** looking at 2015–2023
results — or evaluates all three on a sealed period **without** picking
a winner to redesign the model. This freeze already requires evaluating
4w, 8w, and 12w later without altering the candidate after seeing scores.
