from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[3]

RELATIONSHIPS_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "mhclg_neighbour_relationships_2026.csv"
)

DEPRIVATION_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "authority_deprivation_profile_2025.csv"
)

OUTPUT_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "authority_deprivation_peer_comparison_2025.csv"
)


def build_peer_comparison() -> pd.DataFrame:
    """Attach IoD profiles to official MHCLG statistical neighbours."""

    relationships = pd.read_csv(RELATIONSHIPS_PATH)
    deprivation = pd.read_csv(DEPRIVATION_PATH)

    print("\n=== CIVICDATA PEER COMPARISON ENGINE ===")
    print(f"MHCLG relationships: {len(relationships):,}")
    print(
        "Authorities with IoD profiles: "
        f"{deprivation['authority_code'].nunique():,}"
    )

    # Prefix deprivation measures so it is always clear that these
    # values describe the neighbour rather than the selected authority.
    neighbour_profiles = deprivation.add_prefix("neighbour_")

    neighbour_profiles = neighbour_profiles.rename(
        columns={
            "neighbour_authority_code": "neighbour_code",
            "neighbour_authority_name": "iod_neighbour_name",
        }
    )

    comparison = relationships.merge(
        neighbour_profiles,
        on="neighbour_code",
        how="left",
        validate="many_to_one",
    )

    comparison["iod_available"] = (
        comparison["neighbour_lsoa_count"].notna()
    )

    comparison["iod_coverage_status"] = comparison[
        "iod_available"
    ].map(
        {
            True: "IoD available",
            False: "IoD unavailable at this geography",
        }
    )

    return comparison


def validate_peer_comparison(
    relationships: pd.DataFrame,
    comparison: pd.DataFrame,
) -> None:
    """Validate the peer-comparison output."""

    print("\n=== PEER COMPARISON VALIDATION ===")

    print(
        f"Input relationships: "
        f"{len(relationships):,}"
    )
    print(
        f"Output relationships: "
        f"{len(comparison):,}"
    )

    if len(relationships) != len(comparison):
        raise ValueError(
            "Relationship count changed during deprivation join."
        )

    expected_neighbours = (
        relationships
        .groupby("local_authority_code")
        .size()
    )

    output_neighbours = (
        comparison
        .groupby("local_authority_code")
        .size()
    )

    if not expected_neighbours.equals(output_neighbours):
        raise ValueError(
            "Neighbour counts changed during deprivation join."
        )

    duplicate_relationships = comparison.duplicated(
        subset=[
            "local_authority_code",
            "neighbour_code",
        ]
    ).sum()

    print(
        "Duplicate authority-neighbour relationships: "
        f"{duplicate_relationships:,}"
    )

    if duplicate_relationships:
        raise ValueError(
            "Duplicate authority-neighbour relationships detected."
        )

    available = int(comparison["iod_available"].sum())
    unavailable = int((~comparison["iod_available"]).sum())

    print(f"Relationships with IoD available: {available:,}")
    print(
        "Relationships with IoD unavailable at this geography: "
        f"{unavailable:,}"
    )

    unavailable_authorities = (
        comparison.loc[
            ~comparison["iod_available"],
            ["neighbour_code", "neighbour_name"],
        ]
        .drop_duplicates()
        .sort_values("neighbour_name")
    )

    print("\n=== NEIGHBOURS WITHOUT DIRECT IOD PROFILE ===")

    if unavailable_authorities.empty:
        print("None")
    else:
        print(
            unavailable_authorities.to_string(
                index=False
            )
        )

    print("\nValidation PASS")


def save_peer_comparison(
    comparison: pd.DataFrame,
) -> Path:
    """Save the Power BI-ready peer-comparison table."""

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    comparison.to_csv(
        OUTPUT_PATH,
        index=False,
    )

    print(f"\nSaved to: {OUTPUT_PATH}")

    return OUTPUT_PATH


def main() -> None:
    """Build, validate and save peer-comparison intelligence."""

    relationships = pd.read_csv(
        RELATIONSHIPS_PATH
    )

    comparison = build_peer_comparison()

    validate_peer_comparison(
        relationships,
        comparison,
    )

    save_peer_comparison(comparison)

    print("\n=== OUTPUT SUMMARY ===")
    print(
        f"Rows: {len(comparison):,}"
    )
    print(
        f"Columns: {len(comparison.columns):,}"
    )
    print(
        "Authorities represented: "
        f"{comparison['local_authority_code'].nunique():,}"
    )


if __name__ == "__main__":
    main()