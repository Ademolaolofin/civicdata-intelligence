from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[3]

DEPRIVATION_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "authority_deprivation_profile_2025.csv"
)

PEER_COMPARISON_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "authority_deprivation_peer_comparison_2025.csv"
)

OUTPUT_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "authority_deprivation_peer_benchmarks_2025.csv"
)


BENCHMARK_MEASURES = [
    "pct_lsoas_most_deprived_10pct",
    "pct_lsoas_most_deprived_20pct",
    "pct_lsoas_most_deprived_30pct",
    "pct_lsoas_least_deprived_10pct",
    "pct_income_lsoas_most_deprived_10pct",
    "pct_employment_lsoas_most_deprived_10pct",
    "pct_education_lsoas_most_deprived_10pct",
    "pct_health_lsoas_most_deprived_10pct",
    "pct_crime_lsoas_most_deprived_10pct",
    "pct_housing_services_lsoas_most_deprived_10pct",
    "pct_living_environment_lsoas_most_deprived_10pct",
]


def build_peer_benchmarks() -> pd.DataFrame:
    """Build deprivation benchmarks against official statistical neighbours."""

    deprivation = pd.read_csv(DEPRIVATION_PATH)
    peers = pd.read_csv(PEER_COMPARISON_PATH)

    print("\n=== CIVICDATA PEER BENCHMARKING ENGINE ===")
    print(
        "Authorities with deprivation profiles: "
        f"{deprivation['authority_code'].nunique():,}"
    )
    print(f"Official peer relationships: {len(peers):,}")

    benchmark_rows = []

    for _, authority in deprivation.iterrows():
        authority_code = authority["authority_code"]
        authority_name = authority["authority_name"]

        authority_peers = peers[
            peers["local_authority_code"] == authority_code
        ].copy()

        available_peers = authority_peers[
            authority_peers["iod_available"]
        ].copy()

        row = {
            "authority_code": authority_code,
            "authority_name": authority_name,
            "official_neighbour_count": len(authority_peers),
            "iod_peer_count": len(available_peers),
            "iod_peer_coverage_pct": round(
                (len(available_peers) / len(authority_peers)) * 100,
                2,
            )
            if len(authority_peers)
            else 0.0,
        }

        for measure in BENCHMARK_MEASURES:
            peer_column = f"neighbour_{measure}"

            authority_value = authority[measure]

            peer_values = available_peers[
                peer_column
            ].dropna()

            peer_median = (
                peer_values.median()
                if not peer_values.empty
                else pd.NA
            )

            difference = (
                authority_value - peer_median
                if pd.notna(peer_median)
                else pd.NA
            )

            row[f"{measure}_authority"] = authority_value
            row[f"{measure}_peer_median"] = (
                round(float(peer_median), 2)
                if pd.notna(peer_median)
                else pd.NA
            )
            row[f"{measure}_difference"] = (
                round(float(difference), 2)
                if pd.notna(difference)
                else pd.NA
            )

        benchmark_rows.append(row)

    result = pd.DataFrame(benchmark_rows)

    return result.sort_values(
        "authority_name"
    ).reset_index(drop=True)


def validate_benchmarks(
    deprivation: pd.DataFrame,
    benchmarks: pd.DataFrame,
) -> None:
    """Validate peer benchmarking output."""

    print("\n=== PEER BENCHMARK VALIDATION ===")

    expected = deprivation["authority_code"].nunique()

    print(f"Expected authorities: {expected:,}")
    print(f"Benchmark authorities: {len(benchmarks):,}")

    if len(benchmarks) != expected:
        raise ValueError(
            "Benchmark authority count does not match "
            "deprivation profile coverage."
        )

    if benchmarks["authority_code"].duplicated().any():
        raise ValueError(
            "Duplicate authority codes detected in benchmarks."
        )

    invalid_peer_counts = (
        benchmarks["iod_peer_count"]
        > benchmarks["official_neighbour_count"]
    )

    if invalid_peer_counts.any():
        raise ValueError(
            "IoD peer count exceeds official neighbour count."
        )

    invalid_coverage = ~benchmarks[
        "iod_peer_coverage_pct"
    ].between(0, 100)

    if invalid_coverage.any():
        raise ValueError(
            "Invalid peer coverage percentage detected."
        )

    no_peer_data = int(
        (benchmarks["iod_peer_count"] == 0).sum()
    )

    full_coverage = int(
        (
            benchmarks["iod_peer_count"]
            == benchmarks["official_neighbour_count"]
        ).sum()
    )

    print(
        "Authorities with full IoD peer coverage: "
        f"{full_coverage:,}"
    )
    print(
        "Authorities with zero IoD peer coverage: "
        f"{no_peer_data:,}"
    )

    print("Validation PASS")


def save_benchmarks(
    benchmarks: pd.DataFrame,
) -> Path:
    """Save authority peer benchmarks."""

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    benchmarks.to_csv(
        OUTPUT_PATH,
        index=False,
    )

    print(f"\nSaved to: {OUTPUT_PATH}")

    return OUTPUT_PATH


def main() -> None:
    """Build, validate and save peer benchmarks."""

    deprivation = pd.read_csv(DEPRIVATION_PATH)

    benchmarks = build_peer_benchmarks()

    validate_benchmarks(
        deprivation,
        benchmarks,
    )

    save_benchmarks(benchmarks)

    print("\n=== OUTPUT SUMMARY ===")
    print(f"Authorities: {len(benchmarks):,}")
    print(f"Columns: {len(benchmarks.columns):,}")

    print(
        "\nExample benchmark: "
        "share of LSOAs in nationally most deprived 10%"
    )

    preview = benchmarks[
        [
            "authority_name",
            "pct_lsoas_most_deprived_10pct_authority",
            "pct_lsoas_most_deprived_10pct_peer_median",
            "pct_lsoas_most_deprived_10pct_difference",
            "iod_peer_count",
        ]
    ].sort_values(
        "pct_lsoas_most_deprived_10pct_difference",
        ascending=False,
    ).head(10)

    print(preview.to_string(index=False))


if __name__ == "__main__":
    main()