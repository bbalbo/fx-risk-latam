# FX Risk LatAm

![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![Pandas](https://img.shields.io/badge/pandas-2.0%2B-150458)
![NumPy](https://img.shields.io/badge/numpy-1.26%2B-013243)
![License](https://img.shields.io/badge/license-unspecified-lightgrey)
![Status](https://img.shields.io/badge/status-active-success)
![License](https://img.shields.io/badge/license-PolyForm%20Noncommercial-blue)

> 🇪🇸 ¿Buscas la versión en español? Lee **[README.es.md](README.es.md)**.

A quantitative market-risk toolkit for Latin American currencies. It pulls daily FX data, computes returns, volatility, correlation, Value at Risk, stress scenarios, and statistical anomalies — the same building blocks used in institutional FX risk desks, distilled into a small, readable Python codebase.

---

## Table of Contents

- [Overview](#overview)
- [Why this project](#why-this-project)
- [Currencies covered](#currencies-covered)
- [Project structure](#project-structure)
- [Installation](#installation)
- [Quick start](#quick-start)
- [Module reference](#module-reference)
- [Methodology notes](#methodology-notes)
- [Data source](#data-source)
- [Roadmap ideas](#roadmap-ideas)
- [License](#license)

---

## Overview

**FX Risk LatAm** answers a simple question for a regional currency book: *how risky is this exposure, and how risky was it during a crisis?*

The pipeline is:

```
Frankfurter API  →  SQLite (raw rates)  →  returns  →  risk metrics
```

From there, four standard risk lenses are computed:

| Lens | Question it answers | Module |
|---|---|---|
| **Volatility** | How much does this currency move, recently vs. historically? | `volatility.py` |
| **Value at Risk (VaR) / Expected Shortfall** | What's the worst daily loss I should expect, at a given confidence level? | `var.py` |
| **Correlation** | Do these currencies move together, or independently? | `correlation.py` |
| **Stress testing** | What actually happened to this currency during COVID, the 2022 Fed hikes, the 2023 ARS devaluation, or the 2024 JPY carry unwind? | `stress.py` |
| **Anomaly detection** | Which specific days were statistically extreme, with no prior assumption about the cause? | `anomalies.py` |

## Why this project

Most public FX tutorials stop at "plot the exchange rate." This project goes one level deeper, into the kind of analysis a risk desk actually produces:

- **Historical, not parametric, VaR** — LatAm FX returns have fat tails (high kurtosis). A parametric (normal-distribution) VaR model would systematically understate tail risk for currencies like ARS or MXN, so this project uses historical simulation instead.
- **Event-based stress testing, not just statistics** — VaR summarizes a whole distribution; stress testing isolates specific, nameable events (COVID, Fed hikes, a real devaluation) and reports what actually happened. That's harder to dismiss in front of a risk committee — or in an interview.
- **Two FX perspectives, not one** — most resources default to a USD-only view. This project builds both a USD-base table and a CLP-base table, so the same data also answers "what does this look like from Chile?"

## Currencies covered

**Core LatAm (7):**

| Code | Currency |
|---|---|
| CLP | Chilean peso |
| BRL | Brazilian real |
| ARS | Argentine peso |
| MXN | Mexican peso |
| COP | Colombian peso |
| PEN | Peruvian sol |
| VES | Venezuelan bolívar soberano |

**Reference currencies (3)** — included for specific analytical reasons:

| Code | Currency | Reason |
|---|---|---|
| EUR | Euro | Global benchmark |
| CNY | Chinese yuan | Chile's largest trading partner |
| JPY | Japanese yen | Classic safe-haven currency |

**Plus gold (XAU)** as a non-fiat reference asset, expressed both in USD and in CLP.

> **Note on date range:** all series start on **2018-05-29**, the date the Venezuelan *bolívar soberano* (VES) was introduced. This is a deliberate design choice — cutting every series to a common start avoids mixing real data gaps with the structural absence of VES data before that date. Data is actually pulled from 2015 internally so that forward-fill has prior values to work with right at that boundary.

## Project structure

```
fx-risk-latam/
├── requirements.txt
├── README.md                # this file
├── README.es.md              # Spanish version
├── data/                     # generated locally, not committed (see .gitignore)
│   └── fx_data.db
└── src/
    ├── __init__.py
    ├── config.py              # currencies, date ranges, paths — single source of truth
    ├── extraction.py          # pulls data from Frankfurter API → SQLite
    ├── returns.py              # simple & log returns, summary statistics
    ├── volatility.py           # rolling annualized volatility (30d / 90d / 252d)
    ├── var.py                  # historical VaR + Expected Shortfall
    ├── correlation.py          # static & rolling correlation matrices
    ├── stress.py                # historical crisis scenario testing
    └── anomalies.py             # rolling z-score extreme-move detection
```

## Installation

Requires **Python 3.10+** (the codebase uses `dict[str, tuple[str, str]]`-style type hints).

```bash
git clone https://github.com/bbalbo/fx-risk-latam.git
cd fx-risk-latam
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Dependencies are intentionally minimal:

| Package | Purpose |
|---|---|
| `requests` | calls the Frankfurter API |
| `pandas` | tabular data, returns, rolling windows |
| `numpy` | log returns, annualization math |

No API key is required — [Frankfurter](https://frankfurter.dev/) is a free, open exchange-rate API with daily data going back to 1948.

## Quick start

**1. Pull and store the data** (run once, or whenever you want fresh data):

```bash
python -m src.extraction
```

This builds two local SQLite tables in `data/fx_data.db`:
- `fx_rates_usd` — all currencies vs. USD (Table A)
- `fx_rates_clp` — all currencies vs. CLP, the Chilean perspective (Table B)

**2. Run any analysis module directly:**

```bash
python -m src.returns        # return summary (mean, vol, skew, kurtosis)
python -m src.volatility     # 30d / 90d / 252d annualized volatility
python -m src.var            # VaR & Expected Shortfall at 90/95/99% confidence
python -m src.correlation    # full-period + rolling correlation vs. CLP
python -m src.stress         # cumulative return during 4 historical crises
python -m src.anomalies      # top 20 most extreme single-day moves
```

**3. Or use it as a library:**

```python
from src.returns import load_rates, log_returns
from src.var import var_summary
from src.stress import full_stress_table

rates   = load_rates()
returns = log_returns(rates)

print(var_summary(returns))
print(full_stress_table(returns))
```

Every public function ships with a runnable docstring example (`>>>`), so you can also sanity-check behavior with `python -m doctest src/var.py -v` (or any other module).

## Module reference

### `config.py`
Single source of truth for currency lists, date boundaries, and the SQLite path. Changing the analysis universe (e.g. adding a currency) means editing one file, not hunting through extraction logic.

### `extraction.py`
Fetches daily rates from Frankfurter, pivots them into a wide table (dates × currencies), and forward-fills weekend/holiday gaps so the series is continuous. Validates that zero `NaN`s remain before saving — if any do, it raises rather than silently saving incomplete data.

### `returns.py`
Computes both simple returns (`P_t / P_{t-1} - 1`) and log returns (`ln(P_t / P_{t-1})`). Log returns are used everywhere downstream because they're time-additive and better-behaved statistically. Also computes `return_summary()`: mean, std, annualized vol, min, max, skew, kurtosis — kurtosis specifically motivates the historical (not parametric) VaR choice later.

### `volatility.py`
Rolling standard deviation of log returns, annualized with the standard `√252` trading-day convention. Three window sizes are standard in market risk: 30d (short-term stress), 90d (medium-term trend), 252d (one trading year). Comparing 30d vs. 252d volatility tells you whether a currency is *currently* unusually calm or unusually stressed relative to its own history.

### `var.py`
**Historical simulation** VaR and Expected Shortfall (ES/CVaR) at 90%, 95%, and 99% confidence. Historical simulation is used deliberately instead of a parametric (normal) model, because LatAm FX returns exhibit fat tails — a normal-distribution assumption would understate real tail risk. ES, adopted by Basel III as the primary tail-risk measure in 2016, captures the *severity* of losses beyond the VaR cutoff, not just the cutoff itself.

### `correlation.py`
Computes correlation **on returns, not price levels** — price levels share common trends that artificially inflate correlation. Supports both a full-period snapshot and a rolling correlation against a chosen base currency, useful for spotting regime shifts (e.g., did CLP and BRL become more correlated during a commodity cycle?).

### `stress.py`
Runs four predefined historical stress scenarios and reports the cumulative log return per currency during each:

| Scenario | Window |
|---|---|
| COVID-19 crash | Feb 20 – Mar 31, 2020 |
| Fed rate hikes | Jun 1 – Oct 31, 2022 |
| ARS devaluation (Milei) | Dec 11 – Dec 15, 2023 |
| JPY carry unwind | Aug 1 – Aug 9, 2024 |

Unlike VaR, which summarizes a whole distribution, this isolates *named, real events* — a result that's far harder to wave away than a statistical percentile.

### `anomalies.py`
Flags individual days where a currency's return deviates more than a threshold (default ±3σ) from its own 30-day rolling mean/std. This is complementary to stress testing: stress testing starts from a known event and asks what happened; anomaly detection starts from the data and asks which days were extreme, with no prior knowledge of the cause.

## Methodology notes

- **Returns convention**: all rates are expressed as *units of local currency per 1 USD* (Table A) or *per 1 CLP* (Table B). A **positive** return therefore means the currency **depreciated** (it takes more local currency to buy one USD).
- **252 trading days/year** is the standard annualization convention in market risk — used consistently across `volatility.py` and `returns.py`.
- **VaR sign convention**: VaR and ES are reported as **negative** numbers (they represent losses). ES is always ≤ VaR (a more negative, i.e. larger, loss).
- **Why cut the start date to 2018-05-29 but pull from 2015?** VES didn't exist before May 2018. Pulling from 2015 gives `ffill()` real prior values to draw on right at that boundary, instead of producing artifacts at the edge of the series.

## Data source

All data comes from the [Frankfurter API](https://frankfurter.dev/) — a free, open-source, no-API-key exchange rate service built on European Central Bank reference rates (and gold spot data), with daily history back to 1948.

## Roadmap ideas

- [ ] Add a `LICENSE` file
- [ ] CLI entry point (`fx-risk extract`, `fx-risk var --confidence 0.99`)
- [ ] Parametric (variance-covariance) VaR as a comparison baseline
- [ ] Lightweight plotting helpers (volatility term structure, rolling correlation heatmap)
- [ ] GitHub Actions workflow to refresh `data/fx_data.db` on a schedule
- [ ] Unit test suite beyond doctests (`pytest`)

## License

This project is licensed under [PolyForm Noncommercial 1.0.0](LICENSE) — free for personal, educational, and noncommercial use. Commercial use requires permission from the author.

---

<p align="center">Built for understanding how Latin American currencies actually behave under stress — not just how they trend.</p>
