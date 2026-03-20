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

## Open Questions / To Revisit

- Outlier handling for growth: flag with `is_outlier` column or hard drop? (leaning toward flag so EDA can show the distribution before dropping)
- What threshold makes sense for "unrealistic" annual diameter growth in southern pine? (common heuristic: >2 inches/year is suspicious)
- Should outputs (ICC, variance estimates) be saved to `outputs/variance_params.json` for Notebook 2 to load cleanly, or referenced inline?
