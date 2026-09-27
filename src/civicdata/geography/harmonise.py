from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[3]

IOD_PATH = PROJECT_ROOT / "data" / "raw" / "iod_2025_file_7.csv"

OUTPUT_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "iod_2025_geography_harmonised.csv"
)


# Explicit mappings between geographic code vintages.
#
# The original source code is always retained. These mappings create a
# harmonised code that can be used when linking datasets published using
# different geographic vintages.
AUTHORITY_CODE_MAPPINGS = {
    "E08000016": {
        "harmonised_code": "E08000038",
        "authority_name": "Barnsley",
        "source_geography": "Local Authority District (2024)",
        "target_geography": "MHCLG Statistical Neighbours (2026)",
        "mapping_reason": "Authority code change",
    },
    "E08000019": {
        "harmonised_code": "E08000039",
        "authority_name": "Sheffield",
        "source_geography": "Local Authority District (2024)",
        "target_geography": "MHCLG Statistical Neighbours (2026)",
        "mapping_reason": "Authority code change",
    },
}


def harmonise_authority_codes(df: pd.DataFrame) -> pd.DataFrame:
    """Add harmonised authority identifiers without altering source codes."""

    result = df.copy()

    source_code_column = "Local Authority District code (2024)"
    source_name_column = "Local Authority District name (2024)"

    result["civicdata_authority_code"] = result[source_code_column]
    result["civicdata_authority_name"] = result[source_name_column]

    result["geography_mapping_applied"] = False
    result["geography_mapping_reason"] = "Direct source code"

    for source_code, mapping in AUTHORITY_CODE_MAPPINGS.items():
        mask = result[source_code_column] == source_code

        result.loc[
            mask, "civicdata_authority_code"
        ] = mapping["harmonised_code"]

        result.loc[
            mask, "civicdata_authority_name"
        ] = mapping["authority_name"]

        result.loc[
            mask, "geography_mapping_applied"
        ] = True

        result.loc[
            mask, "geography_mapping_reason"
        ] = mapping["mapping_reason"]

    return result


def validate_harmonisation(
    original: pd.DataFrame,
    harmonised: pd.DataFrame,
) -> None:
    """Validate that geography harmonisation preserves source records."""

    print("\n=== GEOGRAPHY HARMONISATION VALIDATION ===")

    print(f"Input rows: {len(original):,}")
    print(f"Output rows: {len(harmonised):,}")

    if len(original) != len(harmonised):
        raise ValueError(
            "Row count changed during geography harmonisation."
        )

    original_lsoas = original["LSOA code (2021)"].nunique()
    harmonised_lsoas = harmonised["LSOA code (2021)"].nunique()

    print(f"Input unique LSOAs: {original_lsoas:,}")
    print(f"Output unique LSOAs: {harmonised_lsoas:,}")

    if original_lsoas != harmonised_lsoas:
        raise ValueError(
            "LSOA coverage changed during geography harmonisation."
        )

    mapped_rows = harmonised["geography_mapping_applied"].sum()

    mapped_authorities = (
        harmonised.loc[
            harmonised["geography_mapping_applied"],
            [
                "Local Authority District code (2024)",
                "Local Authority District name (2024)",
                "civicdata_authority_code",
                "civicdata_authority_name",
                "geography_mapping_reason",
            ],
        ]
        .drop_duplicates()
        .sort_values("Local Authority District name (2024)")
    )

    print(f"Rows with authority mapping applied: {mapped_rows:,}")

    print("\n=== MAPPED AUTHORITIES ===")

    if mapped_authorities.empty:
        print("None")
    else:
        print(mapped_authorities.to_string(index=False))

    print("\n=== HARMONISED AUTHORITY COVERAGE ===")

    print(
        "Original authority codes: "
        f"{original['Local Authority District code (2024)'].nunique():,}"
    )

    print(
        "Harmonised authority codes: "
        f"{harmonised['civicdata_authority_code'].nunique():,}"
    )

    print("\nValidation PASS")


def build_harmonised_geography() -> Path:
    """Create the CivicData geography-harmonised IoD dataset."""

    iod = pd.read_csv(IOD_PATH)

    harmonised = harmonise_authority_codes(iod)

    validate_harmonisation(iod, harmonised)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    harmonised.to_csv(
        OUTPUT_PATH,
        index=False,
    )

    print(f"\nSaved to: {OUTPUT_PATH}")

    return OUTPUT_PATH


if __name__ == "__main__":
    build_harmonised_geography()