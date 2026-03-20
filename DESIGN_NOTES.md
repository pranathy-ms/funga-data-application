# Design Notes

Running log of decisions, discoveries, and open questions made while building this project.

---

## Data Download

**Decision: Full state zip download, not per-table**
FIA datamart offers per-table downloads but the URLs are less stable. Downloading the full state zip and extracting what we need is simpler and more reproducible.

**Decision: `test_download()` function in `download.py`**
Added a pytest-compatible `test_download()` that runs for GA only, so anyone can validate the download pipeline without pulling all three states. Full run via `python data/download.py`.

**Note: Use `python3`, not `python`**
pyenv setup does not expose a bare `python` command. Always use `python3` or `pytest` directly.

---

## FIA Data Model

The FIA (Forest Inventory & Analysis) program works by visiting fixed physical locations in forests — called **plots** — on a repeating cycle and measuring every tree within them. The same plot and trees get measured multiple times over decades, which is what allows us to track growth over time.

The database uses three core tables per state. Each table has one row per entity per plot visit — meaning the same physical tree or plot appears in multiple rows across inventory years.

### TREE
One row per tree per plot visit. Contains individual tree measurements.

| Column | Description |
|---|---|
| `CN` | Unique ID for this specific tree record (a new ID is assigned each visit) |
| `PLT_CN` | Links this tree to its plot visit in the PLOT table |
| `CONDID` | Links this tree to its forest condition in the COND table (see COND below) |
| `SPCD` | Numeric species code (e.g. 131 = loblolly pine). See species reference in Species Selection section |
| `STATUSCD` | Whether the tree is alive, dead, or removed at this visit (see STATUSCD reference below) |
| `DIA` | Diameter of the tree trunk measured at 4.5 feet above the ground (chest height), in inches. Standard forestry measurement called DBH — diameter at breast height |
| `PREVDIA` | The same diameter measurement taken at the *previous* visit to this plot. Null if this is the tree's first recorded measurement. The difference between DIA and PREVDIA tells us how much the tree grew |
| `INVYR` | The year this measurement was recorded |

### PLOT
One row per plot visit. A plot is a fixed patch of forest (roughly 1 acre) that FIA crews return to on a cycle to remeasure.

| Column | Description |
|---|---|
| `CN` | Unique ID for this plot visit (linked to by `TREE.PLT_CN`) |
| `LAT`, `LON` | GPS coordinates of the plot's location |
| `ELEV` | How high above sea level the plot is, in feet. Used to study whether elevation affects tree growth |
| `REMPER` | How many years passed since this plot was last visited. Null for a plot's very first visit (no prior visit to measure from). This is the time window over which growth happened: annual growth = `(DIA - PREVDIA) / REMPER` |
| `MEASYEAR` | The calendar year this plot visit took place |

### COND
One row per condition per plot visit. A single plot can contain more than one type of forest — for example, half the plot might be a young pine plantation and the other half older mixed forest. Each distinct patch is a "condition." This table describes the characteristics of each such patch.

| Column | Description |
|---|---|
| `PLT_CN` | Links this condition to its plot visit in the PLOT table |
| `CONDID` | A number (1, 2, 3...) identifying which condition within the plot this row describes. Together with `PLT_CN`, uniquely identifies a condition |
| `STDAGE` | How old the trees in this patch of forest are, in years — specifically, the average age of the dominant trees. A plantation harvested and replanted 20 years ago would have STDAGE=20. Null when the condition isn't forested (e.g. a road, pond, or cleared area that falls within the plot boundary) |

### How the tables join
```
TREE.PLT_CN           → PLOT.CN              (which plot visit did this tree come from?)
TREE.PLT_CN + CONDID  → COND.PLT_CN + CONDID (what type of forest patch is this tree in?)
```

---

## Data Loading

**Discovery: `REMPER` is in the PLOT table, not TREE**
Remeasurement period (years between current and previous diameter measurement) lives in PLOT, not TREE. The join must happen before computing annual growth.

**Decision: `usecols` to load only needed columns**
TREE has 199 columns, PLOT 64, COND 154. Loading everything took ~3.5 minutes. Specifying `usecols` with just the columns we need reduces load time to seconds.

Columns selected:
- **TREE**: `CN, PLT_CN, CONDID, SPCD, STATUSCD, DIA, PREVDIA, INVYR`
- **PLOT**: `CN, LAT, LON, ELEV, REMPER, MEASYEAR`
- **COND**: `PLT_CN, CONDID, STDAGE`

