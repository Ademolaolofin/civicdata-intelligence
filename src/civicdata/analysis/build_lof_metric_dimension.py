from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[3]

MANIFEST_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "lof_v01_metric_manifest.csv"
)

LG_MAPPING_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "lof_lg_inform_mapping.csv"
)

LG_METADATA_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "lof_lg_inform_metadata.csv"
)

DIMENSION_OUTPUT_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "lof_v01_metric_dimension.csv"
)

RELATIONSHIP_OUTPUT_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "lof_v01_metric_outcome_relationships.csv"
)


def normalise_label(value: object) -> str:
    if pd.isna(value):
        return ""

    text = str(value).strip()

    if text.lower().endswith("(mhclg)"):
        text = text[:-7].strip()

    return " ".join(text.split()).casefold()


def load_inputs() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    for path in [
        MANIFEST_PATH,
        LG_MAPPING_PATH,
        LG_METADATA_PATH,
    ]:
        if not path.exists():
            raise FileNotFoundError(
                f"Required input not found: {path}"
            )

    manifest = pd.read_csv(MANIFEST_PATH)
    mapping = pd.read_csv(LG_MAPPING_PATH)
    metadata = pd.read_csv(LG_METADATA_PATH)

    return manifest, mapping, metadata


def validate_metric_consistency(manifest: pd.DataFrame) -> None:
    """
    Validate fields that genuinely define a CivicData metric.

    Outcome membership and source_url are deliberately excluded.
    A metric may legitimately appear under multiple outcomes, and
    relationship rows may contain different reference URLs.
    """

    invariant_columns = [
        "metric_name",
        "metric_type",
        "metric_status",
        "source_organisation",
        "source_dataset",
        "data_provider",
        "data_collection",
        "implementation_batch",
        "implementation_status",
        "existing_civicdata_source",
    ]

    for column in invariant_columns:
        if column not in manifest.columns:
            raise ValueError(
                f"Manifest missing required column: {column}"
            )

    conflicts = []

    for metric_id, group in manifest.groupby("metric_id"):
        for column in invariant_columns:
            unique_values = (
                group[column]
                .fillna("<NA>")
                .astype(str)
                .unique()
            )

            if len(unique_values) > 1:
                conflicts.append(
                    {
                        "metric_id": metric_id,
                        "column": column,
                        "values": list(unique_values),
                    }
                )

    if conflicts:
        conflict_text = "\n".join(
            f"{item['metric_id']} | "
            f"{item['column']} | "
            f"{item['values']}"
            for item in conflicts
        )

        raise ValueError(
            "Conflicting metric-level definitions found:\n"
            + conflict_text
        )


def build_relationship_table(
    manifest: pd.DataFrame,
) -> pd.DataFrame:
    required = [
        "metric_id",
        "metric_name",
        "outcome_id",
        "outcome_name",
        "metric_type",
        "source_url",
    ]

    missing = set(required) - set(manifest.columns)

    if missing:
        raise ValueError(
            "Manifest missing relationship columns: "
            + ", ".join(sorted(missing))
        )

    relationships = manifest[required].copy()

    duplicate_relationships = relationships.duplicated(
        subset=["metric_id", "outcome_id"]
    ).sum()

    if duplicate_relationships:
        raise ValueError(
            f"Found {duplicate_relationships} duplicate "
            "metric-outcome relationships."
        )

    relationships = relationships.sort_values(
        ["outcome_id", "metric_name", "metric_id"]
    ).reset_index(drop=True)

    return relationships


def build_metric_base(
    manifest: pd.DataFrame,
) -> pd.DataFrame:
    validate_metric_consistency(manifest)

    metric_columns = [
        "metric_id",
        "metric_name",
        "metric_type",
        "metric_status",
        "source_organisation",
        "source_dataset",
        "data_provider",
        "data_collection",
        "implementation_batch",
        "implementation_status",
        "existing_civicdata_source",
    ]

    metrics = (
        manifest[metric_columns]
        .drop_duplicates(subset=["metric_id"])
        .copy()
    )

    if metrics["metric_id"].duplicated().any():
        raise ValueError(
            "Duplicate CivicData metric IDs remain after "
            "building the metric dimension."
        )

    return metrics


