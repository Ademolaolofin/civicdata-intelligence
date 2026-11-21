from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[3]

RAW_PATH = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "dfe"
    / "eyfs_headline_measures_child_characteristics_2024_25.csv"
)

MHCLG_PATH = (
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

OUTPUT_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "lof_dfe_eyfs_observations.csv"
)


GLD_METRIC_ID = "lof_metric_dbd49799b5ab"
FSM_GAP_METRIC_ID = "lof_metric_c7904d3d7fa2"

GLD_LG_INFORM_ID = 19346
FSM_GAP_LG_INFORM_ID = 27666

SOURCE_DATASET_ID = (
    "019ac0fb-e082-7202-871f-439d6d036893"
)

SOURCE_DATASET_VERSION = "1.0.1"

SOURCE_URL = (
    "https://api.education.gov.uk/statistics/v1/data-sets/"
    f"{SOURCE_DATASET_ID}/csv"
    f"?dataSetVersion={SOURCE_DATASET_VERSION}"
)

FSM_ELIGIBLE = "Eligible for free school meals"
FSM_NOT_ELIGIBLE = "Not eligible for free school meals"


def load_authority_universe():
    relationships = pd.read_csv(
        MHCLG_PATH,
        dtype=str,
    )

    authorities = pd.concat(
        [
            relationships[
                [
                    "local_authority_code",
                    "local_authority_name",
                ]
            ].rename(
                columns={
                    "local_authority_code": "authority_code",
                    "local_authority_name": "authority_name",
                }
            ),
            relationships[
                [
                    "neighbour_code",
                    "neighbour_name",
                ]
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
        .drop_duplicates(
            subset=["authority_code"]
        )
        .sort_values("authority_code")
        .reset_index(drop=True)
    )


def load_metric_names():
    dimension = pd.read_csv(
        METRIC_DIMENSION_PATH,
        dtype=str,
    )

    target_ids = {
        GLD_METRIC_ID,
        FSM_GAP_METRIC_ID,
    }

    selected = dimension.loc[
        dimension["metric_id"].isin(
            target_ids
        ),
        [
            "metric_id",
            "metric_name",
        ],
    ].drop_duplicates()

    if set(selected["metric_id"]) != target_ids:
        raise ValueError(
            "Could not resolve both EYFS metrics "
            "from the CivicData metric dimension."
        )

    return dict(
        zip(
            selected["metric_id"],
            selected["metric_name"],
        )
    )


def normalise_academic_year(value):
    text = str(value).strip()

    if len(text) != 6 or not text.isdigit():
        return pd.NA

    start_year = int(text[:4])
    end_suffix = text[4:]

    return (
        f"{start_year}/{end_suffix}"
    )


def prepare_geography(df):
    """
    Convert DfE's two English local geography types
    into one CivicData authority-code field.

    Local authority:
        use new_la_code

    Local authority district:
        use lad_code
    """

    local_authority = df.loc[
        df["geographic_level"].eq(
            "Local authority"
        )
    ].copy()

    local_authority[
        "authority_code"
    ] = local_authority["new_la_code"]

    local_authority[
        "source_area_name"
    ] = local_authority["la_name"]

    local_authority[
        "source_geography"
    ] = "Local authority"

    districts = df.loc[
        df["geographic_level"].eq(
            "Local authority district"
        )
    ].copy()

    districts[
        "authority_code"
    ] = districts["lad_code"]

    districts[
        "source_area_name"
    ] = districts["lad_name"]

    districts[
        "source_geography"
    ] = "Local authority district"

    combined = pd.concat(
        [
            districts,
            local_authority,
        ],
        ignore_index=True,
    )

    return combined


def select_one_geography_per_authority(
    df,
    authority_codes,
):
    """
    Retain one DfE geography record per CivicData authority.

    Selection hierarchy:
        1. Local authority
        2. Local authority district as fallback

    Local authority and local authority district records
    are not assumed to be interchangeable. Where both
    exist for the same authority and source series,
    Local authority is preferred.

    The selected source geography is retained for
    provenance and subsequent validation.
    """

    selected = df.loc[
        df["authority_code"].isin(
            authority_codes
        )
    ].copy()

    geography_priority = {
        "Local authority": 1,
        "Local authority district": 2,
    }

    selected["_geography_priority"] = (
        selected["source_geography"].map(
            geography_priority
        )
    )

    if selected["_geography_priority"].isna().any():
        unexpected = (
            selected.loc[
                selected["_geography_priority"].isna(),
                "source_geography",
            ]
            .drop_duplicates()
            .tolist()
        )

        raise ValueError(
            "Unexpected DfE geography levels: "
            f"{unexpected}"
        )

    identifying_columns = [
        "time_period",
        "authority_code",
        "breakdown_topic",
        "breakdown",
        "sex",
    ]

    selected = (
        selected
        .sort_values(
            identifying_columns
            + ["_geography_priority"]
        )
        .drop_duplicates(
            subset=identifying_columns,
            keep="first",
        )
        .drop(
            columns=["_geography_priority"]
        )
        .reset_index(drop=True)
    )

    duplicates = selected.duplicated(
        subset=identifying_columns
    ).sum()

    if duplicates:
        raise ValueError(
            "Geography selection produced duplicate "
            "source observations."
        )

    return selected


def build_gld_observations(
    source,
    metric_names,
):
    gld = source.loc[
        source["breakdown_topic"].eq("Total")
        & source["breakdown"].eq("Total")
        & source["sex"].eq("Total")
    ].copy()

    result = pd.DataFrame(
        {
            "metric_id": GLD_METRIC_ID,
            "metric_name": (
                metric_names[GLD_METRIC_ID]
            ),
            "lg_inform_metric_id": (
                GLD_LG_INFORM_ID
            ),
            "authority_code": (
                gld["authority_code"]
            ),
            "authority_name": (
                gld["source_area_name"]
            ),
            "source_geography": (
                gld["source_geography"]
            ),
            "time_period": (
                gld["time_period"]
            ),
            "period": (
                gld["time_period"]
                .apply(
                    normalise_academic_year
                )
            ),
            "period_type": "Academic year",
            "value": pd.to_numeric(
                gld["gld_children_percent"],
                errors="coerce",
            ),
            "numerator": pd.to_numeric(
                gld["gld_children_count"],
                errors="coerce",
            ),
            "denominator": pd.to_numeric(
                gld["children_count"],
                errors="coerce",
            ),
            "unit": "Per cent",
            "calculation_type": (
                "direct_source_measure"
            ),
            "component_eligible_fsm_pct": (
                pd.NA
            ),
            "component_not_eligible_fsm_pct": (
                pd.NA
            ),
            "source_provider": (
                "Department for Education"
            ),
            "source_system": (
                "Explore Education Statistics"
            ),
            "source_dataset": (
                "EYFS headline measures "
                "by child characteristics"
            ),
            "source_dataset_id": (
                SOURCE_DATASET_ID
            ),
            "source_dataset_version": (
                SOURCE_DATASET_VERSION
            ),
            "source_url": SOURCE_URL,
        }
    )

    return result


def build_fsm_gap_observations(
    source,
    metric_names,
):
    fsm = source.loc[
        source["breakdown_topic"].eq(
            "Free school meal eligibility"
        )
        & source["breakdown"].isin(
            [
                FSM_ELIGIBLE,
                FSM_NOT_ELIGIBLE,
            ]
        )
        & source["sex"].eq("Total")
    ].copy()

    fsm[
        "gld_children_percent"
    ] = pd.to_numeric(
        fsm["gld_children_percent"],
        errors="coerce",
    )

    key = [
        "time_period",
        "authority_code",
        "source_area_name",
        "source_geography",
    ]

    pivot = (
        fsm.pivot_table(
            index=key,
            columns="breakdown",
            values="gld_children_percent",
            aggfunc="first",
        )
        .reset_index()
    )

    required_components = {
        FSM_ELIGIBLE,
        FSM_NOT_ELIGIBLE,
    }

    missing_components = (
        required_components
        - set(pivot.columns)
    )

    if missing_components:
        raise ValueError(
            "FSM source components missing: "
            f"{sorted(missing_components)}"
        )

    pivot["fsm_gap_percentage_points"] = (
        pivot[FSM_NOT_ELIGIBLE]
        - pivot[FSM_ELIGIBLE]
    )

    result = pd.DataFrame(
        {
            "metric_id": (
                FSM_GAP_METRIC_ID
            ),
            "metric_name": (
                metric_names[
                    FSM_GAP_METRIC_ID
                ]
            ),
            "lg_inform_metric_id": (
                FSM_GAP_LG_INFORM_ID
            ),
            "authority_code": (
                pivot["authority_code"]
            ),
            "authority_name": (
                pivot["source_area_name"]
            ),
            "source_geography": (
                pivot["source_geography"]
            ),
            "time_period": (
                pivot["time_period"]
            ),
            "period": (
                pivot["time_period"]
                .apply(
                    normalise_academic_year
                )
            ),
            "period_type": (
                "Academic year"
            ),
            "value": (
                pivot[
                    "fsm_gap_percentage_points"
                ]
            ),
            "numerator": pd.NA,
            "denominator": pd.NA,
            "unit": "Percentage point",
            "calculation_type": (
                "derived_from_source_components"
            ),
            "component_eligible_fsm_pct": (
                pivot[FSM_ELIGIBLE]
            ),
            "component_not_eligible_fsm_pct": (
                pivot[FSM_NOT_ELIGIBLE]
            ),
            "source_provider": (
                "Department for Education"
            ),
            "source_system": (
                "Explore Education Statistics"
            ),
            "source_dataset": (
                "EYFS headline measures "
                "by child characteristics"
            ),
            "source_dataset_id": (
                SOURCE_DATASET_ID
            ),
            "source_dataset_version": (
                SOURCE_DATASET_VERSION
            ),
            "source_url": SOURCE_URL,
        }
    )

    return result


def validate(
    observations,
    authority_codes,
):
    duplicate_key = [
        "metric_id",
        "authority_code",
        "time_period",
    ]

    duplicates = (
        observations
        .duplicated(
            subset=duplicate_key
        )
        .sum()
    )

    unknown_codes = (
        set(
            observations[
                "authority_code"
            ].dropna()
        )
        - authority_codes
    )

    missing_periods = (
        observations[
            "period"
        ].isna().sum()
    )

    missing_values = (
        observations[
            "value"
        ].isna().sum()
    )

    metric_counts = (
        observations
        .groupby("metric_id")
        .agg(
            observations=(
                "authority_code",
                "size",
            ),
            authorities=(
                "authority_code",
                "nunique",
            ),
            periods=(
                "time_period",
                "nunique",
            ),
        )
    )

    geography_counts = (
        observations
        .groupby(
            [
                "metric_id",
                "source_geography",
            ]
        )
        .size()
    )

    print()
    print("VALIDATION")
    print("=" * 75)

    print(
        f"Observation rows             : "
        f"{len(observations):,}"
    )

    print(
        f"Metrics                      : "
        f"{observations['metric_id'].nunique()}"
    )

    print(
        f"Unique authorities           : "
        f"{observations['authority_code'].nunique()}"
    )

    print(
        f"Duplicate metric/area/period : "
        f"{duplicates}"
    )

    print(
        f"Unknown authority codes      : "
        f"{len(unknown_codes)}"
    )

    print(
        f"Missing period labels        : "
        f"{missing_periods}"
    )

    print(
        f"Rows with unavailable value  : "
        f"{missing_values}"
    )

    print()
    print("METRIC COVERAGE")
    print("=" * 75)
    print(metric_counts.to_string())

    print()
    print("GEOGRAPHY COVERAGE")
    print("=" * 75)
    print(geography_counts.to_string())

    if duplicates:
        raise ValueError(
            "Duplicate EYFS metric/authority/"
            "period observations found."
        )

    if unknown_codes:
        raise ValueError(
            "EYFS observations contain authority "
            "codes outside the CivicData universe."
        )

    if missing_periods:
        raise ValueError(
            "One or more EYFS observations have "
            "an invalid academic-year value."
        )

    if set(
        observations["metric_id"].unique()
    ) != {
        GLD_METRIC_ID,
        FSM_GAP_METRIC_ID,
    }:
        raise ValueError(
            "Both expected EYFS metrics were "
            "not produced."
        )

    print()
    print("Validation: PASS")


def main():
    print("CivicData LOF DfE EYFS ingestion")
    print("=" * 75)

    authorities = (
        load_authority_universe()
    )

    authority_codes = set(
        authorities["authority_code"]
    )

    metric_names = load_metric_names()

    print(
        f"CivicData authority universe : "
        f"{len(authority_codes)}"
    )

    raw = pd.read_csv(
        RAW_PATH,
        low_memory=False,
        dtype={
            "new_la_code": str,
            "lad_code": str,
        },
    )

    print(
        f"DfE source rows              : "
        f"{len(raw):,}"
    )

    required_columns = {
        "time_period",
        "time_identifier",
        "geographic_level",
        "new_la_code",
        "la_name",
        "lad_code",
        "lad_name",
        "breakdown_topic",
        "breakdown",
        "sex",
        "children_count",
        "gld_children_count",
        "gld_children_percent",
    }

    missing_columns = (
        required_columns
        - set(raw.columns)
    )

    if missing_columns:
        raise ValueError(
            "DfE EYFS dataset is missing "
            "expected columns: "
            f"{sorted(missing_columns)}"
        )

    local = prepare_geography(raw)

    local = (
        select_one_geography_per_authority(
            local,
            authority_codes,
        )
    )

    print(
        f"Matched source rows          : "
        f"{len(local):,}"
    )

    print(
        f"Matched authority codes      : "
        f"{local['authority_code'].nunique()}"
    )

    gld = build_gld_observations(
        local,
        metric_names,
    )

    fsm_gap = (
        build_fsm_gap_observations(
            local,
            metric_names,
        )
    )

    observations = pd.concat(
        [
            gld,
            fsm_gap,
        ],
        ignore_index=True,
    )

    observations = (
        observations
        .sort_values(
            [
                "metric_id",
                "authority_code",
                "time_period",
            ]
        )
        .reset_index(drop=True)
    )

    validate(
        observations,
        authority_codes,
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
    print("PERIOD COVERAGE")
    print("=" * 75)

    summary = (
        observations
        .groupby(
            [
                "metric_id",
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
            available_values=(
                "value",
                "count",
            ),
        )
        .sort_values(
            [
                "metric_id",
                "period",
            ]
        )
    )

    print(
        summary.to_string(
            index=False
        )
    )

    print()
    print(
        f"Output written: {OUTPUT_PATH}"
    )
    print()
    print(
        "LOF DfE EYFS ingestion complete."
    )


if __name__ == "__main__":
    main()