The ~380 other columns cover timber volume, biomass/carbon accounting, damage agents, regional FIA variants (suffixes like `_PNWRS`, `_SRS`, `_NERS`), and audit fields — none needed for diameter growth analysis.

---

## Species Selection

**Decision: Expanded to all four core southern pines (110, 111, 121, 131)**
Original README specified only loblolly (131) and shortleaf (110). EDA of species counts revealed species 111 and 121 also rank highly. Cross-referencing the FIA species code reference confirmed:
- 110: *Pinus echinata* (shortleaf pine) — ModRel=1
- 111: *Pinus elliottii* (slash pine) — ModRel=1 — originally misidentified as Virginia pine; it's a core southern pine
- 121: *Pinus palustris* (longleaf pine) — ModRel=1
- 131: *Pinus taeda* (loblolly pine) — ModRel=1

Species 611 (*Liquidambar styraciflua*, sweetgum) is a hardwood and excluded.
Species 111 was ranked above 110 in record count but was missing from the original scope — expanding the filter adds meaningful data.

**Discovery: INVYR distribution reflects FIA methodology shift ~2000**
Large periodic batches before 2000 (state-wide inventories every 5-10 years), then smaller annual counts (~70-80k/year) after FIA switched to an annual panel system. Each year measures ~1/5 of plots on rotation. This affects interpretation of `REMPER`.

**STATUSCD reference** (source: FIA Database User Guide NFI - https://research.fs.usda.gov/understory/forest-inventory-and-analysis-database-user-guide-nfi)
- `0` — Not presently in sample (remeasurement plots only). Tree incorrectly tallied at previous inventory, removed due to definition/procedural change, or on a nonsampled condition (hazardous/denied access). Excluded from analysis.
- `1` — Live tree. ← keep
- `2` — Dead tree. Excluded.
- `3` — Retired code (valid only for some periodic/annual transitions in specific FIA work units). Removed = cut/harvested by direct human activity. Excluded.

---

## Join Strategy

**Decision: Inner join on both PLOT and COND**
- Inner join TREE → PLOT: trees with no matching plot record have no REMPER and cannot contribute to growth analysis regardless. Dropping them is correct.
- Inner join PLOT result → COND: COND gives us CONDID (plot condition type) and STDAGE (stand age). Both are analytically useful for EDA — plotting growth by condition type and by stand age. Trees with no matching COND row lose both, so keeping them via left join adds nothing.
- STDAGE nulls (63k within matched COND rows) survive the inner join and will be filtered naturally in EDA cells that require stand age.

**Decision: Print row counts after every filter and join step**
Track exactly how many rows are lost at each stage. If the final dataset is too small for meaningful ICC/power analysis, revisit these decisions — e.g. relax the STDAGE null filter or reconsider which STATUSCD values to include.

---

## PREVDIA Nulls — Distribution and Recovery Potential

**Finding:** 433,465 out of 991,354 rows (~44%) in the filtered pine/live dataset have null PREVDIA — meaning no growth can be computed for nearly half the records.

**Distribution is not just early years:** Nulls are concentrated in the first periodic inventory cycles (1968: 31k, 1972: 58k) but persist consistently at 7–10k/year throughout 2000–2024. This is structural — in the annual panel system, each year ~1/5 of plots rotate in. A plot entering the rotation for the first time has no previous measurement regardless of the year.

**Potential recovery approach (not yet implemented):** For trees with consecutive visits where one row has null PREVDIA but an adjacent row has a valid DIA, the prior DIA could be forward-filled as PREVDIA. For example:
- 2002: PREVDIA=3, DIA=4
- 2003: PREVDIA=null, DIA=5 → could infer PREVDIA=4 from prior row
- 2004: PREVDIA=5, DIA=6

**Why this isn't straightforward:** To identify "the same physical tree" across visits we need either `PREV_TRE_CN` (FIA's direct tree-to-prior-record link) or the combination of subplot + tree number within subplot — none of which were loaded in our initial `usecols` selection. Also, FIA may have left PREVDIA null deliberately (newly tallied tree, broken link, or flagged prior measurement).

**Decision for now:** Drop null PREVDIA rows and proceed. If the resulting dataset (~558k rows) proves too small for reliable ICC estimation, revisit by loading `PREV_TRE_CN` and implementing tree-level linkage to recover recoverable nulls.

---

## Growth Computation & Distribution

**Decision: Hard drop negative growth, keep near-zero**
Negative annual growth (7,347 rows, 0.93%) is physically impossible for live trees (STATUSCD=1) — indicates measurement error. Hard dropped.

