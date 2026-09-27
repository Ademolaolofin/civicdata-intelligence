from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[3]

DIMENSION_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "lof_v01_metric_dimension.csv"
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

OUTPUT_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "lof_v01_lg_inform_crosswalk.csv"
)


# Explicit, reviewed mappings for the CivicData v0.1 pilot.
#
# These are deliberately not generated using fuzzy matching.
# The mapping was reviewed against the LG Inform LOF Report IDs
# workbook.
#
# role:
#   primary         = principal LG Inform representation
#   component       = required component of a split LOF concept
#   disaggregation  = additional breakdown explicitly included
#                     within the LOF concept
CROSSWALK = {
    "Income deprivation affecting children index": [
        (3910, "primary"),
    ],
    "Income deprivation affecting older people index": [
        (3911, "primary"),
    ],
    "Indices of Multiple Deprivation (IMD) average score": [
        (3902, "primary"),
    ],
    "Child health: percentage achieving good level of development at 2-2.5 year review ( DHSC )": [
        (13643, "primary"),
    ],
    "Cardiovascular disease prevention: Proportion of NHS health checks completed across the eligible population": [
        (8223, "primary"),
    ],
    "Drugs and alcohol: rate of alcohol-specific mortality (directly standardised rate per 100,000)": [
        (27774, "primary"),
    ],
    "Health life expectancy at birth (split by male and female)": [
        (3155, "component"),
        (3156, "component"),
    ],
    "Mental Health: Suicide Rate": [
        (12156, "primary"),
    ],
    "Smoking: percentage of those setting a quit date who successfully quit smoking": [
        (27585, "primary"),
    ],
    "Child development: Percentage of children with a good level of development at 5 years old": [
        (19346, "primary"),
    ],
    "Child development: Percentage point difference between the proportion of children eligible or not eligible for Free School Meals achieving a Good Level of Development": [
        (27666, "primary"),
    ],
    "School attainment: Percentage of pupils meeting the expected standard in reading, writing and maths at Key Stage 2 for all state funded schools, local authority maintained schools and academies": [
        (6080, "primary"),
    ],
    "Killed or seriously injured per billion vehicle miles": [
        (16135, "primary"),
    ],
    "Passenger journeys on local bus services per head by local authority (including disaggregation by concessionary pass journeys)": [
        (12801, "primary"),
        (12804, "disaggregation"),
    ],
    "Public EVSEs (Electric Vehicle Supply Equipment per 100,000 population)": [
        (14678, "primary"),
    ],
    "Births of new enterprises": [
        (540, "primary"),
    ],
    "Business survival rate": [
        (9644, "primary"),
    ],
    "Deaths of enterprises": [
        (541, "primary"),
    ],
    "Percentage of total household waste sent for recycling, compost and reuse": [
        (46, "primary"),
    ],
    "Rate of fly-tipping enforcement actions per incident": [
        (25733, "primary"),
    ],
}


def load_inputs() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    for path in [
        DIMENSION_PATH,
        LG_MAPPING_PATH,
        LG_METADATA_PATH,
    ]:
        if not path.exists():
            raise FileNotFoundError(
                f"Required input not found: {path}"
            )

    dimension = pd.read_csv(DIMENSION_PATH)
    mapping = pd.read_csv(LG_MAPPING_PATH)
    metadata = pd.read_csv(LG_METADATA_PATH)

    return dimension, mapping, metadata


def build_crosswalk(
    dimension: pd.DataFrame,
    mapping: pd.DataFrame,
    metadata: pd.DataFrame,
) -> pd.DataFrame:
    pilot_names = set(dimension["metric_name"])
    configured_names = set(CROSSWALK)

    missing_configuration = pilot_names - configured_names
    unknown_configuration = configured_names - pilot_names

    if missing_configuration:
        raise ValueError(
            "Pilot metrics missing from explicit crosswalk:\n"
            + "\n".join(sorted(missing_configuration))
        )

    if unknown_configuration:
        raise ValueError(
            "Crosswalk contains metrics not present in pilot dimension:\n"
            + "\n".join(sorted(unknown_configuration))
        )

    mapping = mapping.copy()
    metadata = metadata.copy()

    mapping["lg_inform_metric_id"] = pd.to_numeric(
        mapping["lg_inform_metric_id"],
        errors="coerce",
    ).astype("Int64")

    metadata["lg_inform_metric_id"] = pd.to_numeric(
        metadata["lg_inform_metric_id"],
        errors="coerce",
    ).astype("Int64")

    rows = []

    for metric_name, mappings in CROSSWALK.items():
        metric_row = dimension[
            dimension["metric_name"].eq(metric_name)
        ]

        if len(metric_row) != 1:
            raise ValueError(
                f"Expected exactly one CivicData metric for: "
                f"{metric_name}"
            )

        metric_id = metric_row.iloc[0]["metric_id"]

        for lg_id, role in mappings:
            workbook_rows = mapping[
                mapping["lg_inform_metric_id"].eq(lg_id)
            ]

            if workbook_rows.empty:
                raise ValueError(
                    f"LG Inform metric {lg_id} not found in "
                    f"official mapping workbook."
                )

            # The same LG Inform ID may legitimately appear more
            # than once because a metric can be reused across outcomes.
            # Prefer a workbook row whose LOF label contains the
            # CivicData metric wording where possible.
            candidate = workbook_rows.iloc[0]

            metadata_row = metadata[
                metadata["lg_inform_metric_id"].eq(lg_id)
            ]

            if len(metadata_row) != 1:
                raise ValueError(
                    f"Expected exactly one metadata record for "
                    f"LG Inform metric {lg_id}; found "
                    f"{len(metadata_row)}."
                )

            meta = metadata_row.iloc[0]

            rows.append(
                {
                    "metric_id": metric_id,
                    "metric_name": metric_name,
                    "lg_inform_metric_id": lg_id,
                    "mapping_role": role,
                    "lg_inform_metric_title":
                        candidate["source_lgi_label"],
                    "lg_inform_lof_label":
                        candidate["source_lof_label"],
                    "lg_inform_section":
                        candidate["source_section"],
                    "lg_inform_mapping_status":
                        candidate["mapping_status"],
                    "short_label":
                        meta["short_label"],
                    "description":
                        meta["description"],
                    "measure":
                        meta["measure"],
                    "dataset":
                        meta["dataset"],
                    "collection":
                        meta["collection"],
                    "source":
                        meta["source"],
                    "polarity_original":
                        meta["polarity_original"],
                    "polarity_standardised":
                        meta["polarity_standardised"],
                    "period_type":
                        meta["period_type"],
                    "status":
                        meta["status"],
                    "metric_uri":
                        meta["metric_uri"],
                    "metadata_source":
                        meta["metadata_source"],
                    "metadata_source_url":
                        meta["metadata_source_url"],
                }
            )

    crosswalk = pd.DataFrame(rows)

    crosswalk["lg_inform_metric_id"] = (
        crosswalk["lg_inform_metric_id"].astype("Int64")
    )

    return crosswalk


