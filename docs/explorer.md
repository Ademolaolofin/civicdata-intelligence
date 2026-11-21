# CivicData Explorer v0.2

Atlas — Lead Development Agent, CivicData Intelligence

Local prototype for [Issue #2](https://github.com/Ademolaolofin/civicdata-intelligence/issues/2).

## Run locally

Use the repository virtual environment with `requirements.txt` installed.
Place the following files in `data/processed` or pass their directory with
`--data-dir`. The app reads the snapshots at startup. Restart to pick up any
changes.

| Required snapshot | Source and local build |
| --- | --- |
| `mhclg_neighbour_relationships_2026.csv` | MHCLG 2026 Statistical Neighbours workbook, Statistical Neighbours sheet. Existing pipeline uses `ingestion/parse_neighbours.py` and `analysis/relationships.py`. The parser chooses the first raw workbook, so use the existing validated output or run that pipeline in an isolated copy with only the MHCLG workbook at the raw root. |
| `iod_2025_lad_official_summaries.csv` | English Indices of Deprivation 2025, corrected File 10 v2. Existing build is `ingestion/parse_iod_lad_summaries.py`. |
| `lof_dfe_eyfs_observations.csv` | DfE EYFS headline measures by child characteristics, version 1.0.1. See the EYFS reproduction steps below. |

To rebuild the EYFS snapshot, save the [DfE 1.0.1 CSV](https://api.education.gov.uk/statistics/v1/data-sets/019ac0fb-e082-7202-871f-439d6d036893/csv?dataSetVersion=1.0.1)
as `data/raw/dfe/eyfs_headline_measures_child_characteristics_2024_25.csv`.
With the MHCLG relationships and `lof_v01_metric_dimension.csv` in
`data/processed`, run:

```powershell
.\.venv\Scripts\python.exe src/civicdata/ingestion/build_lof_dfe_eyfs_observations.py
```

From the repository root in PowerShell:

```powershell
.\.venv\Scripts\python.exe src/civicdata/explorer.py
```

Open [http://127.0.0.1:8765/](http://127.0.0.1:8765/), choose an authority,
measure, academic year and comparator, then select **Apply filters**. Use Ctrl+C to
stop the server. If the port is in use, add `--port 8766`.

Python's standard library serves the HTML on loopback and pandas reads the
existing CSVs. This keeps the prototype independent of Streamlit,
databases and hosted infrastructure. No network requests are needed to
render the pages. Publisher links can be opened separately.

## Snapshot audit

| Dataset | Rows | Authority codes | Codes absent from the 317-authority MHCLG universe's coverage |
| --- | ---: | ---: | ---: |
| MHCLG directed relationships | 4,755 | 317 | 0 |
| IoD official district summaries | 296 | 296 | 21 |
| DfE EYFS, two metrics and four academic years | 2,512 | 317 | 0 across the full snapshot |
| Fingertips, five metrics and 54 distinct period labels | 13,979 | 315 | 2 |
| ONS healthy life expectancy, 12 overlapping three-year periods | 3,624 | 151 | 166 |

Every observed authority code in the audited outcome and deprivation
snapshots occurs in the MHCLG universe. Individual metrics and periods may
cover fewer places. Fingertips and ONS were audited for coverage and are
outside the prototype's two-measure view.

The audit matched all 4,755 directed authority, neighbour and rank
triples to the published workbook. SHA-256 fingerprints of the inputs
used for verification, in the same order as the required snapshot table:

```text
cdf4a75836b6c3065361f0d53658d62a2148290184f476625bbabf0f57444e93
2c7d257846d6c79953a8b08253519f52a5e9e0a149e99d590bc36f455ccd953f
e51a69d7834970e54fc5c3e51a96758554bde45b4d89676476f0526676087dc3
```

## How comparisons work

The table retains the broad MHCLG membership, direction and published
rank, including peers without an observation. It joins on exact authority
code, EYFS metric and academic year. Peer availability counts numeric
peer values even when the target is missing. Comparability requires
numeric values on both sides plus matching source geography level,
period type, unit and dataset version. A matching geography level does not establish boundary
equivalence. The app displays mixed-geography values with a status and
does not compute a pooled statistic.

The broad MHCLG Local Outcomes Framework model is the default.
Children’s Services can be selected independently when the optional DfE
snapshot is present. Adult Social Care remains unavailable.
[MHCLG comparator methodology](https://www.gov.uk/government/publications/local-outcomes-framework/local-government-outcomes-statistical-neighbours-model)

The deprivation profile uses the File 10 values and source LAD code,
including the documented code mapping where applicable. A missing
district record remains missing. EYFS shows both source geography levels
and distinguishes a blank value from an absent row and an observed zero.
The DfE derived data does not carry a reason for a blank value. The
dataset metadata is shown separately from observation provenance.
The loader checks geography levels, metric-specific units, academic year
labels and IDs, and one consistent DfE dataset provenance record. LG Inform
observation access remains unverified.

## DfE Children’s Services comparator

DfE published the rebuilt model on 28 May 2025. The workbook identifies it
as v1 and uses April 2023 English upper-tier geography. DfE used regression
and correlation screening and iterative weighting to select and weight
23 background variables, mainly from Census 2021. It ranked peers by
weighted Euclidean distance on standardised inputs. CivicData reads the
published results directly. [DfE release and update note](https://www.gov.uk/government/publications/local-authority-interactive-tool-lait) ·
[DfE technical report](https://assets.publishing.service.gov.uk/media/682e32faa599d03a16bff3d8/Children_s_services_statistical_neighbour_benchmarking_model_-_technical_report.pdf)

Save the [official workbook](https://assets.publishing.service.gov.uk/media/682dd813e9440506ee95390e/Children_s_services_statistical_neighbour_benchmarking_tool.xlsx)
as `data/raw/dfe/childrens_services_statistical_neighbours_2025_05.xlsx`.
Then run the builder and start or restart Explorer:

```powershell
.\.venv\Scripts\python.exe src/civicdata/ingestion/build_dfe_children_neighbours.py
.\.venv\Scripts\python.exe src/civicdata/explorer.py
```

The builder pins the workbook SHA-256
`8ede025998c03ae4aff25b5db8b3cc1a85887e2acef3b42f9109c9dc4b78a89a`.
It validates `ModelLong` against `ModelWide` and `LALookup`, and writes
`data/processed/dfe_children_neighbours_2025_05_v1.json`. The artifact
records publication date, version, geography vintage, source URLs,
checksum, ONS and DfE lookup identifiers, and all **1,530 directed
relationships for 153 authorities**. It preserves raw names, codes,
ranks and proximity labels, including original spacing. Proximity is
normalised only for validation across the two workbook tables.
The raw and processed files remain ignored by Git. With a custom
Explorer `--data-dir`, use the same path as the builder’s `--output-dir`.

Exactly 151 DfE codes match the current MHCLG authority universe.
The two exceptions are DfE’s pre-change Barnsley `E08000016` and
Sheffield `E08000019`. ONS identifies `E08000038` and `E08000039` as
their successors following a boundary change. Explorer retains the
original codes and ranks and withholds outcome joins for those
relationships. Selecting either successor under the DfE model shows
the geography difference. An authority absent from the DfE model for
other reasons shows an out-of-coverage state. [ONS Barnsley](https://www.ons.gov.uk/explore-local-statistics/areas/E08000038-barnsley) ·
[ONS Sheffield](https://www.ons.gov.uk/explore-local-statistics/areas/E08000039-sheffield)

DfE comparisons require exact codes and local authority-level EYFS
observations. The interface distinguishes peer availability and actual
comparability, including absent rows, blank target or peer values,
boundary differences and geography-level mismatches. The May 2025 peer
set is applied as context to the selected EYFS year, including earlier
years. Exact code and level matching cannot prove historic boundary
equivalence. The model supplies context for Children’s Services, and
does not define the EYFS measures or their source geography.

## Verification and next iteration

```powershell
.\.venv\Scripts\python.exe -m pytest -ra
```

The tests exercise snapshot validation, rank preservation, geography
checks, unavailable values, observed zero and rendered provenance. The
snapshot tests verify source coverage and compare all relationship ranks
and names with the original MHCLG workbook. Tests needing local files skip
with an explicit reason if those inputs are absent. The Hartlepool 2024/25
GLD example has 15 of 15 peers with numeric values and matching series
metadata. Sunderland is its published rank 1. Isles of Scilly shows
available FSM gap peer values and no valid comparison for its blank target.

The DfE tests cover the pinned workbook, all published relationships
and lookup codes, invalid artifacts, comparator selection, and coverage
and geography states. Workbook-backed tests skip with a reason when
the official local workbook is absent. The next step is independent
review of the v0.2 comparison and boundary handling.