def attach_lg_inform_mapping(
    metrics: pd.DataFrame,
    mapping: pd.DataFrame,
) -> pd.DataFrame:
    required_mapping = {
        "source_lof_label",
        "lg_inform_metric_id",
        "lg_inform_metric_title",
        "mapping_status",
    }

    missing = required_mapping - set(mapping.columns)

    if missing:
        raise ValueError(
            "LG Inform mapping missing required columns: "
            + ", ".join(sorted(missing))
        )

    metrics = metrics.copy()
    mapping = mapping.copy()

    metrics["match_key"] = metrics["metric_name"].map(
        normalise_label
    )

    mapping["match_key"] = mapping["source_lof_label"].map(
        normalise_label
    )

    direct_mapping = mapping[
        mapping["mapping_status"].eq("mapped")
        & mapping["lg_inform_metric_id"].notna()
    ].copy()

    mapping_counts = (
        direct_mapping.groupby("match_key")
        .size()
        .rename("mapping_count")
        .reset_index()
    )

    direct_mapping = direct_mapping.merge(
        mapping_counts,
        on="match_key",
        how="left",
    )

    unique_mapping = direct_mapping[
        direct_mapping["mapping_count"].eq(1)
    ][
        [
            "match_key",
            "lg_inform_metric_id",
            "lg_inform_metric_title",
            "mapping_status",
        ]
    ].copy()

    result = metrics.merge(
        unique_mapping,
        on="match_key",
        how="left",
        validate="one_to_one",
    )

    result = result.drop(columns=["match_key"])

    return result


def attach_lg_inform_metadata(
    dimension: pd.DataFrame,
    metadata: pd.DataFrame,
) -> pd.DataFrame:
    metadata_columns = [
        "lg_inform_metric_id",
        "short_label",
        "description",
        "status",
        "modified",
        "output_precision",
        "polarity_original",
        "polarity_standardised",
        "polarity_status",
        "measure",
        "dataset",
        "collection",
        "source",
        "discontinued",
        "period_type",
        "period_mapping_status",
        "metric_uri",
        "metadata_source",
        "metadata_source_url",
        "metadata_retrieved_at_utc",
        "metadata_status",
    ]

    missing = set(metadata_columns) - set(metadata.columns)

    if missing:
        raise ValueError(
            "LG Inform metadata missing required columns: "
            + ", ".join(sorted(missing))
        )

    metadata_subset = metadata[metadata_columns].copy()

    if metadata_subset["lg_inform_metric_id"].duplicated().any():
        raise ValueError(
            "Duplicate LG Inform metric IDs found in metadata."
        )

    dimension = dimension.merge(
        metadata_subset,
        on="lg_inform_metric_id",
        how="left",
        validate="many_to_one",
    )

    dimension["lg_inform_mapping_available"] = (
        dimension["lg_inform_metric_id"].notna()
    )

    dimension["lg_inform_metadata_available"] = (
        dimension["metadata_status"].eq("retrieved")
    )

    dimension["lg_inform_metric_id"] = (
        dimension["lg_inform_metric_id"]
        .astype("Int64")
    )

    return dimension


