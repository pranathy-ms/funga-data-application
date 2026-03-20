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

## Open Questions / To Revisit

- Outlier handling for growth: flag with `is_outlier` column or hard drop? (leaning toward flag so EDA can show the distribution before dropping)
- What threshold makes sense for "unrealistic" annual diameter growth in southern pine? (common heuristic: >2 inches/year is suspicious)
- Should outputs (ICC, variance estimates) be saved to `outputs/variance_params.json` for Notebook 2 to load cleanly, or referenced inline?
