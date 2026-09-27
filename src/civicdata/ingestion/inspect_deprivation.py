from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_PATH = PROJECT_ROOT / "data" / "raw" / "iod_2025_file_7.csv"


def inspect_iod() -> None:
    """Inspect the raw English Indices of Deprivation 2025 dataset."""

    df = pd.read_csv(DATA_PATH)

    print("\n=== IoD 2025 DATASET INSPECTION ===")
    print(f"Rows: {len(df):,}")
    print(f"Columns: {len(df.columns):,}")

    print("\n=== GEOGRAPHIC COVERAGE ===")
    print(f"Unique LSOAs: {df['LSOA code (2021)'].nunique():,}")
    print(
        "Unique Local Authorities: "
        f"{df['Local Authority District code (2024)'].nunique():,}"
    )

    print("\n=== DUPLICATE CHECK ===")
    duplicate_lsoas = df["LSOA code (2021)"].duplicated().sum()
    print(f"Duplicate LSOA codes: {duplicate_lsoas:,}")

    print("\n=== MISSING VALUES ===")
    missing = df.isna().sum()
    missing = missing[missing > 0].sort_values(ascending=False)

    if missing.empty:
        print("No missing values detected.")
    else:
        print(missing.to_string())

    print("\n=== COLUMN NAMES ===")
    for number, column in enumerate(df.columns, start=1):
        print(f"{number:02d}. {column}")

    print("\n=== IMD DECILE DISTRIBUTION ===")
    decile_column = (
        "Index of Multiple Deprivation (IMD) Decile "
        "(where 1 is most deprived 10% of LSOAs)"
    )

    print(
        df[decile_column]
        .value_counts()
        .sort_index()
        .to_string()
    )

    print("\n=== SAMPLE AUTHORITIES ===")
    authorities = (
        df[
            [
                "Local Authority District code (2024)",
                "Local Authority District name (2024)",
            ]
        ]
        .drop_duplicates()
        .sort_values("Local Authority District name (2024)")
        .head(10)
    )

    print(authorities.to_string(index=False))


if __name__ == "__main__":
    inspect_iod()