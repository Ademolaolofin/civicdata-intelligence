"""
Enrich Local Outcomes Framework metrics with authoritative LG Inform /
ESD Standards metadata.

The script:

1. Reads the CivicData LG Inform LOF mapping.
2. Identifies unique direct numeric LG Inform Metric IDs.
3. Downloads the public ESD Standards mapping CSV for each metric.
4. Extracts one metric-level metadata record per Metric ID.
5. Extracts period-type mappings.
6. Preserves the source polarity wording.
7. Standardises polarity into a controlled CivicData field.
8. Records provenance and retrieval status.
9. Produces a review queue for failed or unusual records.

Public source pattern:
https://standards.esd.org.uk/csv/mappings?uri=metricType/{METRIC_ID}
"""

from __future__ import annotations

import argparse
import io
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import pandas as pd
import requests


PROJECT_ROOT = Path(__file__).resolve().parents[3]

DEFAULT_MAPPING_PATH = (
    PROJECT_ROOT / "data" / "processed" / "lof_lg_inform_mapping.csv"
)

DEFAULT_OUTPUT_PATH = (
    PROJECT_ROOT / "data" / "processed" / "lof_lg_inform_metadata.csv"
)

DEFAULT_REVIEW_PATH = (
    PROJECT_ROOT / "data" / "processed" / "lof_lg_inform_metadata_review.csv"
)

ESD_STANDARDS_URL = (
    "https://standards.esd.org.uk/csv/mappings?uri=metricType/{metric_id}"
)

EXPECTED_UNIQUE_DIRECT_METRICS = 145

REQUEST_TIMEOUT = 60
MAX_RETRIES = 3
REQUEST_DELAY_SECONDS = 0.35

USER_AGENT = (
    "CivicData-Intelligence/0.1 "
    "(public-sector data integration research project)"
)


