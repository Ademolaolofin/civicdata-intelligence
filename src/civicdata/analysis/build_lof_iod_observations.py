from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[3]

MANIFEST_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "lof_v01_metric_manifest.csv"
)

IOD_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "iod_2025_lad_official_summaries.csv"
)

OUTPUT_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "lof_iod_observations_2025.csv"
)


# Explicit, auditable mapping between MHCLG LOF metric wording
# and the corresponding official IoD 2025 File 10 LAD summary measure.
METRIC_MAPPING = {
    "Income deprivation affecting children index": "idaci_average_score",
    "Income deprivation affecting older people index": "idaopi_average_score",
    "Indices of Multiple Deprivation (IMD) average score": "imd_average_score",
}


def load_inputs() -> tuple[pd.DataFrame, pd.DataFrame]:
    if not MANIFEST_PATH.exists():
        raise FileNotFoundError(
            f"LOF v0.1 manifest not found: {MANIFEST_PATH}"
        )

    if not IOD_PATH.exists():
        raise FileNotFoundError(
            f"IoD official LAD summaries not found: {IOD_PATH}"
        )

    manifest = pd.read_csv(MANIFEST_PATH)
    iod = pd.read_csv(IOD_PATH)

    return manifest, iod


def validate_inputs(
    manifest: pd.DataFrame,
    iod: pd.DataFrame,
) -> pd.DataFrame:
    required_manifest_columns = {
        "metric_id",
        "metric_name",
        "outcome_id",
        "outcome_name",
        "metric_type",
        "metric_status",
        "source_organisation",
        "source_url",
        "data_provider",
        "data_collection",
        "implementation_batch",
        "implementation_status",
    }

    required_iod_columns = {
        "authority_code",
        "authority_name",
        "imd_average_score",
        "idaci_average_score",
        "idaopi_average_score",
    }

    missing_manifest = required_manifest_columns - set(manifest.columns)
    missing_iod = required_iod_columns - set(iod.columns)

    if missing_manifest:
        raise ValueError(
            "Manifest is missing required columns: "
            + ", ".join(sorted(missing_manifest))
        )

    if missing_iod:
        raise ValueError(
            "IoD dataset is missing required columns: "
            + ", ".join(sorted(missing_iod))
        )

    selected = manifest[
        manifest["metric_name"].isin(METRIC_MAPPING)
    ].copy()

    found_metrics = set(selected["metric_name"])
    expected_metrics = set(METRIC_MAPPING)

    missing_metrics = expected_metrics - found_metrics

    if missing_metrics:
        raise ValueError(
            "Required LOF IoD metrics not found in manifest: "
            + ", ".join(sorted(missing_metrics))
        )

    duplicate_relationships = selected.duplicated(
        subset=["metric_id", "outcome_id"]
    ).sum()

    if duplicate_relationships:
        raise ValueError(
            f"Found {duplicate_relationships} duplicate "
            "metric-outcome relationships in manifest."
        )

    if iod["authority_code"].duplicated().any():
        duplicates = iod.loc[
            iod["authority_code"].duplicated(keep=False),
            ["authority_code", "authority_name"],
        ]

        raise ValueError(
            "Duplicate authority codes found in IoD dataset:\n"
            + duplicates.to_string(index=False)
        )

    return selected


