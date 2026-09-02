# Phase 6A — Macro weekly dataset

Build a clean, auditable **weekly Friday** macro panel for **2015–2023**.

This phase answers only:

> Do we have a temporally defensible macro dataset that could have been
> known week by week?

No models. No regressions. No crypto merge. No 2024–2026. No scores.
No Bull/Bear macro labels. Phases 3–5 and V1 are not modified.

## Sample

- Calendar window: 2015-01-01 through 2023-12-31
- Output grid: Fridays `2015-01-02` … `2023-12-29`
- Lookback raw data may start in 2014 so 4-week / 12-week changes exist
  at the start of 2015
- **2024–2026 is not downloaded, parsed, stored, or used**

## Run

```bash
python3 src/build_macro_dataset.py
```

Requires network access to Federal Reserve Board DDP, NY Fed Markets,
U.S. Treasury, and Yahoo Finance chart API.

## Outputs

- `results/macro_weekly.csv` — one row per Friday
- `results/MACRO_DATA_AUDIT.md` — sources, alignment, release lag, vintage,
  lookahead, coverage, missingness, sample rows, warnings

Raw downloads are cached under `data/raw/` (not part of the ChatGPT return set).

## Series policy

If a requested series cannot be obtained from a date-bounded official or
public source, it is **omitted**, not invented.

Documented substitutions / omissions (see the audit):

- `DXY_LEVEL` = Fed H.10 Nominal Broad Dollar Index, **not** ICE DXY
- `FED_BALANCE_SHEET` = H.4.1 Reserve Bank credit (Wednesday), **not** FRED WALCL
- `HY_SPREAD` omitted (FRED ICE BofA OAS unreachable; no substitute invented)

