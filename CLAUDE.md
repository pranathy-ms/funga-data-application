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
notebooks/01_data_pipeline_and_eda.ipynb  # complete
notebooks/02_power_analysis.ipynb         # complete (pending review)
outputs/variance_params.json             # ICC + variance components from Notebook 1 → Notebook 2
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
- **Outlier handling**: No hard cap applied — smooth right-skewed tail with no natural break. Negative growth hard-dropped (7,347 rows, measurement error). Near-zero retained (valid biology + REMPER artifact). Revisit if ICC estimates look inflated.
- **outputs/variance_params.json**: ICC + variance components saved here for Notebook 2 to load

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

## Notebook 1 — Complete
All 10 sections built and executed.

1. Imports + config (species dict, DATA_DIR, OUTPUTS_DIR)
2. Load raw CSVs with usecols — read and concat split into separate cells
3. TREE exploration: dtypes/nulls, INVYR dist, STATUSCD counts, SPCD top 20
4. PLOT exploration: dtypes/nulls, REMPER distribution
5. COND exploration: dtypes/nulls, STDAGE describe
6. Filter + join: 4,177,453 → 1,271,080 rows (0 dropped from joins, all from status+species filter)
7. Edge case validation: PREVDIA nulls by INVYR, REMPER nulls by MEASYEAR, REMPER=0 by year
8. Growth computation: drop nulls/REMPER=0/negatives → 785,988 rows; compute `annual_growth`
9. EDA: growth by state (AL>SC>GA, ~0.03 spread), by species (loblolly>slash>longleaf>shortleaf), by stand age (sigmoid curve, peak 10–30yr), by elevation (declining, 93% below 800ft)
10. Variance decomposition + save: `mixedlm("annual_growth ~ 1", groups=PLT_CN)` → ICC=0.62, saved to `outputs/variance_params.json`

## Notebook 2 — Complete
All 6 sections built and executed. Six review issues fixed (see below).

1. Load variance params from `outputs/variance_params.json`
2. Trial design + power formula: cluster-randomized design explained, formula derived
3. Power curves: n_sites vs power for 10/20/30% effect sizes (m=20 trees/site)
4. Trees-per-site sensitivity: m=5→30 saves <25 sites — trees per site is a weak lever
5. ICC sensitivity: required sites vs ICC across effect sizes — site matching directly reduces burden
6. Recommendation: narrative + planning table across ICC scenarios

## Review Fixes Applied
- NB1 Cell 5: removed duplicate print loop
- NB1 Cell 37: added PLT_CN per-visit nuance (ICC captures spatial + temporal clustering, appropriate for trial planning)
- NB2 Cell 6: fixed 10% power curve x-axis bug — off-chart case now shows clean text box, all panels capped at x=300
- NB2 Cell 12: summary table now uses exact `icc` variable (0.6229) for FIA row — outputs 247/110, consistent with markdown
- NB2 Cell 11: "90%+" replaced with accurate "89–97%, depending on trees per site"
- NB2 Cell 11 + DESIGN_NOTES: removed AMF-sourced effect size numbers (−12% to +48%, consortium ~+48%); replaced with planning scenario framing citing the 2025 FEM meta-analysis (ECM inoculation significantly increases Pinus/Picea growth; specific % varies by site conditions)

## Remaining Tasks
- Decide if project is ready to close and submit

## Key Data Findings
- 1,271,080 live southern pine trees after filter + join (0 integrity issues)
- 785,988 rows usable for growth computation (after dropping null PREVDIA/REMPER, REMPER=0, and negative growth)
- REMPER=0 all in 1970–1972 (artifact), REMPER nulls spread across all years (panel rotation)
- STDAGE nulls (~32% of COND) — non-forest conditions, only affects stand-age EDA
- FIA switched from periodic to annual panel inventory ~2000 — explains INVYR distribution
- **ICC = 0.62** (var_between=0.0215, var_within=0.0130) — 62% of growth variance is between plots (sites). Confirms plot is the experimental unit for a Funga field trial.