def build_observations(
    selected_manifest: pd.DataFrame,
    iod: pd.DataFrame,
) -> pd.DataFrame:
    observation_frames = []

    authority_columns = [
        "authority_code",
        "authority_name",
    ]

    for _, metric in selected_manifest.iterrows():
        metric_name = metric["metric_name"]
        value_column = METRIC_MAPPING[metric_name]

        frame = iod[
            authority_columns + [value_column]
        ].copy()

        frame = frame.rename(
            columns={
                value_column: "value",
            }
        )

        frame["metric_id"] = metric["metric_id"]
        frame["metric_name"] = metric_name
        frame["outcome_id"] = metric["outcome_id"]
        frame["outcome_name"] = metric["outcome_name"]
        frame["metric_type"] = metric["metric_type"]

        # IoD 2025 is a release/version rather than an annual
        # observation series. Preserve that distinction explicitly.
        frame["release"] = "2025"
        frame["period_id"] = pd.NA
        frame["period_label"] = pd.NA
        frame["period_type"] = "release"

        frame["unit"] = (
            "IMD score"
            if metric_name
            == "Indices of Multiple Deprivation (IMD) average score"
            else "index score"
        )

        frame["source_organisation"] = metric[
            "source_organisation"
        ]
        frame["source_dataset"] = (
            "English Indices of Deprivation 2025 "
            "File 10: Local Authority District summaries - lower tier"
        )
        frame["source_url"] = metric["source_url"]
        frame["data_provider"] = metric["data_provider"]
        frame["data_collection"] = metric["data_collection"]

        observation_frames.append(frame)

    observations = pd.concat(
        observation_frames,
        ignore_index=True,
    )

    column_order = [
        "metric_id",
        "metric_name",
        "outcome_id",
        "outcome_name",
        "metric_type",
        "authority_code",
        "authority_name",
        "release",
        "period_id",
        "period_label",
        "period_type",
        "value",
        "unit",
        "source_organisation",
        "source_dataset",
        "source_url",
        "data_provider",
        "data_collection",
    ]

    return observations[column_order]


def validate_output(
    observations: pd.DataFrame,
    authority_count: int,
    metric_count: int,
) -> None:
    expected_rows = authority_count * metric_count
    actual_rows = len(observations)

    duplicate_observations = observations.duplicated(
        subset=[
            "metric_id",
            "outcome_id",
            "authority_code",
        ]
    ).sum()

    missing_values = observations["value"].isna().sum()
    unique_metrics = observations["metric_id"].nunique()
    unique_authorities = observations["authority_code"].nunique()

    print()
    print("VALIDATION")
    print("=" * 60)
    print(f"Expected rows       : {expected_rows:,}")
    print(f"Actual rows         : {actual_rows:,}")
    print(f"Unique metrics      : {unique_metrics:,}")
    print(f"Unique authorities  : {unique_authorities:,}")
    print(f"Missing values      : {missing_values:,}")
    print(f"Duplicate records   : {duplicate_observations:,}")

    checks = {
        "expected row count": actual_rows == expected_rows,
        "metric count": unique_metrics == metric_count,
        "authority count": unique_authorities == authority_count,
        "no missing values": missing_values == 0,
        "no duplicate records": duplicate_observations == 0,
    }

    failed = [
        name
        for name, passed in checks.items()
        if not passed
    ]

    if failed:
        print()
        print("Validation: FAIL")
        print("Failed checks:")
        for check in failed:
            print(f"  - {check}")

        raise ValueError(
            "LOF IoD observation validation failed."
        )

    print()
    print("Validation: PASS")


def main() -> None:
    print("CivicData LOF IoD observation bridge")
    print("=" * 60)

    manifest, iod = load_inputs()

    selected_manifest = validate_inputs(
        manifest,
        iod,
    )

    print(f"Manifest rows       : {len(manifest):,}")
    print(f"Selected LOF rows   : {len(selected_manifest):,}")
    print(
        f"Selected metrics    : "
        f"{selected_manifest['metric_id'].nunique():,}"
    )
    print(
        f"IoD authorities     : "
        f"{iod['authority_code'].nunique():,}"
    )

    print()
    print("METRIC MAPPING")
    print("=" * 60)

    for metric_name, source_column in METRIC_MAPPING.items():
        print(f"{metric_name}")
        print(f"  -> {source_column}")

    observations = build_observations(
        selected_manifest,
        iod,
    )

    validate_output(
        observations,
        authority_count=iod["authority_code"].nunique(),
        metric_count=selected_manifest["metric_id"].nunique(),
    )

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    observations.to_csv(
        OUTPUT_PATH,
        index=False,
    )

    print()
    print(f"Output written      : {OUTPUT_PATH}")
    print()
    print("LOF IoD observation bridge complete.")


if __name__ == "__main__":
    main()