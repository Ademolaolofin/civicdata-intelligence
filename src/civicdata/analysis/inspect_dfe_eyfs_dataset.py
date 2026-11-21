from pathlib import Path
import io

import pandas as pd
import requests


PROJECT_ROOT = Path(__file__).resolve().parents[3]

RAW_DIR = PROJECT_ROOT / "data" / "raw" / "dfe"

OUTPUT_PATH = (
    RAW_DIR
    / "eyfs_headline_measures_child_characteristics_2024_25.csv"
)

SOURCE_URL = (
    "https://api.education.gov.uk/statistics/v1/data-sets/"
    "019ac0fb-e082-7202-871f-439d6d036893/"
    "csv?dataSetVersion=1.0.1"
)


def download_dataset():
    print("Downloading official DfE EYFS dataset...")
    print("=" * 75)

    response = requests.get(
        SOURCE_URL,
        timeout=180,
    )

    response.raise_for_status()

    content_type = response.headers.get(
        "content-type",
        "",
    )

    print(f"HTTP status  : {response.status_code}")
    print(f"Content type : {content_type}")
    print(f"Bytes        : {len(response.content):,}")

    if len(response.content) < 1_000:
        raise ValueError(
            "DfE response is unexpectedly small."
        )

    RAW_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    OUTPUT_PATH.write_bytes(
        response.content
    )

    print(f"Saved        : {OUTPUT_PATH}")

    return response.content


def inspect_dataset(content):
    print()
    print("Inspecting DfE dataset...")
    print("=" * 75)

    df = pd.read_csv(
        io.BytesIO(content),
        low_memory=False,
    )

    print(f"Rows         : {len(df):,}")
    print(f"Columns      : {len(df.columns):,}")

    print()
    print("COLUMN NAMES")
    print("=" * 75)

    for number, column in enumerate(
        df.columns,
        start=1,
    ):
        print(f"{number:>2}. {column}")

    print()
    print("FIRST FIVE ROWS")
    print("=" * 75)

    print(
        df.head(5).to_string(
            index=False
        )
    )

    print()
    print("POTENTIALLY RELEVANT COLUMNS")
    print("=" * 75)

    keywords = [
        "fsm",
        "free",
        "meal",
        "character",
        "geographic",
        "geography",
        "area",
        "local",
        "level",
        "development",
        "indicator",
        "time",
        "year",
    ]

    relevant_columns = [
        column
        for column in df.columns
        if any(
            keyword in column.lower()
            for keyword in keywords
        )
    ]

    for column in relevant_columns:
        print()
        print(f"COLUMN: {column}")

        values = (
            df[column]
            .dropna()
            .astype(str)
            .drop_duplicates()
        )

        print(
            f"Unique values: {len(values):,}"
        )

        for value in values.head(40):
            print(f"  {value}")

        if len(values) > 40:
            print(
                f"  ... {len(values) - 40:,} more"
            )

    print()
    print("Inspection complete.")


def main():
    content = download_dataset()
    inspect_dataset(content)


if __name__ == "__main__":
    main()
