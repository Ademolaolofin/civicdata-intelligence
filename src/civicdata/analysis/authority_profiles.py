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
        / "network_strength_2026.csv"
    )

    if not file_path.exists():
        raise FileNotFoundError(
            f"Network strength dataset not found: {file_path}"
        )

    return pd.read_csv(file_path)


def classify_selection_strength(
    score: float,
) -> str:
    """Classify an authority's selection frequency strength."""

    if score >= 0.67:
        return "High"

    if score >= 0.33:
        return "Medium"

    return "Low"


def classify_rank_influence(
    score: float,
) -> str:
    """Classify rank-weighted selection influence."""

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
    """
    Build analytical profiles for every authority.

    The profiling layer preserves the complete authority
    population from the network strength dataset.
    """

    profiles = df.copy()

    required_inputs = [
        "neighbour_code",
        "neighbour_name",
        "selection_count",
        "rank_weighted_selection_score",
        "reciprocity_rate",
        "selection_frequency_score",
        "rank_weighted_selection_normalised",
        "network_strength_score",
        "network_strength_rank",
    ]

    missing_inputs = [
        column
        for column in required_inputs
        if column not in profiles.columns
    ]

    if missing_inputs:
        raise ValueError(
            "Network strength dataset is missing required "
            "columns: "
            + ", ".join(missing_inputs)
        )

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
        "rank_weighted_selection_normalised"
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
    """
    Validate the authority profiling output.

    The validation confirms that the complete 317-authority
    population is preserved and that all analytical fields
    are populated and valid.
    """

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

    # --------------------------------------------------
    # Authority population validation
    # --------------------------------------------------

    expected_authority_count = 317

    if len(df) != expected_authority_count:
        raise ValueError(
            "Authority population mismatch: expected "
            f"{expected_authority_count} authorities but "
            f"found {len(df)}."
        )

    if df["neighbour_code"].isna().any():
        raise ValueError(
            "Authority codes contain missing values."
        )

    if df["neighbour_code"].duplicated().any():
        raise ValueError(
            "Authority codes are duplicated."
        )

    if df["neighbour_name"].isna().any():
        raise ValueError(
            "Authority names contain missing values."
        )

    # --------------------------------------------------
    # Analytical score validation
    # --------------------------------------------------

    score_columns = [
        "selection_count",
        "rank_weighted_selection_score",
        "reciprocity_rate",
        "network_strength_score",
    ]

    for column in score_columns:

        if df[column].isna().any():
            raise ValueError(
                f"{column} contains missing values."
            )

        if not pd.api.types.is_numeric_dtype(
            df[column]
        ):
            raise ValueError(
                f"{column} must be numeric."
            )

    # --------------------------------------------------
    # Reciprocity validation
    # --------------------------------------------------

    if (
        df["reciprocity_rate"] < 0
    ).any():

        raise ValueError(
            "Reciprocity rate contains values below 0."
        )

    if (
        df["reciprocity_rate"] > 1
    ).any():

        raise ValueError(
            "Reciprocity rate contains values above 1."
        )

    # --------------------------------------------------
    # Network strength validation
    # --------------------------------------------------

    if (
        df["network_strength_score"] < 0
    ).any():

        raise ValueError(
            "Network strength score contains "
            "values below 0."
        )

    if (
        df["network_strength_score"] > 1
    ).any():

        raise ValueError(
            "Network strength score contains "
            "values above 1."
        )

    # --------------------------------------------------
    # Rank validation
    # --------------------------------------------------

    if (
        df["network_strength_rank"]
        .isna()
        .any()
    ):
        raise ValueError(
            "Network strength rank contains "
            "missing values."
        )

    if not pd.api.types.is_numeric_dtype(
        df["network_strength_rank"]
    ):
        raise ValueError(
            "Network strength rank must be numeric."
        )

    if (
        df["network_strength_rank"] < 1
    ).any():
        raise ValueError(
            "Network strength rank contains "
            "values below 1."
        )

    if (
        df["network_strength_rank"]
        > len(df)
    ).any():
        raise ValueError(
            "Network strength rank exceeds the "
            "authority population."
        )

    # Tied network strength scores may legitimately
    # produce tied ranks. Therefore ranks are not
    # required to be unique.

    # --------------------------------------------------
    # Profile validation
    # --------------------------------------------------

    profile_columns = [
        "selection_profile",
        "rank_influence_profile",
        "reciprocity_profile",
        "network_position",
    ]

    for column in profile_columns:

        if df[column].isna().any():
            raise ValueError(
                f"{column} contains missing values."
            )

    valid_profile_levels = {
        "High",
        "Medium",
        "Low",
    }

    for column in [
        "selection_profile",
        "rank_influence_profile",
        "reciprocity_profile",
    ]:

        invalid_values = (
            set(df[column])
            - valid_profile_levels
        )

        if invalid_values:
            raise ValueError(
                f"Unexpected values in {column}: "
                + ", ".join(
                    map(str, invalid_values)
                )
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

    invalid_positions = (
        set(df["network_position"])
        - valid_positions
    )

    if invalid_positions:
        raise ValueError(
            "Unexpected network positions: "
            + ", ".join(
                map(str, invalid_positions)
            )
        )


def print_network_summary(
    profiles: pd.DataFrame,
) -> None:
    """Print a concise analytical summary."""

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
        .sort_values(
            [
                "network_strength_rank",
                "neighbour_name",
            ]
        )
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

    if network_core.empty:

        print(
            "None"
        )

    else:

        print(
            network_core[
                [
                    "neighbour_code",
                    "neighbour_name",
                    "network_strength_score",
                    "network_strength_rank",
                ]
            ]
            .sort_values(
                "network_strength_rank"
            )
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

    if asymmetric.empty:

        print(
            "None"
        )

    else:

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
            .sort_values(
                "network_strength_score",
                ascending=False,
            )
            .head(20)
            .to_string(
                index=False
            )
        )


def main() -> None:
    print(
        "CivicData Intelligence"
    )

    print(
        "Authority Network Profiling Engine"
    )

    print(
        "=" * 60
    )

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

    print(
        "\nValidation: PASS"
    )

    print_network_summary(
        profiles
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
        f"\nAuthorities profiled: "
        f"{len(profiles):,}"
    )

    print(
        "\nValidation: PASS"
    )


if __name__ == "__main__":
    main()