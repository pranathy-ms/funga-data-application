# Forest Productivity Analysis: Data Pipeline & Experimental Design

Analyzing southern pine forest growth using USDA Forest Inventory & Analysis (FIA) public data, and simulating power analysis for mycorrhizal inoculation field trials.

## Motivation

Forest productivity research generates nested, spatially-structured data: individual trees are measured within plots, plots are grouped within sites, and sites span different climatic and soil conditions. Before running expensive field trials (like testing whether fungal inoculation boosts tree growth), researchers need to answer a practical question: **how many sites and plots do we need to detect a real effect?**

This project demonstrates two things:
1. How to ingest, clean, and explore real ecological data from the FIA database
2. How to use the variance structure in that data to design well-powered experiments

## Project Structure

```
forest-productivity-analysis/
├── README.md
├── DESIGN_NOTES.md            # Decision log with reasoning
├── requirements.txt
├── data/
│   ├── download.py            # Downloads and extracts FIA data (run from project root)
│   └── {STATE}_{TABLE}.csv    # Downloaded locally, gitignored
├── notebooks/
│   ├── 01_data_pipeline_and_eda.ipynb
│   └── 02_power_analysis.ipynb
└── outputs/
    └── variance_params.json       # ICC + variance components (NB1 → NB2 handoff)
```

## Data Source

**USDA Forest Inventory & Analysis (FIA) Program**
- URL: https://apps.fs.usda.gov/fia/datamart/datamart.html
- States used: Georgia (GA), Alabama (AL), South Carolina (SC) — southeastern US, southern pine focus
- The FIA program visits fixed forest plots on a repeating cycle and measures every tree, making it ideal for tracking growth over time

Run `python3 data/download.py` from the project root to download all state data automatically.

### Data Model

Three tables are used per state, joined as: `TREE → PLOT → COND`

**TREE** — one row per tree per plot visit
| Column | Meaning |
|---|---|
| `SPCD` | Species code (131=loblolly, 111=slash, 121=longleaf, 110=shortleaf pine) |
| `STATUSCD` | 1=live (kept), 0/2/3=not in sample, dead, or removed (excluded) |
| `DIA` | Trunk diameter measured at chest height (4.5 ft), in inches |
| `PREVDIA` | Same measurement from the previous visit — null if first measurement |
| `PLT_CN` | Links to PLOT (which plot visit this tree belongs to) |
| `CONDID` | Links to COND (which forest patch within the plot this tree is in) |

**PLOT** — one row per plot visit (a plot is a fixed ~1 acre forest location)
| Column | Meaning |
|---|---|
| `REMPER` | Years since the last visit — used to annualize growth: `(DIA - PREVDIA) / REMPER` |
| `LAT`, `LON`, `ELEV` | Location and elevation for environmental analysis |

**COND** — one row per forest condition (patch type) per plot visit
| Column | Meaning |
|---|---|
| `STDAGE` | Age of the dominant trees in this patch, in years. Null for non-forested patches |

See `DESIGN_NOTES.md` for the full data dictionary and decision log.

## Notebook 1: Data Pipeline & Exploratory Analysis

**What it does:**
- Loads raw FIA CSVs for three states and joins TREE → PLOT → COND tables using the FIA key structure (CN, PLT_CN)
- Filters to four southern pine species: loblolly (131), slash (111), longleaf (121), shortleaf pine (110)
- Calculates annual diameter growth increment from repeated measurements
- Handles missing values, outliers, and measurement inconsistencies
- Explores the nested structure of the data: how much do growth rates vary between states, between sites within a state, and between trees within a site?
- Calculates the **Intraclass Correlation Coefficient (ICC)** to quantify what proportion of total variance is at the site level vs the tree level
- Visualizations: growth distributions by site, growth vs environmental variables (elevation, stand age), variance decomposition

**Why this matters:**
The ICC tells us whether sites are meaningfully different from each other. The FIA data yields ICC = 0.62 — meaning 62% of the variation in tree growth is explained by which site the tree is in. Any field trial must account for this clustering when calculating required sample size. This directly motivates the power analysis in Notebook 2.

## Notebook 2: Power Analysis for Inoculation Trial Design

**What it does:**
- Loads variance components (ICC, σ²_between, σ²_within) estimated from FIA data in Notebook 1
- Frames Funga's inoculation trial as a **cluster-randomized design**: sites are the experimental unit (randomized to treatment or control), trees are measurement units within sites
- Derives the analytical power formula for two-arm cluster-randomized trials and computes required sites per arm at 80% power across effect size scenarios (10%, 20%, 30% growth improvement)
- Explores two design levers: trees per site (sensitivity analysis shows this is a weak lever due to high ICC) and site matching (lower ICC directly reduces trial burden)
- Produces **power curves**, a trees-per-site sensitivity plot, an ICC sensitivity plot, and a planning table

**Key findings:**
- At ICC = 0.62 and 20 trees/site: detecting a 20% effect requires ~247 sites/arm; a 30% effect requires ~110
- Trees per site is nearly irrelevant — going from 5 to 30 trees saves fewer than 25 sites
- Site matching (reducing ICC from 0.62 to 0.40) cuts required sites by ~33%, equivalent to running a much larger trial

**Why this matters:**
Before investing in a multi-site, multi-year field trial, you need to know your experimental design can actually detect the effect you're hoping to find. With ICC = 0.62, the limiting resource is not measurement effort within sites — it is the number of distinct sites enrolled. Power analysis makes this tradeoff concrete.



## How to Run

```bash
# 1. Clone the repo
git clone https://github.com/pranathy-ms/forest-productivity-analysis.git
cd forest-productivity-analysis

# 2. Download FIA data
python3 data/download.py

# 3. Install Python dependencies
pip install -r requirements.txt

# 4. Run notebooks in order (launch Jupyter from the notebooks/ directory)
cd notebooks
jupyter notebook 01_data_pipeline_and_eda.ipynb
jupyter notebook 02_power_analysis.ipynb


```

## Dependencies

**Python:**
- pandas, numpy, scipy, scikit-learn, matplotlib, seaborn
- statsmodels (for ICC calculation)
- jupyter


## Relevance

This project demonstrates skills in:
- **Ecological data wrangling**: ingesting and cleaning real USDA forest inventory data
- **Exploratory analysis**: understanding nested variance structure in field data
- **Experimental design**: analytical power analysis for cluster-randomized trials
- **Reproducible workflows**: documented pipeline from raw data to actionable insights
- **Reproducible data acquisition**: automated download pipeline from a public federal database

## Next Steps

Potential extensions for deeper analysis:
- Recover PREVDIA nulls via `PREV_TRE_CN` self-join to increase usable row count (~44% currently dropped)
- Spatial autocorrelation analysis between nearby plots
- Integration of satellite-derived NDVI as a remote proxy for ground-truth growth measurements