def validate_crosswalk(
    crosswalk: pd.DataFrame,
    dimension: pd.DataFrame,
) -> None:
    expected_civicdata_metrics = dimension["metric_id"].nunique()
    actual_civicdata_metrics = crosswalk["metric_id"].nunique()

    expected_rows = sum(
        len(value)
        for value in CROSSWALK.values()
    )

    actual_rows = len(crosswalk)

    duplicate_pairs = crosswalk.duplicated(
        subset=["metric_id", "lg_inform_metric_id"]
    ).sum()

    missing_metadata = crosswalk[
        [
            "measure",
            "collection",
            "source",
            "period_type",
        ]
    ].isna().any(axis=1).sum()

    role_counts = crosswalk["mapping_role"].value_counts()

    multi_mapping = (
        crosswalk.groupby("metric_id")
        .size()
        .loc[lambda x: x > 1]
    )

    print()
    print("VALIDATION")
    print("=" * 60)
    print(
        f"Expected CivicData metrics : "
        f"{expected_civicdata_metrics:,}"
    )
    print(
        f"Mapped CivicData metrics   : "
        f"{actual_civicdata_metrics:,}"
    )
    print(
        f"Expected crosswalk rows    : "
        f"{expected_rows:,}"
    )
    print(
        f"Actual crosswalk rows      : "
        f"{actual_rows:,}"
    )
    print(
        f"Duplicate metric pairs     : "
        f"{duplicate_pairs:,}"
    )
    print(
        f"Rows missing core metadata : "
        f"{missing_metadata:,}"
    )

    print()
    print("Mapping roles")
    print("-" * 60)
    print(role_counts.to_string())

    print()
    print("Multi-mapping CivicData metrics")
    print("-" * 60)

    if multi_mapping.empty:
        print("None")
    else:
        for metric_id, count in multi_mapping.items():
            metric_name = crosswalk.loc[
                crosswalk["metric_id"].eq(metric_id),
                "metric_name",
            ].iloc[0]

            ids = crosswalk.loc[
                crosswalk["metric_id"].eq(metric_id),
                "lg_inform_metric_id",
            ].tolist()

            print(
                f"{metric_name}: "
                f"{count} mappings -> {ids}"
            )

    checks = {
        "all pilot metrics mapped":
            actual_civicdata_metrics == expected_civicdata_metrics,
        "expected crosswalk row count":
            actual_rows == expected_rows,
        "no duplicate metric pairs":
            duplicate_pairs == 0,
        "core metadata complete":
            missing_metadata == 0,
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
            "LOF v0.1 LG Inform crosswalk validation failed."
        )

    print()
    print("Validation: PASS")


def main() -> None:
    print("CivicData LOF v0.1 LG Inform crosswalk")
    print("=" * 60)

    dimension, mapping, metadata = load_inputs()

    crosswalk = build_crosswalk(
        dimension,
        mapping,
        metadata,
    )

    validate_crosswalk(
        crosswalk,
        dimension,
    )

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    crosswalk.to_csv(
        OUTPUT_PATH,
        index=False,
    )

    print()
    print("Crosswalk")
    print("=" * 60)

    print(
        crosswalk[
            [
                "metric_id",
                "metric_name",
                "lg_inform_metric_id",
                "mapping_role",
                "lg_inform_metric_title",
                "period_type",
            ]
        ].to_string(index=False)
    )

    print()
    print(f"Output written: {OUTPUT_PATH}")
    print()
    print("LOF v0.1 LG Inform crosswalk complete.")


if __name__ == "__main__":
    main()