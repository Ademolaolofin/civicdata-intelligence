from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[3]

INPUT_PATH = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "iod_2025_file_10_lad_summaries.xlsx"
)

OUTPUT_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "iod_2025_lad_official_summaries.csv"
)


SHEET_PREFIXES = {
    "IMD": "imd",
    "Income": "income",
    "Employment": "employment",
    "Education": "education",
    "Health": "health",
    "Crime": "crime",
    "Barriers": "barriers",
    "Living": "living_environment",
    "IDACI": "idaci",
    "IDAOPI": "idaopi",
}


# These mappings align the IoD 2024 LAD codes with the authority
# codes used in the 2026 MHCLG Statistical Neighbours dataset.
AUTHORITY_CODE_MAPPING = {
    "E08000016": "E08000038",  # Barnsley
    "E08000019": "E08000039",  # Sheffield
}


def clean_column_name(column: str) -> str:
    """Convert source column names to stable snake_case names."""

    column = str(column).strip().lower()

    replacements = {
        "%": "pct",
        "-": " ",
        ",": "",
        "(": "",
        ")": "",
        "/": "_",
    }

    for old, new in replacements.items():
        column = column.replace(old, new)

    column = "_".join(column.split())

    return column


def load_sheet(
    sheet_name: str,
    prefix: str,
) -> pd.DataFrame:
    """Load and standardise one File 10 analytical sheet."""

    df = pd.read_excel(
        INPUT_PATH,
        sheet_name=sheet_name,
    )

    code_column = "Local Authority District code (2024)"
    name_column = "Local Authority District name (2024)"

    if code_column not in df.columns:
        raise ValueError(
            f"{sheet_name}: authority code column not found."
        )

    if name_column not in df.columns:
        raise ValueError(
            f"{sheet_name}: authority name column not found."
        )

    df = df.rename(
        columns={
            code_column: "source_authority_code",
            name_column: "source_authority_name",
        }
    )

    measure_columns = [
        column
        for column in df.columns
        if column
        not in {
            "source_authority_code",
            "source_authority_name",
        }
    ]

    rename_map = {}

    for column in measure_columns:
        clean_name = clean_column_name(column)

        # Remove repeated source labels from the start so that
        # the sheet prefix provides a consistent namespace.
        source_prefixes = [
            "imd_",
            "imd25_",
            "income_",
            "employment_",
            "education_skills_and_training_",
            "health_deprivation_and_disability_",
            "crime_",
            "barriers_to_housing_and_services_",
            "living_environment_",
            "idaci_",
            "idaopi_",
        ]

        for source_prefix in source_prefixes:
            if clean_name.startswith(source_prefix):
                clean_name = clean_name[len(source_prefix):]
                break

        rename_map[column] = f"{prefix}_{clean_name}"

    df = df.rename(columns=rename_map)

    df["authority_code"] = df[
        "source_authority_code"
    ].replace(AUTHORITY_CODE_MAPPING)

    df["authority_name"] = df["source_authority_name"]

    return df


def build_official_lad_summary() -> pd.DataFrame:
    """Combine all official File 10 LAD summary sheets."""

    print("\n=== IOD 2025 OFFICIAL LAD SUMMARY INGESTION ===")
    print(f"Source: {INPUT_PATH}")

    combined = None

    for sheet_name, prefix in SHEET_PREFIXES.items():
        sheet = load_sheet(
            sheet_name,
            prefix,
        )

        print(
            f"{sheet_name}: "
            f"{len(sheet):,} authorities, "
            f"{len(sheet.columns):,} columns"
        )

        measure_columns = [
            column
            for column in sheet.columns
            if column
            not in {
                "source_authority_code",
                "source_authority_name",
                "authority_code",
                "authority_name",
            }
        ]

        if combined is None:
            combined = sheet[
                [
                    "source_authority_code",
                    "source_authority_name",
                    "authority_code",
                    "authority_name",
                ]
                + measure_columns
            ].copy()

        else:
            combined = combined.merge(
                sheet[
                    ["authority_code"]
                    + measure_columns
                ],
                on="authority_code",
                how="outer",
                validate="one_to_one",
            )

    return combined.sort_values(
        "authority_name"
    ).reset_index(drop=True)


def validate_summary(df: pd.DataFrame) -> None:
    """Validate the combined official LAD summary table."""

    print("\n=== OFFICIAL LAD SUMMARY VALIDATION ===")

    print(f"Authorities: {len(df):,}")
    print(f"Columns: {len(df.columns):,}")

    duplicate_codes = int(
        df["authority_code"].duplicated().sum()
    )

    missing_codes = int(
        df["authority_code"].isna().sum()
    )

    missing_names = int(
        df["authority_name"].isna().sum()
    )

    print(
        f"Duplicate authority codes: "
        f"{duplicate_codes:,}"
    )
    print(
        f"Missing authority codes: "
        f"{missing_codes:,}"
    )
    print(
        f"Missing authority names: "
        f"{missing_names:,}"
    )

    if len(df) != 296:
        raise ValueError(
            "Expected 296 lower-tier authorities "
            f"but found {len(df)}."
        )

    if duplicate_codes:
        raise ValueError(
            "Duplicate authority codes detected."
        )

    if missing_codes:
        raise ValueError(
            "Missing authority codes detected."
        )

    if missing_names:
        raise ValueError(
            "Missing authority names detected."
        )

    expected_mapped_codes = {
        "E08000038",
        "E08000039",
    }

    actual_codes = set(df["authority_code"])

    missing_mapped_codes = (
        expected_mapped_codes - actual_codes
    )

    if missing_mapped_codes:
        raise ValueError(
            "Expected harmonised authority codes "
            f"not found: {missing_mapped_codes}"
        )

    print("Validation PASS")


def save_summary(df: pd.DataFrame) -> Path:
    """Save the clean authority-level IoD summary."""

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    df.to_csv(
        OUTPUT_PATH,
        index=False,
    )

    print(f"\nSaved to: {OUTPUT_PATH}")

    return OUTPUT_PATH


def show_example(df: pd.DataFrame) -> None:
    """Show a small validation example."""

    columns = [
        "authority_name",
        "imd_average_score",
        "imd_rankof_average_score",
        "imd_proportion_of_lsoas_in_most_deprived_10pct_nationally",
        "income_proportion_of_lsoas_in_most_deprived_10pct_nationally",
        "employment_proportion_of_lsoas_in_most_deprived_10pct_nationally",
        "education_proportion_of_lsoas_in_most_deprived_10pct_nationally",
        "health_proportion_of_lsoas_in_most_deprived_10pct_nationally",
        "crime_proportion_of_lsoas_in_most_deprived_10pct_nationally",
    ]

    available_columns = [
        column
        for column in columns
        if column in df.columns
    ]

    example = df[
        df["authority_name"].isin(
            [
                "Burnley",
                "Middlesbrough",
                "Birmingham",
            ]
        )
    ][available_columns]

    print("\n=== EXAMPLE OFFICIAL MEASURES ===")
    print(example.to_string(index=False))


def main() -> None:
    """Build and validate the official File 10 dataset."""

    summary = build_official_lad_summary()

    validate_summary(summary)

    save_summary(summary)

    show_example(summary)

    print("\n=== OUTPUT SUMMARY ===")
    print(f"Authorities: {len(summary):,}")
    print(f"Measures/columns: {len(summary.columns):,}")


if __name__ == "__main__":
    main()