def validate_outputs(
    dimension: pd.DataFrame,
    relationships: pd.DataFrame,
    manifest: pd.DataFrame,
) -> None:
    expected_metrics = manifest["metric_id"].nunique()
    expected_relationships = len(manifest)

    actual_metrics = dimension["metric_id"].nunique()
    actual_relationships = len(relationships)

    duplicate_metric_ids = (
        dimension["metric_id"].duplicated().sum()
    )

    duplicate_relationships = relationships.duplicated(
        subset=["metric_id", "outcome_id"]
    ).sum()

    mapped_metrics = int(
        dimension["lg_inform_mapping_available"].sum()
    )

    metadata_metrics = int(
        dimension["lg_inform_metadata_available"].sum()
    )

    expected_iod_mapping = {
        "Indices of Multiple Deprivation (IMD) average score": 3902,
        "Income deprivation affecting children index": 3910,
        "Income deprivation affecting older people index": 3911,
    }

    iod_mapping_pass = True

    for metric_name, expected_id in expected_iod_mapping.items():
        row = dimension[
            dimension["metric_name"].eq(metric_name)
        ]

        if len(row) != 1:
            iod_mapping_pass = False
            continue

        actual_id = row.iloc[0]["lg_inform_metric_id"]

        if pd.isna(actual_id):
            iod_mapping_pass = False
            continue

        if int(actual_id) != expected_id:
            iod_mapping_pass = False

    repeated_metric_ids = (
        relationships.groupby("metric_id")
        .size()
    )

    multi_outcome_metrics = int(
        (repeated_metric_ids > 1).sum()
    )

    print()
    print("VALIDATION")
    print("=" * 60)
    print(
        f"Expected unique metrics       : "
        f"{expected_metrics:,}"
    )
    print(
        f"Actual unique metrics         : "
        f"{actual_metrics:,}"
    )
    print(
        f"Expected relationships        : "
        f"{expected_relationships:,}"
    )
    print(
        f"Actual relationships          : "
        f"{actual_relationships:,}"
    )
    print(
        f"Multi-outcome metrics         : "
        f"{multi_outcome_metrics:,}"
    )
    print(
        f"Duplicate CivicData IDs       : "
        f"{duplicate_metric_ids:,}"
    )
    print(
        f"Duplicate relationships       : "
        f"{duplicate_relationships:,}"
    )
    print(
        f"LG Inform mappings available  : "
        f"{mapped_metrics:,}"
    )
    print(
        f"LG Inform metadata available  : "
        f"{metadata_metrics:,}"
    )
    print(
        f"IoD mapping check             : "
        f"{'PASS' if iod_mapping_pass else 'FAIL'}"
    )

    checks = {
        "unique metric count":
            actual_metrics == expected_metrics,
        "relationship count":
            actual_relationships == expected_relationships,
        "no duplicate metric IDs":
            duplicate_metric_ids == 0,
        "no duplicate relationships":
            duplicate_relationships == 0,
        "IoD LG Inform mapping":
            iod_mapping_pass,
    }

    failed = [
        name
        for name, passed in checks.items()
        if not passed
    ]

    if failed:
        print()
        print("Validation: FAIL")

        for check in failed:
            print(f"  - {check}")

        raise ValueError(
            "LOF v0.1 metric model validation failed."
        )

    print()
    print("Validation: PASS")


def main() -> None:
    print("CivicData LOF v0.1 metric model")
    print("=" * 60)

    manifest, mapping, metadata = load_inputs()

    relationships = build_relationship_table(
        manifest
    )

    metrics = build_metric_base(
        manifest
    )

    dimension = attach_lg_inform_mapping(
        metrics,
        mapping,
    )

    dimension = attach_lg_inform_metadata(
        dimension,
        metadata,
    )

    validate_outputs(
        dimension,
        relationships,
        manifest,
    )

    DIMENSION_OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    dimension.to_csv(
        DIMENSION_OUTPUT_PATH,
        index=False,
    )

    relationships.to_csv(
        RELATIONSHIP_OUTPUT_PATH,
        index=False,
    )

    print()
    print("IoD mappings")
    print("=" * 60)

    iod_names = [
        "Indices of Multiple Deprivation (IMD) average score",
        "Income deprivation affecting children index",
        "Income deprivation affecting older people index",
    ]

    iod_columns = [
        "metric_id",
        "metric_name",
        "lg_inform_metric_id",
        "lg_inform_metric_title",
        "measure",
        "collection",
        "polarity_standardised",
        "period_type",
    ]

    print(
        dimension.loc[
            dimension["metric_name"].isin(iod_names),
            iod_columns,
        ].to_string(index=False)
    )

    print()
    print(
        f"Metric dimension written      : "
        f"{DIMENSION_OUTPUT_PATH}"
    )
    print(
        f"Outcome relationships written : "
        f"{RELATIONSHIP_OUTPUT_PATH}"
    )

    print()
    print("LOF v0.1 metric model complete.")


if __name__ == "__main__":
    main()