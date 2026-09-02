# Hsieh, Huang & Liu (2025) — replication workspace

**Paper:** Hsieh, Chia-Hsun; Huang, Pao-Hsien; Liu, Hung-Chun (2025).
“State transitions and momentum effect in cryptocurrency market.”
*Finance Research Letters*, Volume 86, Part A, 108356.
DOI: `10.1016/j.frl.2025.108356`

Standalone academic replication. It does not use Wen, rally-map, or Moskowitz files.

PDF used: `1-s2.0-S1544612325016101-main.pdf` (12 pages, Elsevier full text).

---

## Paper specification

### Universo

- CoinMarketCap.com, all listed coins including delisted (Appendix A).
- Final sample: **2130 unique cryptocurrencies** (Table 1 / Appendix A).
- Stablecoins excluded (Data section + Table 1). Tickers are **not listed**.
- Market cap below **$1 million** excluded (Liu et al. 2022 screen).

### Fuente / periodo / frecuencia

- Daily close, market cap, volume from CoinMarketCap, January 2015–December 2023.
- Weekly returns from daily data (footnote 6: CMC aggregates 200+ exchanges).

### Appendix A filters

1. Drop token-days with missing return, volume, or market cap. Formation requires
   non-missing price, volume, and mcap. Drop price = 0. Discard coins with price
   history shorter than **20 weeks**.
2. Market cap < $1m excluded.
3. Keep delisted coins while history exists (Jegadeesh–Titman rolling rebalance
   drops them when untradeable).
4. Drop token-weeks with **zero daily trading volume**.
5. **Weekly returns = log difference of Friday closing prices.** Both Friday
   prices required; otherwise drop.

### Market return

- Value-weighted average of eligible coins (section 3.1).
- Lagged vs contemporaneous weights: **NOT STATED**. Replica uses lagged mcap.

### UP / DOWN — paper contradicts itself

**Section 3.1 (Cooper et al. 2004):** week \(t\) is UP if the value-weighted
cumulative market return over the past four weeks \((t-5\) to \(t-1)\) is
nonnegative.

**Table 2 note:** at the beginning of week \(t\), UP if the **past one-week**
buy-and-hold market return is nonnegative.

**Table 3 / Fig. 1 / Table 4 notes (Asem and Tian 2010):** prior state from the
**past one-week** market return; **subsequent** week is UP/DOWN from **that
week’s** market return (holding-period state, contemporaneous with K=1 payoff).

The core table we replicate is **Table 3**, using the Table 3 note.
Section 3.1 Cooper 4-week states are also computed and stored, labeled separately.

### Momentum (main tables)

- Formation **J = 2** weeks (Tables 2–3; footnote 7: J=1 also works, J=3,4 weaker).
- Holding **K = 1, 2, 3, 4** weeks.
- Five portfolios: Loser, 2, 3, 4, Winner (quintiles).
- WML = Winner − Loser.
- No skip period stated.
- Returns weekly, **decimal**.
- Newey–West (1987) t-statistics. **Lag length NOT STATED.** Replica uses 4.
- Overlapping JT holding: **NOT STATED** explicitly; replica uses Jegadeesh–Titman
  (1993) calendar-time overlapping portfolios, which the appendix cites for
  rebalancing.
- **Winner/loser weighting NOT STATED.** Replica primary = **equal-weighted**
  (Table 4 B–C drop small/illiquid coins, which would barely affect VW).
  Value-weighted rows are also written.

### Table 3 paper numbers (J=2)

| Transition | K=1 WML | t | K=2 WML | t |
| --- | ---: | ---: | ---: | ---: |
| UP–UP | 0.0119 | 2.31 | 0.0101 | 2.45 |
| UP–DOWN | 0.0094 | 0.93 | −0.0026 | −0.30 |
| DOWN–UP | −0.0082 | −0.56 | −0.0010 | −0.09 |
| DOWN–DOWN | 0.0071 | 1.06 | 0.0066 | 1.26 |

Citing papers that said “11.9–15.5 **basis points**” were wrong: Table 3 is
**1.19–1.55 percentage points** per week in UP–UP (K=1 winner 0.0145, WML 0.0119;
K=2 winner 0.0155).

### Robustness (not this phase)

Liu et al. (2022) 3-factor alphas; drop bottom 20% mcap; drop bottom 20% volume;
sentiment/attention/macro regressions; meme stocks (Table 7).

---

## Replica data access

Official CMC Pro historical API: HTTP 401 without a key.

Public `listings/historical` snapshots are used. After the PDF, snapshots are
**Fridays** (2015-01-02 through 2023-12-29), not Wednesdays.

Replica differences vs Appendix A:

1. Friday **snapshots**, not a daily file then Friday log returns (if a Friday is
   missing, that token-week is dropped; no interpolation).
2. Zero-volume filter uses Friday `volume24h`, not every day of the week.
3. Stablecoin list is ours (CMC ids / symbols / names); paper does not list them.
4. Momentum-leg weighting and NW lags as above.

Wednesday snapshot files already on disk are ignored. Only Friday dates enter
the panel.

---

## Folder layout

```text
research/papers/hsieh_2025_state_transition_momentum/
├── README.md
├── data/raw/listings/          # one CSV per snapshot date (resume-safe)
├── data/raw/data_manifest.csv
├── data/processed/crypto_weekly_panel.csv
├── data/processed/market_states.csv
├── src/replicate_hsieh_2025.py
└── results/
    ├── state_transition_momentum.csv
    └── replication_summary.md
```

## How to run

```bash
python3 src/replicate_hsieh_2025.py
```

See `results/replication_summary.md` for the verdict.
