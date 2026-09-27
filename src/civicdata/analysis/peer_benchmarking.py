from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[3]

IOD_SUMMARY_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "iod_2025_lad_official_summaries.csv"
)

RELATIONSHIPS_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "mhclg_neighbour_relationships_2026.csv"
)

BENCHMARK_OUTPUT_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "authority_iod_peer_benchmarks_2025.csv"
)

PEER_VALUES_OUTPUT_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "authority_iod_peer_values_2025.csv"
)


# Selected official File 10 measures for the first CivicData
# authority-level deprivation comparison model.
#
# Proportion measures are stored by MHCLG as fractions:
# 0.40 = 40%.
METRICS = {
    "imd_most_deprived_10pct": {
        "column": (
            "imd_proportion_of_lsoas_in_"
            "most_deprived_10pct_nationally"
        ),
        "label": (
            "LSOAs in nationally most deprived 10% - IMD"
        ),
        "domain": "Overall IMD",
        "measure_type": "proportion",
    },
    "income_most_deprived_10pct": {
        "column": (
            "income_proportion_of_lsoas_in_"
            "most_deprived_10pct_nationally"
        ),
        "label": (
            "LSOAs in nationally most deprived 10% - Income"
        ),
        "domain": "Income",
        "measure_type": "proportion",
    },
    "employment_most_deprived_10pct": {
        "column": (
            "employment_proportion_of_lsoas_in_"
            "most_deprived_10pct_nationally"
        ),
        "label": (
            "LSOAs in nationally most deprived 10% - Employment"
        ),
        "domain": "Employment",
        "measure_type": "proportion",
    },
    "education_most_deprived_10pct": {
        "column": (
            "education_proportion_of_lsoas_in_"
            "most_deprived_10pct_nationally"
        ),
        "label": (
            "LSOAs in nationally most deprived 10% - Education"
        ),
        "domain": "Education",
        "measure_type": "proportion",
    },
    "health_most_deprived_10pct": {
        "column": (
            "health_proportion_of_lsoas_in_"
            "most_deprived_10pct_nationally"
        ),
        "label": (
            "LSOAs in nationally most deprived 10% - Health"
        ),
        "domain": "Health",
        "measure_type": "proportion",
    },
    "crime_most_deprived_10pct": {
        "column": (
            "crime_proportion_of_lsoas_in_"
            "most_deprived_10pct_nationally"
        ),
        "label": (
            "LSOAs in nationally most deprived 10% - Crime"
        ),
        "domain": "Crime",
        "measure_type": "proportion",
    },
    "barriers_most_deprived_10pct": {
        "column": (
            "barriers_proportion_of_lsoas_in_"
            "most_deprived_10pct_nationally"
        ),
        "label": (
            "LSOAs in nationally most deprived 10% - "
            "Barriers to Housing and Services"
        ),
        "domain": "Barriers to Housing and Services",
        "measure_type": "proportion",
    },
    "living_environment_most_deprived_10pct": {
        "column": (
            "living_environment_proportion_of_lsoas_in_"
            "most_deprived_10pct_nationally"
        ),
        "label": (
            "LSOAs in nationally most deprived 10% - "
            "Living Environment"
        ),
        "domain": "Living Environment",
        "measure_type": "proportion",
    },
    "idaci_most_deprived_10pct": {
        "column": (
            "idaci_proportion_of_lsoas_in_"
            "most_deprived_10pct_nationally"
        ),
        "label": (
            "LSOAs in nationally most deprived 10% - IDACI"
        ),
        "domain": "IDACI",
        "measure_type": "proportion",
    },
    "idaopi_most_deprived_10pct": {
        "column": (
            "idaopi_proportion_of_lsoas_in_"
            "most_deprived_10pct_nationally"
        ),
        "label": (
            "LSOAs in nationally most deprived 10% - IDAOPI"
        ),
        "domain": "IDAOPI",
        "measure_type": "proportion",
    },
    "imd_extent": {
        "column": "imd_extent",
        "label": "IMD extent",
        "domain": "Overall IMD",
        "measure_type": "official_index_measure",
    },
    "imd_local_concentration": {
        "column": "imd_local_concentration",
        "label": "IMD local concentration",
        "domain": "Overall IMD",
        "measure_type": "official_index_measure",
    },
}


