from __future__ import annotations

from pathlib import Path

import pandas as pd


# ---------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[3]

INPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "lof_lg_inform_report_ids.xlsx"
)

OUTPUT_DIR = PROJECT_ROOT / "data" / "processed"

OUTPUT_FILE = (
    OUTPUT_DIR
    / "lof_lg_inform_mapping.csv"
)

SHEET_NAME = "REPORT IDs"

SOURCE_COLUMNS = [
    "Section",
    "LOF Label",
    "MetricId",
    "LGI Label",
]


# ---------------------------------------------------------------------
# Load
# ---------------------------------------------------------------------

def load_mapping() -> pd.DataFrame:
    """Load the LG Inform LOF Report IDs workbook."""

    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            "LG Inform LOF mapping workbook was not found.\n"
            f"Expected location: {INPUT_FILE}\n\n"
            "Run download_lof_lg_inform_mapping.py first."
        )

    dataframe = pd.read_excel(
        INPUT_FILE,
        sheet_name=SHEET_NAME,
    )

    missing_columns = [
        column
        for column in SOURCE_COLUMNS
        if column not in dataframe.columns
    ]

    if missing_columns:
        raise RuntimeError(
            "LG Inform workbook structure has changed. "
            f"Missing columns: {missing_columns}"
        )

    dataframe = dataframe[SOURCE_COLUMNS].copy()

    dataframe = dataframe.dropna(
        how="all",
        subset=SOURCE_COLUMNS,
    )

    return dataframe


# ---------------------------------------------------------------------
# Standardisation
# ---------------------------------------------------------------------

def clean_text(value):
    """Trim text while preserving missing values."""

    if pd.isna(value):
        return pd.NA

    text = str(value).strip()

    if not text:
        return pd.NA

    return text


def standardise_mapping(dataframe: pd.DataFrame) -> pd.DataFrame:
    """
    Standardise the source mapping without altering its meaning.

    Original LG Inform fields are retained alongside CivicData-friendly
    column names.
    """

    result = dataframe.copy()

    # Preserve original source fields.
    result = result.rename(
        columns={
            "Section": "source_section",
            "LOF Label": "source_lof_label",
            "MetricId": "source_metric_id",
            "LGI Label": "source_lgi_label",
        }
    )

    text_columns = [
        "source_section",
        "source_lof_label",
        "source_lgi_label",
    ]

    for column in text_columns:
        result[column] = result[column].map(clean_text)

    # Preserve the original MetricId representation.
    result["source_metric_id"] = result["source_metric_id"].map(
        clean_text
    )

    # Create a validated numeric LG Inform Metric ID.
    numeric_metric_id = pd.to_numeric(
        result["source_metric_id"],
        errors="coerce",
    )

    result["lg_inform_metric_id"] = (
        numeric_metric_id.astype("Int64")
    )

    result["lg_inform_metric_title"] = (
        result["source_lgi_label"]
    )

    # Mapping status makes missing IDs explicit rather than dropping them.
    result["mapping_status"] = "mapped"

    result.loc[
        result["lg_inform_metric_id"].isna(),
        "mapping_status",
    ] = "no_numeric_metric_id"

    # Identify IDs used by more than one LOF mapping row.
    metric_counts = (
        result["lg_inform_metric_id"]
        .dropna()
        .value_counts()
    )

    repeated_ids = set(
        metric_counts[metric_counts > 1].index.tolist()
    )

    result["metric_id_reused"] = (
        result["lg_inform_metric_id"].isin(repeated_ids)
    )

    # Add stable source row number for traceability back to workbook.
    # +2 accounts for the Excel header row.
    result.insert(
        0,
        "source_excel_row",
        range(2, len(result) + 2),
    )

    return result


# ---------------------------------------------------------------------
# Validation and diagnostics
# ---------------------------------------------------------------------

def validate_mapping(dataframe: pd.DataFrame) -> None:
    """Validate and report the LG Inform LOF mapping."""

    total_rows = len(dataframe)

    valid_ids = dataframe["lg_inform_metric_id"].dropna()

    rows_with_ids = len(valid_ids)
    rows_without_ids = (
        dataframe["lg_inform_metric_id"].isna().sum()
    )

    unique_ids = valid_ids.nunique()

    repeated_id_values = (
        valid_ids.value_counts()
    )

    repeated_id_values = repeated_id_values[
        repeated_id_values > 1
    ]

    repeated_occurrences = (
        rows_with_ids - unique_ids
    )

    print("=" * 70)
    print("CivicData Intelligence")
    print("LG Inform LOF Mapping Parser")
    print("=" * 70)

    print("\nMapping summary")
    print("-" * 70)
    print(f"Total mapping rows: {total_rows:,}")
    print(f"Rows with valid Metric IDs: {rows_with_ids:,}")
    print(f"Rows without numeric Metric IDs: {rows_without_ids:,}")
    print(f"Unique LG Inform Metric IDs: {unique_ids:,}")
    print(
        "Repeated Metric ID occurrences: "
        f"{repeated_occurrences:,}"
    )

    # -------------------------------------------------------------
    # Rows without numeric IDs
    # -------------------------------------------------------------

    if rows_without_ids:
        print("\nRows without numeric Metric IDs")
        print("-" * 70)

        unresolved = dataframe.loc[
            dataframe["lg_inform_metric_id"].isna(),
            [
                "source_excel_row",
                "source_section",
                "source_lof_label",
                "source_metric_id",
                "source_lgi_label",
            ],
        ]

        print(
            unresolved.to_string(
                index=False
            )
        )

    # -------------------------------------------------------------
    # Reused Metric IDs
    # -------------------------------------------------------------

    if not repeated_id_values.empty:
        print("\nLG Inform Metric IDs used in multiple mapping rows")
        print("-" * 70)

        for metric_id, count in repeated_id_values.items():

            print(
                f"\nMetric ID {int(metric_id)} "
                f"appears {int(count)} times:"
            )

            rows = dataframe.loc[
                dataframe["lg_inform_metric_id"] == metric_id,
                [
                    "source_excel_row",
                    "source_section",
                    "source_lof_label",
                    "source_lgi_label",
                ],
            ]

            print(
                rows.to_string(
                    index=False
                )
            )

    # -------------------------------------------------------------
    # Structural validation
    # -------------------------------------------------------------

    if total_rows == 0:
        raise RuntimeError(
            "No LOF mapping rows were parsed."
        )

    if rows_with_ids == 0:
        raise RuntimeError(
            "No valid LG Inform Metric IDs were parsed."
        )

    print("\nValidation: PASS")


# ---------------------------------------------------------------------
# Save
# ---------------------------------------------------------------------

def save_mapping(dataframe: pd.DataFrame) -> None:
    """Save the processed mapping table."""

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    dataframe.to_csv(
        OUTPUT_FILE,
        index=False,
        encoding="utf-8",
    )

    print("\nOutput")
    print("-" * 70)
    print(f"Saved: {OUTPUT_FILE}")
    print(f"Rows written: {len(dataframe):,}")


# ---------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------

def main() -> None:

    source = load_mapping()

    mapping = standardise_mapping(source)

    validate_mapping(mapping)

    save_mapping(mapping)

    print("\n" + "=" * 70)
    print("LG Inform LOF mapping parsing completed successfully.")
    print("=" * 70)


if __name__ == "__main__":
    main()