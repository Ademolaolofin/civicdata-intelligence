from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[3]

SOURCE_PATH = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "ons_healthy_life_expectancy_2022_2024.xlsx"
)

MHCLG_RELATIONSHIPS_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "mhclg_neighbour_relationships_2026.csv"
)

METRIC_DIMENSION_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "lof_v01_metric_dimension.csv"
)

CROSSWALK_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "lof_v01_lg_inform_crosswalk.csv"
)

OUTPUT_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "lof_ons_hle_observations.csv"
)

HLE_METRIC_ID = "lof_metric_814e15097abc"

SOURCE_URL = (
    "https://www.ons.gov.uk/peoplepopulationandcommunity/"
    "healthandsocialcare/healthandlifeexpectancies/datasets/"
    "healthstatelifeexpectancyallagesuk/current"
)

EXPECTED_COMPONENTS = {
    "Male": 3155,
    "Female": 3156,
}


def load_authority_universe():
    relationships = pd.read_csv(
        MHCLG_RELATIONSHIPS_PATH,
        dtype=str,
    )

    authorities = pd.concat(
        [
            relationships[
                ["local_authority_code", "local_authority_name"]
            ].rename(
                columns={
                    "local_authority_code": "authority_code",
                    "local_authority_name": "authority_name",
                }
            ),
            relationships[
                ["neighbour_code", "neighbour_name"]
            ].rename(
                columns={
                    "neighbour_code": "authority_code",
                    "neighbour_name": "authority_name",
                }
            ),
        ],
        ignore_index=True,
    )

    return (
        authorities
        .drop_duplicates(subset=["authority_code"])
        .sort_values("authority_code")
        .reset_index(drop=True)
    )


def load_metric_name():
    metrics = pd.read_csv(
        METRIC_DIMENSION_PATH,
        dtype=str,
    )

    match = metrics.loc[
        metrics["metric_id"].eq(HLE_METRIC_ID)
    ]

    if len(match) != 1:
        raise ValueError(
            f"Expected exactly one metric dimension row "
            f"for {HLE_METRIC_ID}, found {len(match)}."
        )

    return match.iloc[0]["metric_name"]


def validate_lg_inform_components():
    crosswalk = pd.read_csv(
        CROSSWALK_PATH,
        dtype=str,
    )

    metric_rows = crosswalk.loc[
        crosswalk["metric_id"].eq(HLE_METRIC_ID)
    ].copy()

    if metric_rows.empty:
        raise ValueError(
            "Healthy Life Expectancy is missing from "
            "the LOF/LG Inform crosswalk."
        )

    found_ids = set(
        pd.to_numeric(
            metric_rows["lg_inform_metric_id"],
            errors="coerce",
        )
        .dropna()
        .astype(int)
    )

    expected_ids = set(EXPECTED_COMPONENTS.values())

    if found_ids != expected_ids:
        raise ValueError(
            "Unexpected LG Inform component IDs for HLE. "
            f"Expected {sorted(expected_ids)}, "
            f"found {sorted(found_ids)}."
        )

    print(
        "LG Inform HLE components    : "
        f"{sorted(found_ids)}"
    )


def parse_period_start(period):
    text = str(period).strip()

    try:
        return int(text[:4])
    except (TypeError, ValueError):
        return pd.NA


