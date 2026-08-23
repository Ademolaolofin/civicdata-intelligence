from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[3]
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DATA_DIR = PROJECT_ROOT / "data" / "processed"


def load_neighbour_data() -> pd.DataFrame:
    """Load the MHCLG Statistical Neighbours table."""

    files = list(RAW_DATA_DIR.glob("*.xls*"))

    if not files:
        raise FileNotFoundError(
            "No Excel dataset found in data/raw/"
        )

    file_path = files[0]

    df = pd.read_excel(
        file_path,
        sheet_name="Statistical Neighbours",
        header=10,
    )

    return df


def clean_neighbour_data(df: pd.DataFrame) -> pd.DataFrame:
    """Clean and standardise the Statistical Neighbours table."""

    # Remove completely empty rows and columns.
    df = df.dropna(how="all")
    df = df.dropna(axis=1, how="all")

    # Remove accidental whitespace from column names.
    df.columns = [
        str(column).strip()
        for column in df.columns
    ]

    # Rename the first two columns.
    columns = list(df.columns)

    columns[0] = "local_authority_code"
    columns[1] = "local_authority_name"

    df.columns = columns

    # Remove rows without a local authority code.
    df = df[
        df["local_authority_code"].notna()
    ].copy()

    # Convert authority codes and names to strings.
    df["local_authority_code"] = (
        df["local_authority_code"]
        .astype(str)
        .str.strip()
    )

    df["local_authority_name"] = (
        df["local_authority_name"]
        .astype(str)
        .str.strip()
    )

    return df


def save_processed_data(df: pd.DataFrame) -> Path:
    """Save the cleaned dataset as CSV."""

    PROCESSED_DATA_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path = (
        PROCESSED_DATA_DIR
        / "mhclg_statistical_neighbours_2026.csv"
    )

    df.to_csv(
        output_path,
        index=False,
    )

    return output_path


def main() -> None:
    print("CivicData Intelligence")
    print("MHCLG Statistical Neighbours Parser")
    print("=" * 60)

    raw_df = load_neighbour_data()

    print(f"Raw records: {len(raw_df):,}")
    print(f"Raw columns: {len(raw_df.columns):,}")

    clean_df = clean_neighbour_data(raw_df)

    print(f"Clean records: {len(clean_df):,}")
    print(f"Clean columns: {len(clean_df.columns):,}")

    output_path = save_processed_data(clean_df)

    print(f"\nProcessed dataset saved to:")
    print(output_path)


if __name__ == "__main__":
    main()