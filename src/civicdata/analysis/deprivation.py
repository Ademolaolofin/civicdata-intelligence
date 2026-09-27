from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[3]

INPUT_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "iod_2025_geography_harmonised.csv"
)

OUTPUT_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "authority_deprivation_profile_2025.csv"
)


AUTHORITY_CODE = "civicdata_authority_code"
AUTHORITY_NAME = "civicdata_authority_name"

LSOA_CODE = "LSOA code (2021)"

IMD_SCORE = "Index of Multiple Deprivation (IMD) Score"

IMD_DECILE = (
    "Index of Multiple Deprivation (IMD) Decile "
    "(where 1 is most deprived 10% of LSOAs)"
)

TOTAL_POPULATION = "Total population: mid 2022"


DOMAIN_DECILES = {
    "income": "Income Decile (where 1 is most deprived 10% of LSOAs)",
    "employment": (
        "Employment Decile "
        "(where 1 is most deprived 10% of LSOAs)"
    ),
    "education": (
        "Education, Skills and Training Decile "
        "(where 1 is most deprived 10% of LSOAs)"
    ),
    "health": (
        "Health Deprivation and Disability Decile "
        "(where 1 is most deprived 10% of LSOAs)"
    ),
    "crime": "Crime Decile (where 1 is most deprived 10% of LSOAs)",
    "housing_services": (
        "Barriers to Housing and Services Decile "
        "(where 1 is most deprived 10% of LSOAs)"
    ),
    "living_environment": (
        "Living Environment Decile "
        "(where 1 is most deprived 10% of LSOAs)"
    ),
}


def percentage(part: int, whole: int) -> float:
    """Return percentage to two decimal places."""

    if whole == 0:
        return 0.0

    return round((part / whole) * 100, 2)


def build_authority_profile(
    authority_data: pd.DataFrame,
) -> dict:
    """Build deprivation measures for one local authority."""

    authority_code = authority_data[AUTHORITY_CODE].iloc[0]
    authority_name = authority_data[AUTHORITY_NAME].iloc[0]

    lsoa_count = len(authority_data)

    most_deprived_10 = int(
        (authority_data[IMD_DECILE] == 1).sum()
    )

    most_deprived_20 = int(
        (authority_data[IMD_DECILE] <= 2).sum()
    )

    most_deprived_30 = int(
        (authority_data[IMD_DECILE] <= 3).sum()
    )

    least_deprived_10 = int(
        (authority_data[IMD_DECILE] == 10).sum()
    )

    profile = {
        "authority_code": authority_code,
        "authority_name": authority_name,
        "lsoa_count": lsoa_count,
        "population_mid_2022": int(
            authority_data[TOTAL_POPULATION].sum()
        ),
        "median_imd_score": round(
            authority_data[IMD_SCORE].median(),
            3,
        ),
        "lsoas_most_deprived_10pct": most_deprived_10,
        "pct_lsoas_most_deprived_10pct": percentage(
            most_deprived_10,
            lsoa_count,
        ),
        "lsoas_most_deprived_20pct": most_deprived_20,
        "pct_lsoas_most_deprived_20pct": percentage(
            most_deprived_20,
            lsoa_count,
        ),
        "lsoas_most_deprived_30pct": most_deprived_30,
        "pct_lsoas_most_deprived_30pct": percentage(
            most_deprived_30,
            lsoa_count,
        ),
        "lsoas_least_deprived_10pct": least_deprived_10,
        "pct_lsoas_least_deprived_10pct": percentage(
            least_deprived_10,
            lsoa_count,
        ),
    }

    for domain_name, decile_column in DOMAIN_DECILES.items():
        domain_most_deprived_10 = int(
            (authority_data[decile_column] == 1).sum()
        )

        domain_most_deprived_20 = int(
            (authority_data[decile_column] <= 2).sum()
        )

        profile[
            f"pct_{domain_name}_lsoas_most_deprived_10pct"
        ] = percentage(
            domain_most_deprived_10,
            lsoa_count,
        )

        profile[
            f"pct_{domain_name}_lsoas_most_deprived_20pct"
        ] = percentage(
            domain_most_deprived_20,
            lsoa_count,
        )

    return profile


def build_deprivation_profiles() -> pd.DataFrame:
    """Build authority-level deprivation profiles."""

    iod = pd.read_csv(INPUT_PATH)

    print("\n=== CIVICDATA DEPRIVATION INTELLIGENCE ===")
    print(f"Input LSOAs: {len(iod):,}")
    print(
        f"Input authorities: "
        f"{iod[AUTHORITY_CODE].nunique():,}"
    )

    profiles = []

    for _, authority_data in iod.groupby(
        AUTHORITY_CODE,
        sort=True,
    ):
        profiles.append(
            build_authority_profile(authority_data)
        )

    result = pd.DataFrame(profiles)

    result = result.sort_values(
        "authority_name"
    ).reset_index(drop=True)

    return result


def validate_profiles(
    source: pd.DataFrame,
    profiles: pd.DataFrame,
) -> None:
    """Validate authority deprivation outputs."""

    expected_authorities = source[AUTHORITY_CODE].nunique()

    print("\n=== DEPRIVATION PROFILE VALIDATION ===")
    print(f"Expected authorities: {expected_authorities:,}")
    print(f"Profile authorities: {len(profiles):,}")

    if len(profiles) != expected_authorities:
        raise ValueError(
            "Authority profile count does not match source coverage."
        )

    if profiles["authority_code"].duplicated().any():
        raise ValueError(
            "Duplicate authority codes found in deprivation profiles."
        )

    percentage_columns = [
        column
        for column in profiles.columns
        if column.startswith("pct_")
    ]

    for column in percentage_columns:
        invalid = ~profiles[column].between(0, 100)

        if invalid.any():
            raise ValueError(
                f"Invalid percentage values detected in {column}."
            )

    source_population = int(source[TOTAL_POPULATION].sum())
    profile_population = int(
        profiles["population_mid_2022"].sum()
    )

    print(
        f"Source population total: "
        f"{source_population:,}"
    )
    print(
        f"Profile population total: "
        f"{profile_population:,}"
    )

    if source_population != profile_population:
        raise ValueError(
            "Population totals changed during aggregation."
        )

    print("Validation PASS")


def save_profiles(
    profiles: pd.DataFrame,
) -> Path:
    """Save authority deprivation profiles."""

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    profiles.to_csv(
        OUTPUT_PATH,
        index=False,
    )

    print(f"\nSaved to: {OUTPUT_PATH}")

    return OUTPUT_PATH


def main() -> None:
    """Build, validate and save deprivation intelligence."""

    source = pd.read_csv(INPUT_PATH)

    profiles = build_deprivation_profiles()

    validate_profiles(
        source,
        profiles,
    )

    save_profiles(profiles)

    print("\n=== OUTPUT SUMMARY ===")
    print(f"Authorities: {len(profiles):,}")
    print(f"Measures: {len(profiles.columns):,}")

    print(
        "\nAuthorities with highest shares of LSOAs "
        "in the nationally most deprived 10%:"
    )

    preview = profiles[
        [
            "authority_name",
            "lsoa_count",
            "pct_lsoas_most_deprived_10pct",
        ]
    ].sort_values(
        "pct_lsoas_most_deprived_10pct",
        ascending=False,
    ).head(10)

    print(preview.to_string(index=False))


if __name__ == "__main__":
    main()