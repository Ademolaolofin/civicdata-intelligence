from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[3]

CATALOGUE_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "lof_metric_catalogue.csv"
)

OUTPUT_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "lof_metric_catalogue_enriched.csv"
)


LG_INFORM_COLUMNS = [
    "lg_inform_available",
    "lg_inform_metric_id",
    "lg_inform_metric_title",
    "lg_inform_collection",
    "lg_inform_unit",
    "lg_inform_polarity",
    "lg_inform_period",
    "lg_inform_metric_uri",
]


REQUIRED_COLUMNS = [
    "outcome_id",
    "outcome_name",
    "metric_id",
    "metric_name",
    "metric_type",
    "metric_status",
]


def load_catalogue() -> pd.DataFrame:
    """
    Load the official MHCLG-derived LOF catalogue.
    """

    if not CATALOGUE_PATH.exists():
        raise FileNotFoundError(
            "LOF catalogue not found. Run "
            "build_lof_catalogue.py first."
        )

    catalogue = pd.read_csv(
        CATALOGUE_PATH
    )

    print(
        f"Catalogue rows loaded: "
        f"{len(catalogue):,}"
    )

    return catalogue


def validate_catalogue(
    catalogue: pd.DataFrame,
) -> None:
    """
    Validate the catalogue structure before LG Inform
    enrichment begins.
    """

    missing_columns = [
        column
        for column in REQUIRED_COLUMNS
        if column not in catalogue.columns
    ]

    if missing_columns:
        raise ValueError(
            "Missing required catalogue columns: "
            f"{missing_columns}"
        )

    missing_lg_columns = [
        column
        for column in LG_INFORM_COLUMNS
        if column not in catalogue.columns
    ]

    if missing_lg_columns:
        raise ValueError(
            "Missing LG Inform enrichment columns: "
            f"{missing_lg_columns}"
        )

    print(
        f"Unique MHCLG metrics: "
        f"{catalogue['metric_id'].nunique():,}"
    )

    print(
        f"Outcome-metric relationships: "
        f"{len(catalogue):,}"
    )

    print(
        "Catalogue structure PASS"
    )


def prepare_lg_inform_columns(
    catalogue: pd.DataFrame,
) -> pd.DataFrame:
    """
    Prepare LG Inform enrichment columns for text metadata.

    Empty CSV columns are commonly inferred by pandas as float64
    because their values are represented as NaN. Explicitly
    converting these columns to object dtype allows them to hold
    LG Inform identifiers, labels, URIs and mapping statuses
    safely.
    """

    result = catalogue.copy()

    for column in LG_INFORM_COLUMNS:
        if column not in result.columns:
            result[column] = pd.Series(
                pd.NA,
                index=result.index,
                dtype="object",
            )
        else:
            result[column] = result[
                column
            ].astype("object")

    return result


def initialise_mapping_status(
    catalogue: pd.DataFrame,
) -> pd.DataFrame:
    """
    Initialise LG Inform mapping status.

    Placeholder metrics are explicitly marked as not applicable
    for current observation mapping.

    Available metrics remain unassessed until a verified
    LG Inform metric has been identified.
    """

    result = prepare_lg_inform_columns(
        catalogue
    )

    placeholder_mask = (
        result["metric_status"]
        .fillna("")
        .str.lower()
        .eq("placeholder")
    )

    available_mask = (
        result["metric_status"]
        .fillna("")
        .str.lower()
        .eq("available")
    )

    result.loc[
        placeholder_mask,
        "lg_inform_available",
    ] = "not_applicable_placeholder"

    result.loc[
        available_mask
        & result[
            "lg_inform_available"
        ].isna(),
        "lg_inform_available",
    ] = "not_assessed"

    return result


def build_unique_metric_view(
    catalogue: pd.DataFrame,
) -> pd.DataFrame:
    """
    Create a unique metric-level view.

    The main LOF catalogue is an outcome-metric relationship
    table, so the same metric may legitimately appear under
    multiple outcomes.

    LG Inform mapping should therefore be assessed at the
    unique metric level rather than counting duplicated
    outcome relationships as separate metrics.
    """

    unique_metrics = (
        catalogue[
            [
                "metric_id",
                "metric_name",
                "metric_status",
                "source_organisation",
                "lg_inform_available",
                "lg_inform_metric_id",
                "lg_inform_metric_title",
                "lg_inform_collection",
                "lg_inform_unit",
                "lg_inform_polarity",
                "lg_inform_period",
                "lg_inform_metric_uri",
            ]
        ]
        .drop_duplicates(
            subset=["metric_id"]
        )
        .copy()
    )

    return unique_metrics


