from pathlib import Path

import pandas as pd


# ============================================================
# Project configuration
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[3]

DATA_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
)


# ============================================================
# Data loading
# ============================================================

def load_relationships() -> pd.DataFrame:
    """Load the long-format neighbour relationship dataset."""

    file_path = (
        DATA_DIR
        / "mhclg_neighbour_relationships_2026.csv"
    )

    if not file_path.exists():
        raise FileNotFoundError(
            f"Relationship dataset not found: {file_path}"
        )

    df = pd.read_csv(file_path)

    required_columns = {
        "local_authority_code",
        "local_authority_name",
        "neighbour_code",
        "neighbour_name",
        "rank",
    }

    missing_columns = (
        required_columns
        - set(df.columns)
    )

    if missing_columns:
        raise ValueError(
            "Relationship dataset is missing "
            f"required columns: {sorted(missing_columns)}"
        )

    return df


# ============================================================
# Authority population
# ============================================================

def build_authority_population(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Build the complete authority population represented
    in the relationship network.

    Authorities are collected from both the local-authority
    and neighbour sides of the relationship dataset.
    """

    local_authorities = (
        df[
            [
                "local_authority_code",
                "local_authority_name",
            ]
        ]
        .rename(
            columns={
                "local_authority_code":
                    "authority_code",
                "local_authority_name":
                    "authority_name",
            }
        )
    )

    neighbour_authorities = (
        df[
            [
                "neighbour_code",
                "neighbour_name",
            ]
        ]
        .rename(
            columns={
                "neighbour_code":
                    "authority_code",
                "neighbour_name":
                    "authority_name",
            }
        )
    )

    authorities = (
        pd.concat(
            [
                local_authorities,
                neighbour_authorities,
            ],
            ignore_index=True,
        )
        .drop_duplicates(
            subset=["authority_code"]
        )
        .sort_values(
            "authority_code"
        )
        .reset_index(drop=True)
    )

    return authorities


# ============================================================
# Metric 1: Neighbour frequency
# ============================================================

def calculate_neighbour_frequency(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Calculate how often each authority is selected
    as a statistical neighbour.

    Authorities with zero inbound selections are retained.
    """

    authorities = (
        build_authority_population(df)
        .rename(
            columns={
                "authority_code":
                    "neighbour_code",
                "authority_name":
                    "neighbour_name",
            }
        )
    )

    frequency = (
        df.groupby(
            [
                "neighbour_code",
                "neighbour_name",
            ]
        )
        .size()
        .reset_index(
            name="selection_count"
        )
    )

    frequency = authorities.merge(
        frequency,
        on=[
            "neighbour_code",
            "neighbour_name",
        ],
        how="left",
    )

    frequency["selection_count"] = (
        frequency["selection_count"]
        .fillna(0)
        .astype(int)
    )

    return (
        frequency
        .sort_values(
            [
                "selection_count",
                "neighbour_name",
            ],
            ascending=[
                False,
                True,
            ],
        )
        .reset_index(drop=True)
    )


# ============================================================
# Metric 2: Rank-weighted selection
# ============================================================

def calculate_rank_weight(
    rank: int,
) -> float:
    """
    Calculate the rank weight.

    Rank 1 receives the greatest weight.
    """

    return 1 / rank


def calculate_rank_weighted_selection_score(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Calculate the rank-weighted selection score.

    Each inbound neighbour selection contributes:

        1 / rank

    Therefore, selections at rank 1 contribute more than
    selections at lower ranks.
    """

    authorities = (
        build_authority_population(df)
        .rename(
            columns={
                "authority_code":
                    "neighbour_code",
                "authority_name":
                    "neighbour_name",
            }
        )
    )

    working = df.copy()

    working["rank_weight"] = (
        working["rank"]
        .apply(calculate_rank_weight)
    )

    weighted = (
        working.groupby(
            [
                "neighbour_code",
                "neighbour_name",
            ]
        )["rank_weight"]
        .sum()
        .reset_index(
            name="rank_weighted_selection_score"
        )
    )

    result = authorities.merge(
        weighted,
        on=[
            "neighbour_code",
            "neighbour_name",
        ],
        how="left",
    )

    result[
        "rank_weighted_selection_score"
    ] = (
        result[
            "rank_weighted_selection_score"
        ]
        .fillna(0.0)
    )

    return (
        result
        .sort_values(
            "rank_weighted_selection_score",
            ascending=False,
        )
        .reset_index(drop=True)
    )


# ============================================================
# Metric 3: Reciprocity
# ============================================================

def calculate_reciprocity(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Calculate reciprocal neighbour relationships.

    A relationship is reciprocal when:

        Authority A -> Authority B

    and:

        Authority B -> Authority A

    Reciprocity rate is:

        reciprocal neighbours / total neighbours
    """

    authorities = build_authority_population(df)

    relationships = set(
        zip(
            df["local_authority_code"],
            df["neighbour_code"],
        )
    )

    results = []

    for _, authority in authorities.iterrows():

        authority_code = (
            authority["authority_code"]
        )

        authority_name = (
            authority["authority_name"]
        )

        authority_group = df[
            df["local_authority_code"]
            == authority_code
        ]

        total_neighbours = (
            len(authority_group)
        )

        reciprocal_count = 0

        for neighbour_code in (
            authority_group[
                "neighbour_code"
            ]
        ):

            if (
                neighbour_code,
                authority_code,
            ) in relationships:

                reciprocal_count += 1

        reciprocity_rate = (
            reciprocal_count
            / total_neighbours
            if total_neighbours > 0
            else 0.0
        )

        results.append(
            {
                "local_authority_code":
                    authority_code,

                "local_authority_name":
                    authority_name,

                "neighbour_count":
                    total_neighbours,

                "reciprocal_neighbour_count":
                    reciprocal_count,

                "reciprocity_rate":
                    reciprocity_rate,
            }
        )

    return (
        pd.DataFrame(results)
        .sort_values(
            "reciprocity_rate",
            ascending=False,
        )
        .reset_index(drop=True)
    )


# ============================================================
# Normalisation
# ============================================================

def min_max_normalise(
    series: pd.Series,
) -> pd.Series:
    """
    Normalise a numeric series to a 0 to 1 scale.

    Constant series receive 1.0.
    """

    minimum = series.min()
    maximum = series.max()

    if maximum == minimum:
        return pd.Series(
            1.0,
            index=series.index,
        )

    return (
        (series - minimum)
        / (maximum - minimum)
    )


# ============================================================
# Metric 4: Network Strength Score
# ============================================================

def build_network_strength_score(
    frequency: pd.DataFrame,
    rank_weighted_selection: pd.DataFrame,
    reciprocity: pd.DataFrame,
) -> pd.DataFrame:
    """
    Build the consolidated Network Strength Score.

    Components:

    1. Selection frequency
    2. Rank-weighted selection score
    3. Reciprocity rate

    All three components are normalised to 0 to 1 and
    equally weighted.
    """

    network = frequency.merge(
        rank_weighted_selection[
            [
                "neighbour_code",
                "neighbour_name",
                "rank_weighted_selection_score",
            ]
        ],
        on=[
            "neighbour_code",
            "neighbour_name",
        ],
        how="left",
    )

    reciprocity_for_merge = (
        reciprocity[
            [
                "local_authority_code",
                "local_authority_name",
                "neighbour_count",
                "reciprocal_neighbour_count",
                "reciprocity_rate",
            ]
        ]
        .rename(
            columns={
                "local_authority_code":
                    "neighbour_code",
                "local_authority_name":
                    "neighbour_name",
            }
        )
    )

    network = network.merge(
        reciprocity_for_merge,
        on=[
            "neighbour_code",
            "neighbour_name",
        ],
        how="left",
    )

    # Defensive handling of missing analytical values.
    network[
        "selection_count"
    ] = (
        network["selection_count"]
        .fillna(0)
    )

    network[
        "rank_weighted_selection_score"
    ] = (
        network[
            "rank_weighted_selection_score"
        ]
        .fillna(0.0)
    )

    network[
        "reciprocity_rate"
    ] = (
        network[
            "reciprocity_rate"
        ]
        .fillna(0.0)
    )

    # Normalised components.
    network[
        "selection_frequency_score"
    ] = min_max_normalise(
        network["selection_count"]
    )

    network[
        "rank_weighted_selection_normalised"
    ] = min_max_normalise(
        network[
            "rank_weighted_selection_score"
        ]
    )

    network[
        "reciprocity_normalised"
    ] = min_max_normalise(
        network["reciprocity_rate"]
    )

    # Equal weighting.
    network[
        "network_strength_score"
    ] = (
        network[
            "selection_frequency_score"
        ]
        + network[
            "rank_weighted_selection_normalised"
        ]
        + network[
            "reciprocity_normalised"
        ]
    ) / 3

    network = network.sort_values(
        "network_strength_score",
        ascending=False,
    ).reset_index(drop=True)

    network[
        "network_strength_rank"
    ] = (
        network[
            "network_strength_score"
        ]
        .rank(
            method="min",
            ascending=False,
        )
        .astype(int)
    )

    return network


# ============================================================
# Validation
# ============================================================

def validate_network_strength(
    network: pd.DataFrame,
) -> None:
    """Validate the consolidated network strength dataset."""

    required_columns = {
        "neighbour_code",
        "neighbour_name",
        "selection_count",
        "rank_weighted_selection_score",
        "reciprocity_rate",
        "network_strength_score",
        "network_strength_rank",
    }

    missing_columns = (
        required_columns
        - set(network.columns)
    )

    assert not missing_columns, (
        "Network strength dataset is missing "
        f"columns: {sorted(missing_columns)}"
    )

    score = (
        network["network_strength_score"]
    )

    assert not score.isna().any(), (
        "Network strength score contains "
        "missing values."
    )

    assert (
        score.between(0, 1).all()
    ), (
        "Network strength scores must be "
        "between 0 and 1."
    )

    assert (
        network[
            "selection_count"
        ].isna().sum()
        == 0
    )

    assert (
        network[
            "rank_weighted_selection_score"
        ].isna().sum()
        == 0
    )

    assert (
        network[
            "reciprocity_rate"
        ].isna().sum()
        == 0
    )

    assert (
        network[
            "neighbour_code"
        ].duplicated().sum()
        == 0
    )


# ============================================================
# Main analytical pipeline
# ============================================================

def main() -> None:

    print("CivicData Intelligence")
    print("Network Metrics Engine")
    print("=" * 60)

    df = load_relationships()

    print(
        f"Relationships analysed: "
        f"{len(df):,}"
    )

    authorities = (
        build_authority_population(df)
    )

    print(
        f"Authorities represented: "
        f"{len(authorities):,}"
    )

    # --------------------------------------------------------
    # Metric 1: Neighbour frequency
    # --------------------------------------------------------

    frequency = (
        calculate_neighbour_frequency(df)
    )

    print(
        "\nTop 10 authorities by neighbour frequency:"
    )

    print(
        frequency.head(10)
        .to_string(index=False)
    )

    # --------------------------------------------------------
    # Metric 2: Rank-weighted selection
    # --------------------------------------------------------

    rank_weighted_selection = (
        calculate_rank_weighted_selection_score(
            df
        )
    )

    print(
        "\nTop 10 authorities by rank-weighted "
        "selection score:"
    )

    print(
        rank_weighted_selection.head(10)
        .to_string(index=False)
    )

    # --------------------------------------------------------
    # Metric 3: Reciprocity
    # --------------------------------------------------------

    reciprocity = (
        calculate_reciprocity(df)
    )

    print(
        "\nTop 10 authorities by reciprocity:"
    )

    print(
        reciprocity.head(10)
        .to_string(index=False)
    )

    # --------------------------------------------------------
    # Reciprocity distribution
    # --------------------------------------------------------

    print(
        "\nReciprocity distribution:"
    )

    print(
        reciprocity[
            "reciprocity_rate"
        ].describe()
    )

    # --------------------------------------------------------
    # Metric 4: Network Strength
    # --------------------------------------------------------

    network_strength = (
        build_network_strength_score(
            frequency,
            rank_weighted_selection,
            reciprocity,
        )
    )

    validate_network_strength(
        network_strength
    )

    print(
        "\nNetwork Strength validation: PASS"
    )

    print(
        "\nTop 10 authorities by Network "
        "Strength Score:"
    )

    print(
        network_strength[
            [
                "neighbour_code",
                "neighbour_name",
                "selection_count",
                "rank_weighted_selection_score",
                "reciprocity_rate",
                "network_strength_score",
                "network_strength_rank",
            ]
        ]
        .head(10)
        .to_string(index=False)
    )

    # --------------------------------------------------------
    # Save analytical outputs
    # --------------------------------------------------------

    frequency.to_csv(
        DATA_DIR
        / "neighbour_frequency_2026.csv",
        index=False,
    )

    rank_weighted_selection.to_csv(
        DATA_DIR
        / "neighbour_rank_weighted_selection_2026.csv",
        index=False,
    )

    reciprocity.to_csv(
        DATA_DIR
        / "neighbour_reciprocity_2026.csv",
        index=False,
    )

    network_strength.to_csv(
        DATA_DIR
        / "network_strength_2026.csv",
        index=False,
    )

    print(
        "\nAnalytical outputs written:"
    )

    print(
        "  - neighbour_frequency_2026.csv"
    )

    print(
        "  - neighbour_rank_weighted_selection_2026.csv"
    )

    print(
        "  - neighbour_reciprocity_2026.csv"
    )

    print(
        "  - network_strength_2026.csv"
    )


if __name__ == "__main__":
    main()