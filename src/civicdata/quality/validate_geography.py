from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[3]

IOD_PATH = PROJECT_ROOT / "data" / "raw" / "iod_2025_file_7.csv"

NEIGHBOURS_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "mhclg_neighbour_relationships_2026.csv"
)


def validate_geography() -> None:
    """Compare Local Authority coverage between IoD and MHCLG datasets."""

    iod = pd.read_csv(IOD_PATH)
    neighbours = pd.read_csv(NEIGHBOURS_PATH)

    print("\n=== CIVICDATA GEOGRAPHY VALIDATION ===")

    print("\n=== MHCLG RELATIONSHIP COLUMNS ===")
    for column in neighbours.columns:
        print(column)

    iod_authorities = (
        iod[
            [
                "Local Authority District code (2024)",
                "Local Authority District name (2024)",
            ]
        ]
        .drop_duplicates()
        .rename(
            columns={
                "Local Authority District code (2024)": "authority_code",
                "Local Authority District name (2024)": "authority_name",
            }
        )
    )

    print("\n=== IOD COVERAGE ===")
    print(f"IoD authorities: {len(iod_authorities):,}")

    # Identify authority-code columns in the MHCLG relationship table.
    code_columns = [
        column
        for column in neighbours.columns
        if "code" in column.lower()
    ]

    print("\n=== DETECTED MHCLG CODE COLUMNS ===")
    for column in code_columns:
        print(column)

    if not code_columns:
        raise ValueError(
            "No authority code columns were detected in the "
            "MHCLG relationship dataset."
        )

    mhclg_codes = set()

    for column in code_columns:
        values = (
            neighbours[column]
            .dropna()
            .astype(str)
            .str.strip()
        )

        mhclg_codes.update(
            value
            for value in values
            if value.startswith("E")
        )

    iod_codes = set(iod_authorities["authority_code"])

    shared_codes = iod_codes & mhclg_codes
    iod_only = iod_codes - mhclg_codes
    mhclg_only = mhclg_codes - iod_codes

    print("\n=== GEOGRAPHIC OVERLAP ===")
    print(f"Unique MHCLG authority codes: {len(mhclg_codes):,}")
    print(f"Unique IoD authority codes: {len(iod_codes):,}")
    print(f"Shared authority codes: {len(shared_codes):,}")
    print(f"IoD only: {len(iod_only):,}")
    print(f"MHCLG only: {len(mhclg_only):,}")

    print("\n=== IOD AUTHORITIES NOT FOUND IN MHCLG ===")

    iod_only_details = (
        iod_authorities[
            iod_authorities["authority_code"].isin(iod_only)
        ]
        .sort_values("authority_name")
    )

    if iod_only_details.empty:
        print("None")
    else:
        print(iod_only_details.to_string(index=False))

    print("\n=== MHCLG CODES NOT FOUND IN IOD ===")

    if not mhclg_only:
        print("None")
    else:
        for code in sorted(mhclg_only):
            print(code)


if __name__ == "__main__":
    validate_geography()