def normalise_column_name(value: object) -> str:
    """Normalise a source column name for robust matching."""
    text = str(value).strip().lower()

    replacements = {
        " ": "_",
        "-": "_",
        "/": "_",
        "\\": "_",
        "(": "",
        ")": "",
        ":": "",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    while "__" in text:
        text = text.replace("__", "_")

    return text.strip("_")


def clean_value(value: object) -> Optional[str]:
    """Return a clean string or None for empty/NaN values."""
    if value is None:
        return None

    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass

    text = str(value).strip()

    if not text:
        return None

    if text.lower() in {"nan", "none", "null"}:
        return None

    return text


def first_non_empty(
    dataframe: pd.DataFrame,
    candidate_columns: list[str],
) -> Optional[str]:
    """Return the first non-empty value from candidate columns."""
    for column in candidate_columns:
        if column not in dataframe.columns:
            continue

        for value in dataframe[column]:
            cleaned = clean_value(value)
            if cleaned is not None:
                return cleaned

    return None


def find_column(
    dataframe: pd.DataFrame,
    candidates: list[str],
) -> Optional[str]:
    """Find the first matching normalised column."""
    available = set(dataframe.columns)

    for candidate in candidates:
        if candidate in available:
            return candidate

    return None


def standardise_polarity(
    polarity_original: Optional[str],
) -> str:
    """
    Standardise authoritative ESD Standards polarity wording.

    The original source wording is preserved separately. This function
    tolerates differences in capitalisation, punctuation, whitespace and
    minor wording variations, but does not infer a direction when the
    source wording is genuinely unclear.
    """
    if polarity_original is None:
        return "unresolved"

    import re

    value = polarity_original.casefold().strip()

    # Normalise punctuation and repeated whitespace.
    value = re.sub(r"[^a-z0-9]+", " ", value)
    value = re.sub(r"\s+", " ", value).strip()

    # Explicitly non-directional source values.
    no_direction_patterns = [
        r"\bnot applicable\b",
        r"\bno polarity\b",
        r"\bno direction\b",
        r"\bneither high nor low\b",
        r"\bneither higher nor lower\b",
    ]

    if any(
        re.search(pattern, value)
        for pattern in no_direction_patterns
    ):
        return "no_direction"

    # Explicit favourable direction: higher values.
    high_good_patterns = [
        r"\b(?:a )?high(?:er)?(?: value)?(?: is)? good\b",
        r"\b(?:a )?high(?:er)?(?: value)?(?: is)? better\b",
    ]

    if any(
        re.search(pattern, value)
        for pattern in high_good_patterns
    ):
        return "high_is_good"

    # Explicit favourable direction: lower values.
    low_good_patterns = [
        r"\b(?:a )?low(?:er)?(?: value)?(?: is)? good\b",
        r"\b(?:a )?low(?:er)?(?: value)?(?: is)? better\b",
    ]

    if any(
        re.search(pattern, value)
        for pattern in low_good_patterns
    ):
        return "low_is_good"

    # Never guess unfamiliar authoritative wording.
    return "unresolved"


def load_direct_metric_ids(mapping_path: Path) -> list[int]:
    """Load unique numeric LG Inform Metric IDs from the LOF mapping."""
    if not mapping_path.exists():
        raise FileNotFoundError(
            f"LG Inform mapping file not found: {mapping_path}"
        )

    mapping = pd.read_csv(mapping_path)

    possible_columns = [
        "metric_id",
        "metricid",
        "lg_inform_metric_id",
        "source_metric_id",
        "numeric_metric_id",
    ]

    normalised_lookup = {
        normalise_column_name(column): column
        for column in mapping.columns
    }

    metric_column = None

    for candidate in possible_columns:
        if candidate in normalised_lookup:
            metric_column = normalised_lookup[candidate]
            break

    if metric_column is None:
        # Fall back to any column containing "metric" and "id".
        for normalised, original in normalised_lookup.items():
            if "metric" in normalised and "id" in normalised:
                numeric_test = pd.to_numeric(
                    mapping[original],
                    errors="coerce",
                )

                if numeric_test.notna().sum() > 0:
                    metric_column = original
                    break

    if metric_column is None:
        raise ValueError(
            "Could not identify the numeric LG Inform Metric ID column.\n"
            f"Available columns: {list(mapping.columns)}"
        )

    numeric_ids = pd.to_numeric(
        mapping[metric_column],
        errors="coerce",
    ).dropna()

    metric_ids = sorted(
        numeric_ids.astype(int).unique().tolist()
    )

    return metric_ids


def download_metric_csv(
    session: requests.Session,
    metric_id: int,
) -> tuple[pd.DataFrame, str, str]:
    """
    Download one ESD Standards metric mappings CSV.

    Returns:
        dataframe
        resolved_url
        retrieved_at_utc
    """
    url = ESD_STANDARDS_URL.format(metric_id=metric_id)

    last_exception: Optional[Exception] = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = session.get(
                url,
                timeout=REQUEST_TIMEOUT,
            )

            response.raise_for_status()

            retrieved_at = datetime.now(timezone.utc).isoformat()

            dataframe = pd.read_csv(
                io.StringIO(response.text),
                dtype=str,
                keep_default_na=False,
            )

            if dataframe.empty:
                raise ValueError(
                    f"Metric {metric_id} returned an empty CSV."
                )

            dataframe.columns = [
                normalise_column_name(column)
                for column in dataframe.columns
            ]

            return dataframe, response.url, retrieved_at

        except (
            requests.RequestException,
            pd.errors.ParserError,
            UnicodeDecodeError,
            ValueError,
        ) as exc:
            last_exception = exc

            if attempt < MAX_RETRIES:
                wait_seconds = attempt * 2
                time.sleep(wait_seconds)

    raise RuntimeError(
        f"Failed to retrieve metric {metric_id} after "
        f"{MAX_RETRIES} attempts: {last_exception}"
    )


def extract_period_types(dataframe: pd.DataFrame) -> list[str]:
    """Extract mapped period types from an ESD Standards mappings CSV."""
    mapping_type_column = find_column(
        dataframe,
        [
            "mapped_type",
            "mapping_type",
            "mappedtype",
        ],
    )

    mapped_label_column = find_column(
        dataframe,
        [
            "mapped_label",
            "mapping_label",
            "mappedlabel",
        ],
    )

    if (
        mapping_type_column is None
        or mapped_label_column is None
    ):
        return []

    period_rows = dataframe[
        dataframe[mapping_type_column]
        .astype(str)
        .str.strip()
        .str.casefold()
        .eq("period")
    ]

    values: list[str] = []

    for value in period_rows[mapped_label_column]:
        cleaned = clean_value(value)

        if cleaned and cleaned not in values:
            values.append(cleaned)

    return values


def extract_metric_metadata(
    metric_id: int,
    dataframe: pd.DataFrame,
    resolved_url: str,
    retrieved_at: str,
) -> dict:
    """Collapse repeated mapping rows into one metric metadata record."""

    title = first_non_empty(
        dataframe,
        [
            "label",
            "metric_label",
            "title",
            "name",
        ],
    )

    short_label = first_non_empty(
        dataframe,
        [
            "short_label",
            "shortlabel",
        ],
    )

    description = first_non_empty(
        dataframe,
        [
            "description",
            "help_text",
            "helptext",
            "definition",
        ],
    )

    status = first_non_empty(
        dataframe,
        [
            "status",
        ],
    )

    modified = first_non_empty(
        dataframe,
        [
            "modified",
            "modified_date",
            "last_modified",
        ],
    )

    output_precision = first_non_empty(
        dataframe,
        [
            "output_precision",
            "outputprecision",
        ],
    )

    polarity_original = first_non_empty(
        dataframe,
        [
            "polarity",
            "polarity_label",
            "polaritylabel",
        ],
    )

    measure = first_non_empty(
        dataframe,
        [
            "measure",
            "measure_label",
            "measurelabel",
            "unit",
            "unit_of_measure",
        ],
    )

    dataset = first_non_empty(
        dataframe,
        [
            "dataset",
            "dataset_label",
            "datasetlabel",
        ],
    )

    collection = first_non_empty(
        dataframe,
        [
            "collection",
            "collection_label",
            "collectionlabel",
        ],
    )

    source = first_non_empty(
        dataframe,
        [
            "source",
            "source_label",
            "sourcelabel",
        ],
    )

    discontinued = first_non_empty(
        dataframe,
        [
            "discontinued",
        ],
    )

    uri = first_non_empty(
        dataframe,
        [
            "uri",
            "identifier_uri",
        ],
    )

    period_types = extract_period_types(dataframe)

    if len(period_types) == 1:
        period_type = period_types[0]
        period_mapping_status = "single_period_type"

    elif len(period_types) > 1:
        period_type = " | ".join(period_types)
        period_mapping_status = "multiple_period_types"

    else:
        period_type = None
        period_mapping_status = "period_type_not_found"

    polarity_standardised = standardise_polarity(
        polarity_original
    )

    if polarity_original is None:
        polarity_status = "missing_from_esd_standards"
    elif polarity_standardised == "unresolved":
        polarity_status = "unrecognised_source_wording"
    else:
        polarity_status = "verified_esd_standards"

    metadata_status = "retrieved"

    return {
        "lg_inform_metric_id": metric_id,
        "lg_inform_metric_title": title,
        "short_label": short_label,
        "description": description,
        "status": status,
        "modified": modified,
        "output_precision": output_precision,
        "polarity_original": polarity_original,
        "polarity_standardised": polarity_standardised,
        "polarity_status": polarity_status,
        "measure": measure,
        "dataset": dataset,
        "collection": collection,
        "source": source,
        "discontinued": discontinued,
        "period_type": period_type,
        "period_mapping_status": period_mapping_status,
        "metric_uri": uri,
        "metadata_source": "ESD Standards",
        "metadata_source_url": resolved_url,
        "metadata_retrieved_at_utc": retrieved_at,
        "metadata_status": metadata_status,
    }


def build_failure_record(
    metric_id: int,
    error: Exception,
) -> dict:
    """Create a metadata row when retrieval fails."""
    return {
        "lg_inform_metric_id": metric_id,
        "lg_inform_metric_title": None,
        "short_label": None,
        "description": None,
        "status": None,
        "modified": None,
        "output_precision": None,
        "polarity_original": None,
        "polarity_standardised": "unresolved",
        "polarity_status": "retrieval_failed",
        "measure": None,
        "dataset": None,
        "collection": None,
        "source": None,
        "discontinued": None,
        "period_type": None,
        "period_mapping_status": "retrieval_failed",
        "metric_uri": None,
        "metadata_source": "ESD Standards",
        "metadata_source_url": ESD_STANDARDS_URL.format(
            metric_id=metric_id
        ),
        "metadata_retrieved_at_utc": None,
        "metadata_status": "retrieval_failed",
        "error_message": str(error),
    }


def needs_review(row: pd.Series) -> bool:
    """Determine whether a metadata record needs manual review."""
    return any(
        [
            row.get("metadata_status") != "retrieved",
            row.get("polarity_standardised") == "unresolved",
            row.get("period_mapping_status")
            in {
                "multiple_period_types",
                "period_type_not_found",
                "retrieval_failed",
            },
        ]
    )


def print_coverage(
    metadata: pd.DataFrame,
    expected_count: int,
) -> None:
    """Print concise validation and metadata coverage statistics."""
    total = len(metadata)

    retrieved = (
        metadata["metadata_status"]
        .eq("retrieved")
        .sum()
    )

    failed = total - retrieved

    polarity_present = (
        metadata["polarity_original"]
        .notna()
        .sum()
    )

    polarity_verified = (
        metadata["polarity_status"]
        .eq("verified_esd_standards")
        .sum()
    )

    polarity_unresolved = (
        metadata["polarity_standardised"]
        .eq("unresolved")
        .sum()
    )

    period_present = (
        metadata["period_type"]
        .notna()
        .sum()
    )

    source_present = (
        metadata["source"]
        .notna()
        .sum()
    )

    collection_present = (
        metadata["collection"]
        .notna()
        .sum()
    )

    measure_present = (
        metadata["measure"]
        .notna()
        .sum()
    )

    print()
    print("LG INFORM / ESD STANDARDS METADATA VALIDATION")
    print("=" * 52)
    print(f"Expected unique direct metrics : {expected_count}")
    print(f"Metadata rows produced         : {total}")
    print(f"Successfully retrieved         : {retrieved}")
    print(f"Retrieval failures             : {failed}")
    print()
    print(f"Polarity present               : {polarity_present}")
    print(f"Polarity verified              : {polarity_verified}")
    print(f"Polarity unresolved            : {polarity_unresolved}")
    print(f"Period type present            : {period_present}")
    print(f"Source present                 : {source_present}")
    print(f"Collection present             : {collection_present}")
    print(f"Measure present                : {measure_present}")

    duplicate_ids = metadata[
        "lg_inform_metric_id"
    ].duplicated().sum()

    print(f"Duplicate Metric IDs           : {duplicate_ids}")

    if (
        total == expected_count
        and duplicate_ids == 0
        and failed == 0
    ):
        print()
        print("Core retrieval validation: PASS")
    else:
        print()
        print("Core retrieval validation: REVIEW REQUIRED")


def run(
    mapping_path: Path,
    output_path: Path,
    review_path: Path,
    limit: Optional[int] = None,
    metric_id: Optional[int] = None,
) -> None:
    """Run metadata enrichment."""

    metric_ids = load_direct_metric_ids(mapping_path)

    print("LG Inform / ESD Standards metadata enrichment")
    print("=" * 52)
    print(f"Mapping file: {mapping_path}")
    print(f"Unique direct Metric IDs found: {len(metric_ids)}")

    if len(metric_ids) != EXPECTED_UNIQUE_DIRECT_METRICS:
        print(
            "WARNING: expected "
            f"{EXPECTED_UNIQUE_DIRECT_METRICS} unique direct metrics "
            f"but found {len(metric_ids)}."
        )

    if metric_id is not None:
        if metric_id not in metric_ids:
            print(
                f"WARNING: Metric ID {metric_id} is not present in "
                "the current LOF mapping."
            )

        metric_ids = [metric_id]

    elif limit is not None:
        metric_ids = metric_ids[:limit]

    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": USER_AGENT,
            "Accept": "text/csv,text/plain,*/*",
        }
    )

    records: list[dict] = []

    total_to_process = len(metric_ids)

    for position, current_metric_id in enumerate(
        metric_ids,
        start=1,
    ):
        print(
            f"[{position}/{total_to_process}] "
            f"Metric {current_metric_id}...",
            end=" ",
            flush=True,
        )

        try:
            source_df, resolved_url, retrieved_at = (
                download_metric_csv(
                    session,
                    current_metric_id,
                )
            )

            record = extract_metric_metadata(
                metric_id=current_metric_id,
                dataframe=source_df,
                resolved_url=resolved_url,
                retrieved_at=retrieved_at,
            )

            records.append(record)

            print(
                "OK"
                f" | polarity={record['polarity_original']}"
                f" | period={record['period_type']}"
            )

        except Exception as exc:
            records.append(
                build_failure_record(
                    current_metric_id,
                    exc,
                )
            )

            print(f"FAILED | {exc}")

        if position < total_to_process:
            time.sleep(REQUEST_DELAY_SECONDS)

    metadata = pd.DataFrame(records)

    if "error_message" not in metadata.columns:
        metadata["error_message"] = None

    metadata = metadata.sort_values(
        "lg_inform_metric_id"
    ).reset_index(drop=True)

    review_mask = metadata.apply(
        needs_review,
        axis=1,
    )

    review = metadata.loc[review_mask].copy()

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    metadata.to_csv(
        output_path,
        index=False,
    )

    review.to_csv(
        review_path,
        index=False,
    )

    print_coverage(
        metadata,
        expected_count=(
            1
            if metric_id is not None
            else (
                len(metric_ids)
                if limit is not None
                else EXPECTED_UNIQUE_DIRECT_METRICS
            )
        ),
    )

    print()
    print(f"Metadata output : {output_path}")
    print(f"Review output   : {review_path}")
    print(f"Rows for review : {len(review)}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Enrich LOF LG Inform metrics using public "
            "ESD Standards mappings CSVs."
        )
    )

    parser.add_argument(
        "--mapping",
        type=Path,
        default=DEFAULT_MAPPING_PATH,
        help="Path to lof_lg_inform_mapping.csv",
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Metadata output CSV",
    )

    parser.add_argument(
        "--review-output",
        type=Path,
        default=DEFAULT_REVIEW_PATH,
        help="Review queue output CSV",
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Process only the first N metrics for testing",
    )

    parser.add_argument(
        "--metric-id",
        type=int,
        default=None,
        help="Process one specific Metric ID",
    )

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    run(
        mapping_path=args.mapping,
        output_path=args.output,
        review_path=args.review_output,
        limit=args.limit,
        metric_id=args.metric_id,
    )