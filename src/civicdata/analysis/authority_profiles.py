from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[3]

DATA_DIR = (
    PROJECT_ROOT / "data" / "processed"
)


def load_network_strength() -> pd.DataFrame:
    """Load the consolidated network strength dataset."""

    file_path = (
        DATA_DIR
        / "authority_network_strength_2026.csv"
    )

    if not file_path.exists():
        raise FileNotFoundError(
            f"Network strength dataset not found: {file_path}"
        )

    return pd.read_csv(file_path)


def classify_selection_strength(
    score: float,
) -> str:
    """Classify an authority's selection strength."""

    if score >= 0.67:
        return "High"

    if score >= 0.33:
        return "Medium"

    return "Low"


def classify_rank_influence(
    score: float,
) -> str:
    """Classify rank-weighted influence."""

    if score >= 0.67:
        return "High"

    if score >= 0.33:
        return "Medium"

    return "Low"


def classify_reciprocity(
    rate: float,
) -> str:
    """Classify reciprocal network strength."""

    if rate >= 0.67:
        return "High"

    if rate >= 0.33:
        return "Medium"

    return "Low"


def classify_network_position(
    row: pd.Series,
) -> str:
    """
    Classify an authority's overall network position.

    The classification considers selection strength,
    rank influence and reciprocity together.
    """

    selection = row[
        "selection_profile"
    ]

    influence = row[
        "rank_influence_profile"
    ]

    reciprocity = row[
        "reciprocity_profile"
    ]

    if (
        selection == "High"
        and influence == "High"
        and reciprocity == "High"
    ):
        return "Network Core"

    if (
        selection == "High"
        and influence == "High"
        and reciprocity != "High"
    ):
        return "High Influence / Low Reciprocity"

    if (
        reciprocity == "High"
        and selection != "High"
        and influence != "High"
    ):
        return "Mutual Network"

    if (
        selection == "Low"
        and influence == "Low"
        and reciprocity == "Low"
    ):
        return "Peripheral"

    if (
        selection == "High"
        or influence == "High"
    ):
        return "Influential Connector"

    if reciprocity == "High":
        return "Reciprocal Network"

    return "Intermediate Network"


def build_authority_profiles(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """Build analytical profiles for each authority."""

    profiles = df.copy()

    profiles[
        "selection_profile"
    ] = profiles[
        "selection_frequency_score"
    ].apply(
        classify_selection_strength
    )

    profiles[
        "rank_influence_profile"
    ] = profiles[
        "rank_weighted_score_normalised"
    ].apply(
        classify_rank_influence
    )

    profiles[
        "reciprocity_profile"
    ] = profiles[
        "reciprocity_rate"
    ].apply(
        classify_reciprocity
    )

    profiles[
        "network_position"
    ] = profiles.apply(
        classify_network_position,
        axis=1,
    )

    return profiles


def validate_profiles(
    df: pd.DataFrame,
) -> None:
    """Validate the authority profiling output."""

    required_columns = [
        "neighbour_code",
        "neighbour_name",
        "selection_count",
        "rank_weighted_selection_score",
        "reciprocity_rate",
        "network_strength_score",
        "network_strength_rank",
        "selection_profile",
        "rank_influence_profile",
        "reciprocity_profile",
        "network_position",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            "Missing required columns: "
            + ", ".join(missing_columns)
        )

    if df["network_position"].isna().any():
        raise ValueError(
            "Network position contains missing values."
        )

    if df["network_strength_rank"].duplicated().any():
        raise ValueError(
            "Network strength ranks are duplicated."
        )

    valid_positions = {
        "Network Core",
        "High Influence / Low Reciprocity",
        "Mutual Network",
        "Peripheral",
        "Influential Connector",
        "Reciprocal Network",
        "Intermediate Network",
    }

    invalid_positions = set(
        df["network_position"]
    ) - valid_positions

    if invalid_positions:
        raise ValueError(
            "Unexpected network positions: "
            + ", ".join(invalid_positions)
        )


def main() -> None:
    print("CivicData Intelligence")
    print("Authority Network Profiling Engine")
    print("=" * 60)

    network_strength = (
        load_network_strength()
    )

    print(
        f"Authorities analysed: "
        f"{len(network_strength):,}"
    )

    profiles = (
        build_authority_profiles(
            network_strength
        )
    )

    validate_profiles(
        profiles
    )

    # --------------------------------------------------
    # Profile distribution
    # --------------------------------------------------

    print(
        "\nNetwork position distribution:"
    )

    print(
        profiles[
            "network_position"
        ]
        .value_counts()
        .to_string()
    )

    # --------------------------------------------------
    # Top authorities
    # --------------------------------------------------

    print(
        "\nTop 10 authorities by "
        "Network Strength:"
    )

    print(
        profiles[
            [
                "neighbour_code",
                "neighbour_name",
                "network_strength_score",
                "network_strength_rank",
                "selection_profile",
                "rank_influence_profile",
                "reciprocity_profile",
                "network_position",
            ]
        ]
        .head(10)
        .to_string(
            index=False
        )
    )

    # --------------------------------------------------
    # Network Core
    # --------------------------------------------------

    print(
        "\nNetwork Core authorities:"
    )

    network_core = profiles[
        profiles[
            "network_position"
        ] == "Network Core"
    ]

    print(
        network_core[
            [
                "neighbour_code",
                "neighbour_name",
                "network_strength_score",
                "network_strength_rank",
            ]
        ]
        .head(20)
        .to_string(
            index=False
        )
    )

    # --------------------------------------------------
    # High Influence / Low Reciprocity
    # --------------------------------------------------

    print(
        "\nHigh Influence / Low Reciprocity:"
    )

    asymmetric = profiles[
        profiles[
            "network_position"
        ]
        == "High Influence / Low Reciprocity"
    ]

    print(
        asymmetric[
            [
                "neighbour_code",
                "neighbour_name",
                "selection_count",
                "reciprocity_rate",
                "network_strength_score",
            ]
        ]
        .head(20)
        .to_string(
            index=False
        )
    )

    # --------------------------------------------------
    # Save output
    # --------------------------------------------------

    output_file = (
        DATA_DIR
        / "authority_network_profiles_2026.csv"
    )

    profiles.to_csv(
        output_file,
        index=False,
    )

    print(
        "\nProfile dataset written to:"
    )

    print(
        output_file
    )

    print(
        "\nValidation: PASS"
    )


if __name__ == "__main__":
    main()