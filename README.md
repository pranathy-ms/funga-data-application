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
├── requirements.txt
├── data/
│   ├── README.md              # Instructions for downloading FIA data
│   ├── GA_TREE.csv            # (downloaded by user)
│   ├── GA_PLOT.csv
│   ├── GA_COND.csv
│   ├── AL_TREE.csv
│   ├── AL_PLOT.csv
│   ├── AL_COND.csv
│   ├── SC_TREE.csv
│   ├── SC_PLOT.csv
│   └── SC_COND.csv
├── src/
│   ├── data_loader.py         # ETL: loads, joins, and cleans FIA tables
│   └── utils.py               # Shared helpers (ICC calculation, plotting)
├── notebooks/
│   ├── 01_data_pipeline_and_eda.ipynb
│   └── 02_power_analysis.ipynb
└── outputs/
    └── (generated figures and summary tables)
```

## Data Source

**USDA Forest Inventory & Analysis (FIA) Program**
- URL: https://apps.fs.usda.gov/fia/datamart/datamart.html
- States used: Georgia (GA), Alabama (AL), South Carolina (SC) — southeastern US, southern pine focus
- Tables: TREE (individual tree measurements), PLOT (site coordinates and conditions), COND (stand characteristics)
- The FIA program collects repeated measurements of permanent forest plots across the US, making it ideal for studying growth over time

See `data/README.md` for step-by-step download instructions.

## Notebook 1: Data Pipeline & Exploratory Analysis

**What it does:**
- Loads raw FIA CSVs for three states and joins TREE → PLOT → COND tables using the FIA key structure (CN, PLT_CN)
- Filters to southern pine species (loblolly pine: species code 131, shortleaf pine: species code 110)
- Calculates annual diameter growth increment from repeated measurements
- Handles missing values, outliers, and measurement inconsistencies
- Explores the nested structure of the data: how much do growth rates vary between states, between sites within a state, and between trees within a site?
- Calculates the **Intraclass Correlation Coefficient (ICC)** to quantify what proportion of total variance is at the site level vs the tree level
- Visualizations: growth distributions by site, growth vs environmental variables (elevation, stand age), variance decomposition

**Why this matters:**
The ICC tells us whether sites are meaningfully different from each other. A high ICC (say 0.3) means 30% of the variation in tree growth is explained by which site the tree is in — which means any experiment needs to account for this clustering. This directly motivates the power analysis in Notebook 2.

## Notebook 2: Power Analysis for Inoculation Trial Design

**What it does:**
- Uses the between-site and within-site variance estimated from the real FIA data in Notebook 1
- Simulates a hypothetical mycorrhizal inoculation experiment: treatment plots (fungi added) vs control plots (no treatment) across multiple forest sites
- Runs Monte Carlo simulations (1,000 iterations per design) to determine statistical power for different configurations:
  - Number of sites: 5, 10, 15, 20
  - Plots per site: 5, 10, 20
  - Effect sizes: 10%, 15%, 20% growth increase
- For each simulated experiment: generates treatment and control data with realistic variance, runs a t-test, records whether the effect was detected (p < 0.05)
- Power = proportion of simulations where the effect was correctly detected
- Produces **power curves**: x-axis = number of sites, y-axis = power, separate lines for different plots-per-site configurations, with a horizontal reference line at 80% power (standard threshold)

**Why this matters:**
Before investing in a multi-site, multi-year field trial, you need to know your experimental design can actually detect the effect you're hoping to find. A design with too few sites wastes time and money. A design with more sites than needed wastes resources. Power analysis finds the sweet spot.



## How to Run

```bash
# 1. Clone the repo
git clone https://github.com/pranathy-ms/forest-productivity-analysis.git
cd forest-productivity-analysis

# 2. Download FIA data (see data/README.md for instructions)

# 3. Install Python dependencies
pip install -r requirements.txt

# 4. Run notebooks in order
jupyter notebook notebooks/01_data_pipeline_and_eda.ipynb
jupyter notebook notebooks/02_power_analysis.ipynb


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
- **Experimental design**: Monte Carlo power analysis for multi-site trials
- **Reproducible workflows**: documented pipeline from raw data to actionable insights
- **Cross-language fluency**: Python + R implementations

## Next Steps

Potential extensions for deeper analysis:
- Mixed-effects models (Python `statsmodels.MixedLM` / R `lme4::lmer`) to formally model the hierarchical structure
- Spatial autocorrelation analysis between nearby plots
- Integration of satellite-derived NDVI as a remote proxy for ground-truth growth measurements