def load_inputs() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load official IoD summaries and MHCLG relationships."""

    iod = pd.read_csv(IOD_SUMMARY_PATH)
    relationships = pd.read_csv(RELATIONSHIPS_PATH)

    return iod, relationships


def validate_inputs(
    iod: pd.DataFrame,
    relationships: pd.DataFrame,
) -> None:
    """Validate required input structure."""

    print("\n=== INPUT VALIDATION ===")

    required_iod_columns = {
        "authority_code",
        "authority_name",
    }

    required_relationship_columns = {
    "local_authority_code",
    "local_authority_name",
    "neighbour_code",
    "neighbour_name",
    "rank",
}

    missing_iod = required_iod_columns - set(iod.columns)
    missing_relationships = (
        required_relationship_columns - set(relationships.columns)
    )

    if missing_iod:
        raise ValueError(
            f"Missing IoD columns: {sorted(missing_iod)}"
        )

    if missing_relationships:
        raise ValueError(
            "Missing relationship columns: "
            f"{sorted(missing_relationships)}"
        )

    missing_metrics = [
        config["column"]
        for config in METRICS.values()
        if config["column"] not in iod.columns
    ]

    if missing_metrics:
        raise ValueError(
            "Missing official IoD metric columns: "
            f"{missing_metrics}"
        )

    if iod["authority_code"].duplicated().any():
        raise ValueError(
            "Duplicate authority codes found in IoD summary."
        )

    print(f"IoD authorities: {len(iod):,}")
    print(f"Official relationships: {len(relationships):,}")
    print(f"Selected metrics: {len(METRICS):,}")
    print("Input validation PASS")


def build_peer_values(
    iod: pd.DataFrame,
    relationships: pd.DataFrame,
) -> pd.DataFrame:
    """
    Build long-format values for every authority, official
    statistical neighbour and selected IoD metric.
    """

    iod_lookup = iod.set_index("authority_code")

    rows = []

    eligible_authorities = iod[
        ["authority_code", "authority_name"]
    ].drop_duplicates()

    for _, authority in eligible_authorities.iterrows():
        authority_code = authority["authority_code"]
        authority_name = authority["authority_name"]

        authority_relationships = relationships[
            relationships["local_authority_code"]
            == authority_code
        ].copy()

        for _, relationship in authority_relationships.iterrows():
            neighbour_code = relationship["neighbour_code"]
            neighbour_name = relationship["neighbour_name"]
            neighbour_rank = relationship["rank"]

            neighbour_available = (
                neighbour_code in iod_lookup.index
            )

            for metric_id, config in METRICS.items():
                if neighbour_available:
                    neighbour_value = iod_lookup.at[
                        neighbour_code,
                        config["column"],
                    ]
                else:
                    neighbour_value = pd.NA

                rows.append(
                    {
                        "authority_code": authority_code,
                        "authority_name": authority_name,
                        "neighbour_code": neighbour_code,
                        "neighbour_name": neighbour_name,
                        "neighbour_rank": neighbour_rank,
                        "metric_id": metric_id,
                        "metric_label": config["label"],
                        "domain": config["domain"],
                        "measure_type": config[
                            "measure_type"
                        ],
                        "neighbour_value": neighbour_value,
                        "iod_available": neighbour_available,
                    }
                )

    return pd.DataFrame(rows)


def build_benchmarks(
    iod: pd.DataFrame,
    peer_values: pd.DataFrame,
) -> pd.DataFrame:
    """
    Build one benchmark row per authority and metric using
    available official statistical-neighbour values.
    """

    rows = []

    for _, authority in iod.iterrows():
        authority_code = authority["authority_code"]
        authority_name = authority["authority_name"]

        for metric_id, config in METRICS.items():
            authority_value = authority[config["column"]]

            peers = peer_values[
                (peer_values["authority_code"] == authority_code)
                & (peer_values["metric_id"] == metric_id)
                & (peer_values["iod_available"])
            ].copy()

            peer_series = pd.to_numeric(
                peers["neighbour_value"],
                errors="coerce",
            ).dropna()

            peer_count_total = int(
                peer_values[
                    (
                        peer_values["authority_code"]
                        == authority_code
                    )
                    & (
                        peer_values["metric_id"]
                        == metric_id
                    )
                ]["neighbour_code"].nunique()
            )

            peer_count_available = int(
                peer_series.count()
            )

            if peer_count_available:
                peer_median = float(
                    peer_series.median()
                )
                peer_q1 = float(
                    peer_series.quantile(0.25)
                )
                peer_q3 = float(
                    peer_series.quantile(0.75)
                )
                peer_min = float(
                    peer_series.min()
                )
                peer_max = float(
                    peer_series.max()
                )
                difference = float(
                    authority_value - peer_median
                )
            else:
                peer_median = pd.NA
                peer_q1 = pd.NA
                peer_q3 = pd.NA
                peer_min = pd.NA
                peer_max = pd.NA
                difference = pd.NA

            coverage_pct = (
                (
                    peer_count_available
                    / peer_count_total
                )
                * 100
                if peer_count_total
                else 0.0
            )

            rows.append(
                {
                    "authority_code": authority_code,
                    "authority_name": authority_name,
                    "metric_id": metric_id,
                    "metric_label": config["label"],
                    "domain": config["domain"],
                    "measure_type": config[
                        "measure_type"
                    ],
                    "authority_value": authority_value,
                    "peer_median": peer_median,
                    "difference_from_peer_median": (
                        difference
                    ),
                    "peer_q1": peer_q1,
                    "peer_q3": peer_q3,
                    "peer_min": peer_min,
                    "peer_max": peer_max,
                    "peer_count_total": peer_count_total,
                    "peer_count_available": (
                        peer_count_available
                    ),
                    "peer_coverage_pct": round(
                        coverage_pct,
                        2,
                    ),
                }
            )

    return pd.DataFrame(rows)


def validate_outputs(
    iod: pd.DataFrame,
    peer_values: pd.DataFrame,
    benchmarks: pd.DataFrame,
) -> None:
    """Validate peer-value and benchmark outputs."""

    print("\n=== OUTPUT VALIDATION ===")

    expected_benchmarks = len(iod) * len(METRICS)

    print(
        f"Expected benchmark rows: "
        f"{expected_benchmarks:,}"
    )
    print(
        f"Actual benchmark rows: "
        f"{len(benchmarks):,}"
    )
    print(
        f"Peer-value rows: "
        f"{len(peer_values):,}"
    )

    if len(benchmarks) != expected_benchmarks:
        raise ValueError(
            "Unexpected benchmark row count."
        )

    duplicate_benchmarks = benchmarks.duplicated(
        subset=[
            "authority_code",
            "metric_id",
        ]
    ).sum()

    if duplicate_benchmarks:
        raise ValueError(
            "Duplicate authority-metric benchmark rows found."
        )

    invalid_peer_counts = benchmarks[
        "peer_count_available"
    ] > benchmarks["peer_count_total"]

    if invalid_peer_counts.any():
        raise ValueError(
            "Available peer count exceeds total peer count."
        )

    zero_peer_benchmarks = int(
        (
            benchmarks["peer_count_available"]
            == 0
        ).sum()
    )

    full_coverage = int(
        (
            benchmarks["peer_count_available"]
            == benchmarks["peer_count_total"]
        ).sum()
    )

    print(
        f"Benchmarks with full peer coverage: "
        f"{full_coverage:,}"
    )
    print(
        f"Benchmarks with zero peer coverage: "
        f"{zero_peer_benchmarks:,}"
    )

    print("Output validation PASS")


def save_outputs(
    peer_values: pd.DataFrame,
    benchmarks: pd.DataFrame,
) -> None:
    """Save Power BI-ready analytical outputs."""

    PEER_VALUES_OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    peer_values.to_csv(
        PEER_VALUES_OUTPUT_PATH,
        index=False,
    )

    benchmarks.to_csv(
        BENCHMARK_OUTPUT_PATH,
        index=False,
    )

    print(
        f"\nPeer values saved to: "
        f"{PEER_VALUES_OUTPUT_PATH}"
    )
    print(
        f"Benchmarks saved to: "
        f"{BENCHMARK_OUTPUT_PATH}"
    )


def show_example(
    benchmarks: pd.DataFrame,
    peer_values: pd.DataFrame,
) -> None:
    """Show an interpretable example using Burnley."""

    metric_id = "imd_most_deprived_10pct"

    benchmark = benchmarks[
        (benchmarks["authority_name"] == "Burnley")
        & (benchmarks["metric_id"] == metric_id)
    ]

    peers = peer_values[
        (peer_values["authority_name"] == "Burnley")
        & (peer_values["metric_id"] == metric_id)
        & (peer_values["iod_available"])
    ].copy()

    if benchmark.empty:
        print("\nBurnley benchmark not found.")
        return

    row = benchmark.iloc[0]

    print("\n=== BURNLEY EXAMPLE ===")
    print(
        "Measure: "
        f"{row['metric_label']}"
    )
    print(
        "Burnley: "
        f"{row['authority_value']:.4f} "
        f"({row['authority_value']:.2%})"
    )
    print(
        "Peer median: "
        f"{row['peer_median']:.4f} "
        f"({row['peer_median']:.2%})"
    )
    print(
        "Difference: "
        f"{row['difference_from_peer_median']:.4f} "
        "proportion points"
    )
    print(
        "Peer coverage: "
        f"{row['peer_count_available']}/"
        f"{row['peer_count_total']}"
    )

    print("\nBurnley's official statistical neighbours:")

    display = peers[
        [
            "neighbour_rank",
            "neighbour_name",
            "neighbour_value",
        ]
    ].sort_values("neighbour_rank")

    display["neighbour_pct"] = (
        pd.to_numeric(
            display["neighbour_value"]
        )
        * 100
    ).round(2)

    print(
        display[
            [
                "neighbour_rank",
                "neighbour_name",
                "neighbour_pct",
            ]
        ].to_string(index=False)
    )


def main() -> None:
    """Run official IoD peer benchmarking."""

    print(
        "\n=== CIVICDATA OFFICIAL IOD "
        "PEER BENCHMARKING ==="
    )

    iod, relationships = load_inputs()

    validate_inputs(
        iod,
        relationships,
    )

    peer_values = build_peer_values(
        iod,
        relationships,
    )

    benchmarks = build_benchmarks(
        iod,
        peer_values,
    )

    validate_outputs(
        iod,
        peer_values,
        benchmarks,
    )

    save_outputs(
        peer_values,
        benchmarks,
    )

    show_example(
        benchmarks,
        peer_values,
    )

    print("\n=== COMPLETE ===")
    print(
        f"Authorities benchmarked: "
        f"{iod['authority_code'].nunique():,}"
    )
    print(
        f"Metrics per authority: "
        f"{len(METRICS):,}"
    )


if __name__ == "__main__":
    main()