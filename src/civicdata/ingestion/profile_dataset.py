from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[3]
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"


def inspect_excel_file(file_path: Path) -> None:
    """Inspect the sheets and basic structure of an Excel dataset."""

    print(f"\nInspecting: {file_path.name}")
    print("=" * 60)

    excel_file = pd.ExcelFile(file_path)

    print("\nSheets:")

    for sheet in excel_file.sheet_names:
        print(f"  - {sheet}")

        df = pd.read_excel(file_path, sheet_name=sheet)

        print(f"    Rows: {len(df):,}")
        print(f"    Columns: {len(df.columns):,}")

        print("\n    Columns:")

        for column in df.columns:
            print(f"      - {column}")

        print()


if __name__ == "__main__":
    excel_files = list(RAW_DATA_DIR.glob("*.xls*"))

    if not excel_files:
        raise FileNotFoundError(
            "No Excel files found in data/raw/"
        )

    for file_path in excel_files:
        inspect_excel_file(file_path)