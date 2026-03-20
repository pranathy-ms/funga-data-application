# CLAUDE.md — Project Context

## What This Is
Forest productivity analysis using USDA FIA public data (GA, AL, SC).
Two notebooks: (1) data pipeline + EDA, (2) power analysis for mycorrhizal inoculation trials.
Portfolio/assessment project — narrative and thought process matter as much as code.

## How to Run
- Jupyter notebooks run from the `notebooks/` directory (`DATA_DIR = "../data"`)
- Use `python3`, not `python` (pyenv does not expose bare `python`)
- Download data: `python3 data/download.py` (all states) or `pytest data/download.py` (GA only, smoke test)

## Project Structure
```
data/download.py                        # downloads FIA zips, extracts TREE/PLOT/COND per state
data/{GA,AL,SC}_{TREE,PLOT,COND}.csv   # gitignored — download locally (all 9 files present)
notebooks/01_data_pipeline_and_eda.ipynb  # in progress
notebooks/02_power_analysis.ipynb         # not yet built
DESIGN_NOTES.md                           # full decision log with reasoning and data dictionary
CLAUDE.md                                 # this file — quick reference
```
No `src/` module — all logic lives in notebooks.

## Key Decisions
- **Species**: 4 southern pines — 110 shortleaf, 111 slash, 121 longleaf, 131 loblolly (all ModRel=1)
  - 611 (sweetgum) is hardwood, excluded. 111 is slash pine, not Virginia pine.
- **Columns**: load with `usecols` only — full load took 3.5 min, targeted load ~10s
- **REMPER** lives in PLOT, not TREE — join must happen before computing growth
- **Growth formula**: `(DIA - PREVDIA) / REMPER` — annual diameter increment in inches/year
- **Filter before join**: STATUSCD=1 + species filter on TREE first, then join PLOT + COND
- **Join type**: inner join on both PLOT and COND — confirmed 0 rows dropped (clean data integrity)
- **PREVDIA nulls**: drop for now — 433,465 (~44%) of filtered 991,354 rows. Nulls span all years (not just early) due to annual panel rotation. Recovery possible via `PREV_TRE_CN` self-join (not yet implemented). See DESIGN_NOTES.
- **REMPER nulls**: drop — same structural reason as PREVDIA nulls
- **REMPER=0**: 534 cases, all in 1970–1972 only — confirmed data artifact, drop
- **Outlier handling**: TBD — leaning toward flagging with `is_outlier` column, not hard drop

## Columns Loaded
- **TREE**: `CN, PLT_CN, CONDID, SPCD, STATUSCD, DIA, PREVDIA, INVYR`
- **PLOT**: `CN, LAT, LON, ELEV, REMPER, MEASYEAR`
- **COND**: `PLT_CN, CONDID, STDAGE`

## STATUSCD Reference
- 0: Not in sample (remeasurement admin), excluded
- 1: Live tree ← keep
- 2: Dead tree, excluded
- 3: Removed/harvested (retired code), excluded

## FIA Table Join Keys
```
TREE.PLT_CN               → PLOT.CN
TREE.PLT_CN + TREE.CONDID → COND.PLT_CN + COND.CONDID
```

## Notebook 1 — Current State
Sections built and executed:
1. Imports + config (species dict, DATA_DIR)
2. Load raw CSVs with usecols — read and concat split into separate cells
3. TREE exploration: dtypes/nulls, INVYR dist, STATUSCD counts, SPCD top 20
4. PLOT exploration: dtypes/nulls, REMPER distribution
5. COND exploration: dtypes/nulls, STDAGE describe
6. Filter + join: 4,177,453 → 991,354 rows (0 dropped from joins, all from status+species filter)
7. Edge case validation: PREVDIA nulls by INVYR, REMPER nulls by MEASYEAR, REMPER=0 by year

**Next cell to write**: growth computation — `(DIA - PREVDIA) / REMPER`, drop nulls/zeros, flag outliers

## Notebook 2 — Not Started
Uses variance estimates from Notebook 1: ICC + between-site/within-site variance components.
Output from Notebook 1 → `outputs/variance_params.json` (TBD decision).

## Key Data Findings
- 991,354 live southern pine trees after filter + join (0 integrity issues)
- 433,465 (~44%) have null PREVDIA → ~558k rows available for growth computation
- REMPER=0 all in 1970–1972 (artifact), REMPER nulls spread across all years (panel rotation)
- STDAGE nulls (~32% of COND) — non-forest conditions, only affects stand-age EDA
- FIA switched from periodic to annual panel inventory ~2000 — explains INVYR distribution