def validate_mapping(
    catalogue: pd.DataFrame,
) -> None:
    """
    Validate initial LG Inform mapping status.
    """

    print(
        "\n=== LG INFORM MAPPING VALIDATION ==="
    )

    unique_metrics = build_unique_metric_view(
        catalogue
    )

    print(
        f"Unique metrics: "
        f"{len(unique_metrics):,}"
    )

    available_mask = (
        unique_metrics[
            "metric_status"
        ]
        .fillna("")
        .str.lower()
        .eq("available")
    )

    placeholder_mask = (
        unique_metrics[
            "metric_status"
        ]
        .fillna("")
        .str.lower()
        .eq("placeholder")
    )

    available_metrics = int(
        available_mask.sum()
    )

    placeholder_metrics = int(
        placeholder_mask.sum()
    )

    print(
        f"Available MHCLG metrics: "
        f"{available_metrics:,}"
    )

    print(
        f"Placeholder metrics: "
        f"{placeholder_metrics:,}"
    )

    if (
        available_metrics
        + placeholder_metrics
        != len(unique_metrics)
    ):
        unknown_status_count = (
            len(unique_metrics)
            - available_metrics
            - placeholder_metrics
        )

        raise ValueError(
            "Unexpected MHCLG metric status values "
            f"found: {unknown_status_count}"
        )

    print(
        "\nLG Inform mapping status:"
    )

    status_counts = (
        unique_metrics[
            "lg_inform_available"
        ]
        .fillna("missing")
        .value_counts()
    )

    for status, count in (
        status_counts.items()
    ):
        print(
            f"  {status}: {count:,}"
        )

    placeholder_status_valid = (
        unique_metrics.loc[
            placeholder_mask,
            "lg_inform_available",
        ]
        .eq(
            "not_applicable_placeholder"
        )
        .all()
    )

    if not placeholder_status_valid:
        raise ValueError(
            "Placeholder metrics have incorrect "
            "LG Inform mapping status."
        )

    available_status_valid = (
        unique_metrics.loc[
            available_mask,
            "lg_inform_available",
        ]
        .notna()
        .all()
    )

    if not available_status_valid:
        raise ValueError(
            "Available metrics contain missing "
            "LG Inform assessment status."
        )

    print(
        "\nLG Inform mapping validation PASS"
    )


def show_mapping_candidates(
    catalogue: pd.DataFrame,
) -> None:
    """
    Display available unique metrics that still require
    assessment against LG Inform.

    No automatic match is made at this stage.
    """

    unique_metrics = build_unique_metric_view(
        catalogue
    )

    candidates = (
        unique_metrics[
            (
                unique_metrics[
                    "metric_status"
                ]
                .fillna("")
                .str.lower()
                .eq("available")
            )
            & (
                unique_metrics[
                    "lg_inform_available"
                ]
                .eq("not_assessed")
            )
        ][
            [
                "metric_id",
                "metric_name",
                "source_organisation",
            ]
        ]
        .sort_values(
            by=[
                "source_organisation",
                "metric_name",
            ],
            na_position="last",
        )
        .reset_index(
            drop=True
        )
    )

    print(
        "\n=== LG INFORM MAPPING CANDIDATES ==="
    )

    print(
        f"Metrics requiring assessment: "
        f"{len(candidates):,}"
    )

    print(
        "\nFirst 20 candidates:"
    )

    if candidates.empty:
        print(
            "No unassessed metrics."
        )
    else:
        print(
            candidates.head(
                20
            ).to_string(
                index=False
            )
        )


def validate_relationship_preservation(
    original: pd.DataFrame,
    enriched: pd.DataFrame,
) -> None:
    """
    Ensure LG Inform enrichment has not altered the official
    MHCLG outcome-metric relationship structure.
    """

    if len(original) != len(enriched):
        raise ValueError(
            "Row count changed during LG Inform enrichment."
        )

    original_relationships = set(
        zip(
            original["outcome_id"],
            original["metric_id"],
        )
    )

    enriched_relationships = set(
        zip(
            enriched["outcome_id"],
            enriched["metric_id"],
        )
    )

    if (
        original_relationships
        != enriched_relationships
    ):
        raise ValueError(
            "MHCLG outcome-metric relationships changed "
            "during LG Inform enrichment."
        )

    print(
        "\nRelationship preservation PASS"
    )


def save_enriched_catalogue(
    catalogue: pd.DataFrame,
) -> None:
    """
    Save the LOF catalogue with LG Inform mapping fields.
    """

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    catalogue.to_csv(
        OUTPUT_PATH,
        index=False,
    )

    print(
        "\nEnriched catalogue saved to: "
        f"{OUTPUT_PATH}"
    )


def main() -> None:
    """
    Prepare the official LOF catalogue for verified
    LG Inform mapping.
    """

    print(
        "\n=== CIVICDATA LG INFORM "
        "MAPPING LAYER ==="
    )

    catalogue = load_catalogue()

    validate_catalogue(
        catalogue
    )

    enriched = (
        initialise_mapping_status(
            catalogue
        )
    )

    validate_relationship_preservation(
        catalogue,
        enriched,
    )

    validate_mapping(
        enriched
    )

    show_mapping_candidates(
        enriched
    )

    save_enriched_catalogue(
        enriched
    )

    print(
        "\n=== COMPLETE ==="
    )

    print(
        "LG Inform mapping layer initialised."
    )

    print(
        "No LG Inform matches have been "
        "assumed or fabricated."
    )


if __name__ == "__main__":
    main()