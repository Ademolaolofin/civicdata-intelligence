from io import StringIO
from pathlib import Path
import time

import pandas as pd
import requests


PROJECT_ROOT = Path(__file__).resolve().parents[3]

CROSSWALK_PATH = (
    PROJECT_ROOT / "data" / "processed" / "lof_v01_fingertips_crosswalk.csv"
)

MHCLG_RELATIONSHIPS_PATH = (
    PROJECT_ROOT / "data" / "processed" / "mhclg_neighbour_relationships_2026.csv"
)

RAW_DIR = PROJECT_ROOT / "data" / "raw" / "fingertips"

OUTPUT_PATH = (
    PROJECT_ROOT / "data" / "processed" / "lof_fingertips_observations.csv"
)

API_URL = (
    "https://fingertips.phe.org.uk/api/all_data/csv/by_indicator_id"
)

REQUEST_TIMEOUT = 120


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

    authorities = (
        authorities
        .drop_duplicates(subset=["authority_code"])
        .sort_values("authority_code")
        .reset_index(drop=True)
    )

    if authorities["authority_code"].duplicated().any():
        raise ValueError(
            "Duplicate authority codes in CivicData authority universe."
        )

    return authorities


def download_indicator(indicator_id):
    response = requests.get(
        API_URL,
        params={"indicator_ids": indicator_id},
        timeout=REQUEST_TIMEOUT,
    )

    response.raise_for_status()

    content_type = response.headers.get(
        "content-type",
        "",
    )

    if "csv" not in content_type.lower():
        raise ValueError(
            f"Indicator {indicator_id} did not return CSV. "
            f"Content-Type: {content_type}"
        )

    RAW_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    raw_path = (
        RAW_DIR
        / f"fingertips_indicator_{indicator_id}.csv"
    )

    raw_path.write_bytes(response.content)

    data = pd.read_csv(
        StringIO(response.text),
        low_memory=False,
        dtype={
            "Indicator ID": "Int64",
            "Area Code": str,
            "Parent Code": str,
        },
    )

    if data.empty:
        raise ValueError(
            f"Indicator {indicator_id} returned no observations."
        )

    returned_ids = set(
        data["Indicator ID"]
        .dropna()
        .astype(int)
        .unique()
    )

    if returned_ids != {indicator_id}:
        raise ValueError(
            f"Unexpected indicator IDs returned for "
            f"{indicator_id}: {sorted(returned_ids)}"
        )

    return data, raw_path


def filter_indicator(data, mapping):
    filtered = data.loc[
        data["Sex"].eq(mapping["sex_filter"])
        & data["Age"].eq(mapping["age_filter"])
        & data["Category Type"].isna()
        & data["Time period range"].eq(
            mapping["period_range"]
        )
    ].copy()

    if filtered.empty:
        raise ValueError(
            "Validated series filter returned no observations "
            f"for indicator "
            f"{int(mapping['fingertips_indicator_id'])}."
        )

    return filtered


def normalise_indicator(
    filtered,
    mapping,
    authority_codes,
):
    filtered = filtered.loc[
        filtered["Area Code"].isin(
            authority_codes
        )
    ].copy()

    if filtered.empty:
        raise ValueError(
            "No observations intersect the CivicData "
            f"authority universe for indicator "
            f"{int(mapping['fingertips_indicator_id'])}."
        )

    normalised = pd.DataFrame(
        {
            "metric_id": mapping["metric_id"],
            "metric_name": mapping["metric_name"],
            "fingertips_indicator_id": int(
                mapping["fingertips_indicator_id"]
            ),
            "fingertips_indicator_name": filtered[
                "Indicator Name"
            ],
            "authority_code": filtered["Area Code"],
            "authority_name": filtered["Area Name"],
            "area_type": filtered["Area Type"],
            "sex": filtered["Sex"],
            "age": filtered["Age"],
            "period": filtered[
                "Time period"
            ].astype(str),
            "period_sortable": filtered[
                "Time period Sortable"
            ],
            "period_range": filtered[
                "Time period range"
            ],
            "value": pd.to_numeric(
                filtered["Value"],
                errors="coerce",
            ),
            "lower_ci_95": pd.to_numeric(
                filtered["Lower CI 95.0 limit"],
                errors="coerce",
            ),
            "upper_ci_95": pd.to_numeric(
                filtered["Upper CI 95.0 limit"],
                errors="coerce",
            ),
            "count": pd.to_numeric(
                filtered["Count"],
                errors="coerce",
            ),
            "denominator": pd.to_numeric(
                filtered["Denominator"],
                errors="coerce",
            ),
            "value_note": filtered[
                "Value note"
            ],
            "recent_trend": filtered[
                "Recent Trend"
            ],
            "comparison_to_england": filtered[
                "Compared to England value or percentiles"
            ],
            "source_provider": mapping[
                "source_provider"
            ],
            "source_system": "OHID Fingertips",
            "source_url": API_URL,
        }
    )

    return normalised


