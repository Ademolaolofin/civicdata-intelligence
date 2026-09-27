from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[3]

OBSERVATIONS_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "lof_fingertips_observations.csv"
)

AUTHORITY_RELATIONSHIPS_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "mhclg_neighbour_relationships_2026.csv"
)


def build_authority_universe():
    relationships = pd.read_csv(
        AUTHORITY_RELATIONSHIPS_PATH,
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


def main():
    observations = pd.read_csv(
        OBSERVATIONS_PATH,
        dtype={
            "authority_code": str,
            "period": str,
        },
        low_memory=False,
    )

    authority_universe = build_authority_universe()

    print("CivicData Fingertips observation quality diagnostic")
    print("=" * 75)

    print()
    print("OVERALL")
    print("=" * 75)
    print(f"Observation rows       : {len(observations):,}")
    print(
        f"Metrics                : "
        f"{observations['metric_id'].nunique()}"
    )
    print(
        f"Authorities represented: "
        f"{observations['authority_code'].nunique()}"
    )
    print(
        f"CivicData universe     : "
        f"{len(authority_universe)}"
    )
    print(
        f"Missing values         : "
        f"{observations['value'].isna().sum():,}"
    )

    print()
    print("GEOGRAPHY COVERAGE BY METRIC")
    print("=" * 75)

    for metric_id, group in observations.groupby("metric_id"):
        metric_name = group["metric_name"].iloc[0]

        area_types = (
            group["area_type"]
            .value_counts(dropna=False)
            .to_dict()
        )

        authorities = group["authority_code"].nunique()

        print()
        print(metric_name)
        print(f"Metric ID      : {metric_id}")
        print(f"Authorities    : {authorities}")
        print(f"Area types     : {area_types}")

    print()
    print("MISSING VALUES BY METRIC")
    print("=" * 75)

    missing_summary = (
        observations
        .assign(missing_value=observations["value"].isna())
        .groupby(
            [
                "metric_id",
                "metric_name",
            ],
            as_index=False,
        )
        .agg(
            rows=("value", "size"),
            missing_values=("missing_value", "sum"),
        )
    )

    missing_summary["missing_pct"] = (
        missing_summary["missing_values"]
        / missing_summary["rows"]
        * 100
    ).round(2)

    print(
        missing_summary[
            [
                "metric_name",
                "rows",
                "missing_values",
                "missing_pct",
            ]
        ].to_string(index=False)
    )

    print()
    print("MISSING VALUES BY PERIOD")
    print("=" * 75)

    missing = observations.loc[
        observations["value"].isna()
    ].copy()

    if missing.empty:
        print("No missing observation values.")
    else:
        missing_periods = (
            missing
            .groupby(
                [
                    "fingertips_indicator_id",
                    "period",
                ],
                dropna=False,
            )
            .size()
            .reset_index(name="missing_rows")
        )

        print(
            missing_periods.to_string(index=False)
        )

    print()
    print("VALUE NOTES FOR MISSING OBSERVATIONS")
    print("=" * 75)

    if missing.empty:
        print("No missing observation values.")
    else:
        notes = (
            missing["value_note"]
            .fillna("<no value note>")
            .value_counts(dropna=False)
        )

        print(notes.to_string())

    print()
    print("LATEST PERIOD COVERAGE")
    print("=" * 75)

    latest_rows = []

    for metric_id, group in observations.groupby("metric_id"):
        sortable = pd.to_numeric(
            group["period_sortable"],
            errors="coerce",
        )

        latest_sortable = sortable.max()

        latest = group.loc[
            sortable.eq(latest_sortable)
        ].copy()

        latest_rows.append(
            {
                "metric_name": group["metric_name"].iloc[0],
                "latest_period": (
                    latest["period"].iloc[0]
                    if not latest.empty
                    else None
                ),
                "authority_rows": len(latest),
                "authorities": (
                    latest["authority_code"].nunique()
                ),
                "values_available": (
                    latest["value"].notna().sum()
                ),
                "values_missing": (
                    latest["value"].isna().sum()
                ),
            }
        )

    latest_summary = pd.DataFrame(latest_rows)

    print(
        latest_summary.to_string(index=False)
    )

    print()
    print("Diagnostic complete.")


if __name__ == "__main__":
    main()
