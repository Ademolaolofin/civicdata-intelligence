# CivicData Explorer v0.1

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
| `lof_dfe_eyfs_observations.csv` | DfE EYFS headline measures by child characteristics, version 1.0.1. See [EYFS reproduction steps](lg-inform-eyfs-feasibility.md#reproduce-the-checks). |

From the repository root in PowerShell:

```powershell
.\.venv\Scripts\python.exe src/civicdata/explorer.py
```

Open [http://127.0.0.1:8765/](http://127.0.0.1:8765/), choose an authority,
measure and academic year, then select **Apply filters**. Use Ctrl+C to
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
code, EYFS metric and academic year. The coverage count requires a numeric
peer value and matching source geography level, period type, unit and
dataset version. A matching geography level does not establish boundary
equivalence. The app displays mixed-geography values with a status and
does not compute a pooled statistic.

Children's Services and Adult Social Care comparator sets have separate
availability labels. The local MHCLG list is a broad contextual model.
The workbook supplies no service-specific relationship lists, so those
sets are unavailable in the app. [MHCLG comparator methodology](https://www.gov.uk/government/publications/local-outcomes-framework/local-government-outcomes-statistical-neighbours-model)

The deprivation profile uses the File 10 values and source LAD code,
including the documented code mapping where applicable. A missing
district record remains missing. EYFS shows both source geography levels
and distinguishes a blank value from an absent row and an observed zero.
The DfE derived data does not carry a reason for a blank value. LG Inform
observation access remains unverified. [LG Inform feasibility report](lg-inform-eyfs-feasibility.md)

## Verification and next iteration

```powershell
.\.venv\Scripts\python.exe -m pytest -ra
```

The tests exercise snapshot validation, rank preservation, geography
checks, unavailable values, observed zero and rendered provenance. The
Hartlepool 2024/25 GLD example has 15 of 15 peers with numeric
values and matching series metadata. Sunderland is its published rank 1.

The next iteration is to ingest a versioned, official service-specific
relationship snapshot, starting with the DfE Children's Services model,
and add a separate comparison view once its authority coverage and ranks
are verified.
