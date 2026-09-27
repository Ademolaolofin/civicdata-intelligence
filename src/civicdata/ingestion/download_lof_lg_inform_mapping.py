from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests


# ---------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------

SOURCE_URL = "https://e-sd.org/ODNyD/"

PROJECT_ROOT = Path(__file__).resolve().parents[3]
RAW_DIR = PROJECT_ROOT / "data" / "raw"

OUTPUT_FILE = RAW_DIR / "lof_lg_inform_report_ids.xlsx"

EXPECTED_SHEET = "REPORT IDs"

EXPECTED_COLUMNS = {
    "Section",
    "LOF Label",
    "MetricId",
    "LGI Label",
}


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------

def calculate_sha256(file_path: Path) -> str:
    """Calculate SHA-256 hash for source provenance and change detection."""

    sha256 = hashlib.sha256()

    with file_path.open("rb") as file:
        for chunk in iter(lambda: file.read(8192), b""):
            sha256.update(chunk)

    return sha256.hexdigest()


# ---------------------------------------------------------------------
# Download
# ---------------------------------------------------------------------

def download_workbook() -> str:
    """Download the latest LG Inform LOF Report IDs workbook."""

    RAW_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("CivicData Intelligence")
    print("LG Inform LOF Report IDs Downloader")
    print("=" * 70)

    print(f"\nSource URL:\n{SOURCE_URL}")
    print(f"\nDestination:\n{OUTPUT_FILE}")

    response = requests.get(
        SOURCE_URL,
        timeout=60,
        allow_redirects=True,
        headers={
            "User-Agent": (
                "CivicData-Intelligence/0.1 "
                "(public-sector data research project)"
            )
        },
    )

    response.raise_for_status()

    if not response.content:
        raise RuntimeError("Downloaded file is empty.")

    OUTPUT_FILE.write_bytes(response.content)

    print("\nDownload complete.")
    print(f"Bytes downloaded: {len(response.content):,}")
    print(f"Resolved URL: {response.url}")

    return response.url


# ---------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------

def validate_workbook() -> tuple[int, int]:
    """Validate that the downloaded workbook has the expected structure."""

    print("\nValidating workbook...")

    try:
        workbook = pd.ExcelFile(OUTPUT_FILE)
    except Exception as exc:
        raise RuntimeError(
            "Downloaded content could not be opened as an Excel workbook."
        ) from exc

    print(f"Workbook sheets: {workbook.sheet_names}")

    if EXPECTED_SHEET not in workbook.sheet_names:
        raise RuntimeError(
            f"Expected sheet '{EXPECTED_SHEET}' was not found. "
            f"Available sheets: {workbook.sheet_names}"
        )

    dataframe = pd.read_excel(
        OUTPUT_FILE,
        sheet_name=EXPECTED_SHEET,
    )

    actual_columns = set(dataframe.columns)
    missing_columns = EXPECTED_COLUMNS - actual_columns

    if missing_columns:
        raise RuntimeError(
            "LG Inform workbook structure has changed. "
            f"Missing expected columns: {sorted(missing_columns)}"
        )

    relevant = dataframe[
        ["Section", "LOF Label", "MetricId", "LGI Label"]
    ].copy()

    relevant = relevant.dropna(
        how="all",
        subset=["Section", "LOF Label", "MetricId", "LGI Label"],
    )

    metric_ids = pd.to_numeric(
        relevant["MetricId"],
        errors="coerce",
    )

    valid_metric_ids = metric_ids.dropna().astype(int)

    if valid_metric_ids.empty:
        raise RuntimeError(
            "No valid LG Inform Metric IDs were found in the workbook."
        )

    mapping_rows = len(relevant)
    unique_metric_ids = valid_metric_ids.nunique()
    repeated_metric_ids = valid_metric_ids.duplicated().sum()

    print(f"Mapping rows: {mapping_rows:,}")
    print(f"Rows with valid Metric IDs: {len(valid_metric_ids):,}")
    print(f"Unique Metric IDs: {unique_metric_ids:,}")
    print(f"Repeated Metric ID occurrences: {repeated_metric_ids:,}")

    print("\nValidation: PASS")

    return mapping_rows, unique_metric_ids


# ---------------------------------------------------------------------
# Provenance
# ---------------------------------------------------------------------

def report_provenance(resolved_url: str) -> None:
    """Print provenance information for the downloaded source."""

    sha256 = calculate_sha256(OUTPUT_FILE)
    retrieved_at = datetime.now(timezone.utc).isoformat()

    print("\nSource provenance")
    print("-" * 70)
    print("Source organisation: LG Inform / Local Government Association")
    print(f"Source URL: {SOURCE_URL}")
    print(f"Resolved download URL: {resolved_url}")
    print(f"Retrieved UTC: {retrieved_at}")
    print(f"Local file: {OUTPUT_FILE}")
    print(f"SHA-256: {sha256}")


# ---------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------

def main() -> None:
    resolved_url = download_workbook()

    validate_workbook()

    report_provenance(resolved_url)

    print("\n" + "=" * 70)
    print("LG Inform LOF mapping download completed successfully.")
    print("=" * 70)


if __name__ == "__main__":
    main()