def main():
    print("CivicData LOF ONS Healthy Life Expectancy ingestion")
    print("=" * 75)

    metric_name = load_metric_name()
    validate_lg_inform_components()

    authorities = load_authority_universe()
    authority_codes = set(
        authorities["authority_code"]
    )

    print(
        f"CivicData authority universe : "
        f"{len(authorities)}"
    )

    raw = pd.read_excel(
        SOURCE_PATH,
        sheet_name="1",
        header=6,
        engine="openpyxl",
        dtype={
            "Area code": str,
        },
    )

    print(
        f"ONS Sheet 1 rows             : "
        f"{len(raw):,}"
    )

    required_columns = {
        "Period",
        "Country",
        "Area type",
        "Area code",
        "Area name",
        "Sex",
        "Age group",
        "HLE",
        "LCI",
        "UCI",
        "Proportion (%)",
    }

    missing_columns = (
        required_columns - set(raw.columns)
    )

    if missing_columns:
        raise ValueError(
            "ONS workbook is missing expected columns: "
            f"{sorted(missing_columns)}"
        )

    hle = raw.loc[
        raw["Country"].eq("England")
        & raw["Area type"].eq("Local Areas")
        & raw["Age group"].eq("<1")
        & raw["Sex"].isin(
            EXPECTED_COMPONENTS.keys()
        )
    ].copy()

    print(
        f"England HLE-at-birth rows    : "
        f"{len(hle):,}"
    )
    print(
        f"ONS local authority codes    : "
        f"{hle['Area code'].nunique():,}"
    )
    print(
        f"Periods                      : "
        f"{hle['Period'].nunique():,}"
    )
    print(
        f"Sex components               : "
        f"{sorted(hle['Sex'].dropna().unique().tolist())}"
    )

    hle = hle.loc[
        hle["Area code"].isin(
            authority_codes
        )
    ].copy()

    print(
        f"CivicData matched rows       : "
        f"{len(hle):,}"
    )
    print(
        f"CivicData matched authorities: "
        f"{hle['Area code'].nunique():,}"
    )

    hle["lg_inform_metric_id"] = (
        hle["Sex"].map(
            EXPECTED_COMPONENTS
        )
    )

    hle["period_start"] = (
        hle["Period"]
        .apply(parse_period_start)
        .astype("Int64")
    )

    observations = pd.DataFrame(
        {
            "metric_id": HLE_METRIC_ID,
            "metric_name": metric_name,
            "component": hle["Sex"],
            "lg_inform_metric_id": (
                hle["lg_inform_metric_id"]
            ),
            "authority_code": hle["Area code"],
            "authority_name": hle["Area name"],
            "area_type": hle["Area type"],
            "sex": hle["Sex"],
            "age": "At birth",
            "period": hle["Period"],
            "period_start": hle["period_start"],
            "period_range": "3y",
            "value": pd.to_numeric(
                hle["HLE"],
                errors="coerce",
            ),
            "lower_ci_95": pd.to_numeric(
                hle["LCI"],
                errors="coerce",
            ),
            "upper_ci_95": pd.to_numeric(
                hle["UCI"],
                errors="coerce",
            ),
            "proportion_life_good_health_pct": (
                pd.to_numeric(
                    hle["Proportion (%)"],
                    errors="coerce",
                )
            ),
            "unit": "Years",
            "source_provider": (
                "Office for National Statistics"
            ),
            "source_system": (
                "ONS Healthy life expectancy, UK"
            ),
            "source_url": SOURCE_URL,
        }
    )

    duplicate_key = [
        "metric_id",
        "component",
        "authority_code",
        "period",
    ]

    duplicate_rows = observations.duplicated(
        subset=duplicate_key
    ).sum()

    unknown_codes = (
        set(
            observations[
                "authority_code"
            ].dropna()
        )
        - authority_codes
    )

    missing_values = observations[
        "value"
    ].isna().sum()

    component_counts = (
        observations
        .groupby("component")
        ["authority_code"]
        .nunique()
        .to_dict()
    )

    print()
    print("VALIDATION")
    print("=" * 75)
    print(
        f"Observation rows             : "
        f"{len(observations):,}"
    )
    print(
        f"Unique authorities           : "
        f"{observations['authority_code'].nunique():,}"
    )
    print(
        f"Unique periods               : "
        f"{observations['period'].nunique():,}"
    )
    print(
        f"Components                   : "
        f"{sorted(observations['component'].unique().tolist())}"
    )
    print(
        f"Authorities by component     : "
        f"{component_counts}"
    )
    print(
        f"Duplicate component/area/time: "
        f"{duplicate_rows}"
    )
    print(
        f"Rows with unavailable HLE    : "
        f"{missing_values}"
    )
    print(
        f"Unknown authority codes      : "
        f"{len(unknown_codes)}"
    )

    if observations.empty:
        raise ValueError(
            "No HLE observations were produced."
        )

    if set(
        observations["component"].unique()
    ) != set(EXPECTED_COMPONENTS):
        raise ValueError(
            "Male and Female HLE components "
            "were not both produced."
        )

    if duplicate_rows:
        raise ValueError(
            "Duplicate HLE component/authority/"
            "period observations found."
        )

    if unknown_codes:
        raise ValueError(
            "HLE observations contain codes outside "
            "the CivicData authority universe: "
            f"{sorted(unknown_codes)}"
        )

    if missing_values:
        raise ValueError(
            "One or more selected HLE observations "
            "have no numeric HLE value."
        )

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    observations = observations.sort_values(
        [
            "authority_code",
            "component",
            "period_start",
        ]
    ).reset_index(drop=True)

    observations.to_csv(
        OUTPUT_PATH,
        index=False,
    )

    print()
    print("PERIOD COVERAGE")
    print("=" * 75)

    period_summary = (
        observations
        .groupby(
            [
                "period_start",
                "period",
            ],
            as_index=False,
        )
        .agg(
            observations=(
                "authority_code",
                "size",
            ),
            authorities=(
                "authority_code",
                "nunique",
            ),
        )
        .sort_values("period_start")
    )

    print(
        period_summary.to_string(
            index=False
        )
    )

    print()
    print("Validation: PASS")
    print(
        f"Output written: {OUTPUT_PATH}"
    )
    print()
    print(
        "LOF ONS Healthy Life Expectancy "
        "ingestion complete."
    )


if __name__ == "__main__":
    main()