Near-zero growth (<0.05 in/yr) accounts for 28.2% of the dataset (221k rows). Investigation showed two causes:
- **REMPER artifact**: Trees with longer remeasurement gaps (median 8.2 yrs vs 6.3 yrs for faster-growing trees) have their absolute growth divided by a larger number, mechanically producing lower annual rates. The same 0.3-inch absolute growth over 8 years = 0.037 in/yr; over 5 years = 0.06 in/yr.
- **Real biology**: Near-zero trees are smaller on average (median DIA 6.5 vs 8.7 inches) — likely suppressed understory trees or younger trees not yet in peak growth. These are valid data points, not errors.

**Decision: No upper outlier threshold applied yet**
Distribution has no natural break — smooth right-skewed tail to max 4.7 in/yr. The 2 in/yr common heuristic is far too lenient (only 784 rows above 1 in/yr). IQR fence lands at 0.67 in/yr. Proceeding with full cleaned dataset for EDA; will revisit if ICC/variance estimates appear distorted.

---

## EDA Findings

### Growth by State
**Expected:** Some regional variation — GA, AL, SC have different soils, rainfall patterns, and species mixes. But all three are in the southeastern coastal plain, so large differences would be surprising.

**Found:** Nearly identical — AL 0.184, SC 0.161, GA 0.154 in/yr (medians within 0.03 of each other, overlapping IQR boxes). AL edges slightly higher, possibly reflecting soil or climate differences, but the three states are essentially comparable.

**Implication:** Safe to pool across states for ICC and variance estimation without state-level adjustments. State is not a major confound for an experimental design across this region.

---

### Growth by Species
**Expected:** Some species differences — pines vary in growth strategy. Plantation species (loblolly, slash) are bred and selected for fast growth. Ecological specialists (longleaf, shortleaf) prioritize stress tolerance over stem growth rate.

**Found:** Clear ranking — loblolly (0.185) > slash (0.145) > longleaf (0.136) > shortleaf (0.103). Loblolly is ~1.8x faster than shortleaf and is also the most variable grower (widest IQR). Loblolly dominates the dataset (~71% of records, 555k rows).

**Implication:** Species composition is a strong confound for any field trial. Two sites with different species mixes will have systematically different growth rates regardless of any treatment effect. A mycorrhizal inoculation trial should either control for species (same species at all sites) or include species as a covariate in the analysis. Loblolly dominance also means the overall variance structure is largely driven by loblolly behavior.

---

### Growth vs Stand Age
**Expected:** A classic sigmoid growth curve — slow early establishment phase, rapid juvenile growth in the middle years, then a tapering off as trees approach their mature size and canopy competition intensifies.

**Found:** Exactly this pattern. Growth is low at 0–10 years (0.077 in/yr) — seedlings establishing root systems — then jumps to peak at 10–30 years (0.20 in/yr), then declines steadily through maturity to ~0.07 in/yr at 110+ years. One anomaly: a bump at 90–100 years (0.149), likely noise from a small sample (7,681 records vs 120k+ in peak bins).

**Implication:** Stand age is a strong site-level covariate. Field trial sites with different age structures will have different baseline growth rates. Matching sites by age (or including STDAGE as a covariate) is important for isolating a treatment effect. The peak growth window of 10–30 years is also the most relevant target for a mycorrhizal inoculation study — this is when the intervention would have the most measurable impact.

---

### Growth vs Elevation
**Expected:** A declining trend with elevation — southern pines are warm-climate species. Higher elevations mean shorter growing seasons, colder winters, and often different soil types (rockier, shallower). We'd expect growth to drop as elevation increases.

**Found:** Consistent decline from 0–1400 ft (0.167 → 0.130 in/yr). Above 2000 ft, sample sizes collapse to hundreds of records and the signal becomes unreliable. 93% of data is below 800 ft — confirming that southern pines naturally concentrate in the coastal plain and piedmont, not the mountains.

**Implication:** Elevation is a meaningful site-level covariate, but practically speaking, a field trial in this region would almost certainly be sited below 800 ft where the species are abundant and data is reliable. The elevation effect is real but unlikely to be a practical design challenge if sites are chosen appropriately.

---

## Open Questions / To Revisit

- Upper outlier threshold: IQR fence (0.67 in/yr) is data-derived but flags 1.4% of rows. Revisit after ICC estimation — if variance estimates look inflated, cap the upper tail.
- Should outputs (ICC, variance estimates) be saved to `outputs/variance_params.json` for Notebook 2 to load cleanly, or referenced inline?