def validate_observations(
    observations,
    crosswalk,
    authority_codes,
):
    expected_metrics = crosswalk[
        "metric_id"
    ].nunique()

    actual_metrics = observations[
        "metric_id"
    ].nunique()

    duplicate_key = [
        "metric_id",
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

    missing = observations.loc[
        observations["value"].isna()
    ].copy()

    missing_without_note = missing[
        "value_note"
    ].isna().sum()

    print()
    print("FINAL VALIDATION")
    print("=" * 70)

    print(
        f"Expected metrics             : "
        f"{expected_metrics}"
    )
    print(
        f"Metrics with observations    : "
        f"{actual_metrics}"
    )
    print(
        f"Observation rows             : "
        f"{len(observations):,}"
    )
    print(
        f"Unique authorities           : "
        f"{observations['authority_code'].nunique()}"
    )
    print(
        f"Duplicate metric/area/period : "
        f"{duplicate_rows}"
    )
    print(
        f"Rows with unavailable value  : "
        f"{len(missing):,}"
    )
    print(
        f"Unavailable rows with note   : "
        f"{len(missing) - missing_without_note:,}"
    )
    print(
        f"Unavailable rows without note: "
        f"{missing_without_note:,}"
    )
    print(
        f"Unknown authority codes      : "
        f"{len(unknown_codes)}"
    )

    if actual_metrics != expected_metrics:
        raise ValueError(
            "Not all Fingertips metrics produced observations."
        )

    if duplicate_rows:
        raise ValueError(
            "Duplicate metric/authority/period "
            "observations found."
        )

    if unknown_codes:
        raise ValueError(
            "Observations contain authority codes "
            "outside the CivicData authority universe: "
            f"{sorted(unknown_codes)}"
        )

    if missing_without_note:
        raise ValueError(
            "One or more unavailable observations have "
            "no source value note explaining the absence."
        )

    print(
        "Validation: PASS "
        "(source-suppressed/unavailable values preserved)"
    )


def main():
    print(
        "CivicData LOF Fingertips observation ingestion"
    )
    print("=" * 70)

    crosswalk = pd.read_csv(
        CROSSWALK_PATH
    )

    authorities = load_authority_universe()

    authority_codes = set(
        authorities["authority_code"]
    )

    print(
        f"CivicData authority universe : "
        f"{len(authorities)}"
    )
    print(
        f"Fingertips metrics           : "
        f"{len(crosswalk)}"
    )

    outputs = []

    for index, mapping in crosswalk.iterrows():
        indicator_id = int(
            mapping["fingertips_indicator_id"]
        )

        print()
        print("-" * 70)
        print(
            f"Downloading {indicator_id}: "
            f"{mapping['metric_name']}"
        )

        data, raw_path = download_indicator(
            indicator_id
        )

        print(
            f"Raw rows downloaded          : "
            f"{len(data):,}"
        )
        print(
            f"Raw file                     : "
            f"{raw_path}"
        )

        filtered = filter_indicator(
            data,
            mapping,
        )

        print(
            f"Rows after series filter     : "
            f"{len(filtered):,}"
        )
        print(
            f"Series areas                 : "
            f"{filtered['Area Code'].nunique():,}"
        )
        print(
            f"Series periods               : "
            f"{filtered['Time period'].nunique():,}"
        )

        normalised = normalise_indicator(
            filtered,
            mapping,
            authority_codes,
        )

        print(
            f"CivicData authority rows     : "
            f"{len(normalised):,}"
        )
        print(
            f"CivicData authorities        : "
            f"{normalised['authority_code'].nunique():,}"
        )

        outputs.append(normalised)

        if index < len(crosswalk) - 1:
            time.sleep(0.5)

    observations = pd.concat(
        outputs,
        ignore_index=True,
    )

    observations = observations.sort_values(
        [
            "metric_id",
            "authority_code",
            "period_sortable",
        ],
        na_position="last",
    ).reset_index(drop=True)

    validate_observations(
        observations,
        crosswalk,
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
    print("METRIC SUMMARY")
    print("=" * 70)

    summary = (
        observations
        .groupby(
            [
                "metric_name",
                "fingertips_indicator_id",
            ],
            dropna=False,
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
            periods=(
                "period",
                "nunique",
            ),
            values_available=(
                "value",
                "count",
            ),
        )
        .reset_index()
    )

    summary["values_unavailable"] = (
        summary["observations"]
        - summary["values_available"]
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
        "LOF Fingertips observation "
        "ingestion complete."
    )


if __name__ == "__main__":
    main()
