from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[3]
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"


def inspect_neighbours() -> None:
    """Inspect the raw Statistical Neighbours worksheet."""

    files = list(RAW_DATA_DIR.glob("*.xls*"))

    if not files:
        raise FileNotFoundError(
            "No Excel dataset found in data/raw/"
        )

    file_path = files[0]

    print(f"Reading: {file_path.name}")
    print("=" * 70)

    # Read without assuming that the first row is the header.
    df = pd.read_excel(
        file_path,
        sheet_name="Statistical Neighbours",
        header=None,
    )

    print(f"\nRaw shape: {df.shape}")

    print("\nFirst 25 rows:")
    print(df.head(25).to_string(index=True, header=False))


if __name__ == "__main__":
    inspect_neighbours()