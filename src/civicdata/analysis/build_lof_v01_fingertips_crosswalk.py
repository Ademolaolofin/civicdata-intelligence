from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[3]

METRIC_DIMENSION_PATH = (
    PROJECT_ROOT / "data" / "processed" / "lof_v01_metric_dimension.csv"
)

OUTPUT_PATH = (
    PROJECT_ROOT / "data" / "processed" / "lof_v01_fingertips_crosswalk.csv"
)


CROSSWALK = {
    "lof_metric_df814253e5d4": {
        "fingertips_indicator_id": 93436,
        "fingertips_indicator_name": (
            "Child development: percentage of children achieving "
            "a good level of development at 2 to 2 and a half years"
        ),
        "sex_filter": "Persons",
        "age_filter": "2-2.5 yrs",
        "category_type_filter": None,
        "period_range": "1y",
        "source_provider": "OHID Fingertips",
    },
    "lof_metric_e6e5febbc4ff": {
        "fingertips_indicator_id": 91734,
        "fingertips_indicator_name": (
            "People receiving an NHS Health Check per year"
        ),
        "sex_filter": "Persons",
        "age_filter": "40-74 yrs",
        "category_type_filter": None,
        "period_range": "1y",
        "source_provider": "OHID Fingertips",
    },
    "lof_metric_6acae76f75e0": {
        "fingertips_indicator_id": 91380,
        "fingertips_indicator_name": "Alcohol-specific mortality",
        "sex_filter": "Persons",
        "age_filter": "All ages",
        "category_type_filter": None,
        "period_range": "1y",
        "source_provider": "OHID Fingertips",
    },
    "lof_metric_a42711e2cb44": {
        "fingertips_indicator_id": 41001,
        "fingertips_indicator_name": "Suicide rate",
        "sex_filter": "Persons",
        "age_filter": "10+ yrs",
        "category_type_filter": None,
        "period_range": "3y",
        "source_provider": "OHID Fingertips",
    },
    "lof_metric_c7d3c6b21dc2": {
        "fingertips_indicator_id": 94243,
        "fingertips_indicator_name": (
            "Proportion of those setting a quit date "
            "who successfully quit smoking"
        ),
        "sex_filter": "Persons",
        "age_filter": "16+ yrs",
        "category_type_filter": None,
        "period_range": "1y",
        "source_provider": "OHID Fingertips",
    },
}


def main():
    print("CivicData LOF v0.1 Fingertips crosswalk")
    print("=" * 60)

    metrics = pd.read_csv(METRIC_DIMENSION_PATH)

    required_metric_ids = set(CROSSWALK)
    available_metric_ids = set(metrics["metric_id"])

    missing_metrics = required_metric_ids - available_metric_ids

    if missing_metrics:
        raise ValueError(
            "Crosswalk contains CivicData metric IDs not present "
            f"in metric dimension: {sorted(missing_metrics)}"
        )

    rows = []

    for metric_id, mapping in CROSSWALK.items():
        metric_row = metrics.loc[
            metrics["metric_id"].eq(metric_id)
        ]

        if len(metric_row) != 1:
            raise ValueError(
                f"Expected one metric dimension row for {metric_id}, "
                f"found {len(metric_row)}"
            )

        metric_row = metric_row.iloc[0]

        rows.append(
            {
                "metric_id": metric_id,
                "metric_name": metric_row["metric_name"],
                "fingertips_indicator_id": mapping[
                    "fingertips_indicator_id"
                ],
                "fingertips_indicator_name": mapping[
                    "fingertips_indicator_name"
                ],
                "sex_filter": mapping["sex_filter"],
                "age_filter": mapping["age_filter"],
                "category_type_filter": mapping[
                    "category_type_filter"
                ],
                "period_range": mapping["period_range"],
                "source_provider": mapping["source_provider"],
                "mapping_status": "validated",
            }
        )

    crosswalk = pd.DataFrame(rows)

    duplicate_metric_ids = crosswalk["metric_id"].duplicated().sum()
    duplicate_indicator_ids = (
        crosswalk["fingertips_indicator_id"].duplicated().sum()
    )

    expected_metrics = 5
    actual_metrics = crosswalk["metric_id"].nunique()

    print()
    print("VALIDATION")
    print("=" * 60)
    print(f"Expected CivicData metrics : {expected_metrics}")
    print(f"Mapped CivicData metrics   : {actual_metrics}")
    print(f"Crosswalk rows             : {len(crosswalk)}")
    print(f"Duplicate CivicData IDs    : {duplicate_metric_ids}")
    print(f"Duplicate Fingertips IDs   : {duplicate_indicator_ids}")

    validation_passed = (
        actual_metrics == expected_metrics
        and len(crosswalk) == expected_metrics
        and duplicate_metric_ids == 0
        and duplicate_indicator_ids == 0
    )

    if not validation_passed:
        raise ValueError("Fingertips crosswalk validation failed.")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    crosswalk.to_csv(OUTPUT_PATH, index=False)

    print()
    print("Crosswalk")
    print("=" * 60)

    print(
        crosswalk[
            [
                "metric_name",
                "fingertips_indicator_id",
                "sex_filter",
                "age_filter",
                "period_range",
            ]
        ].to_string(index=False)
    )

    print()
    print("Validation: PASS")
    print(f"Output written: {OUTPUT_PATH}")
    print()
    print("LOF v0.1 Fingertips crosswalk complete.")


if __name__ == "__main__":
    main()
