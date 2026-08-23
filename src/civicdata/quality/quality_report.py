from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[3]
PROCESSED_DATA_DIR = PROJECT_ROOT / "data" / "processed"


EXPECTED_NEIGHBOUR_COUNT = 15


def load_dataset() -> pd.DataFrame:
    """Load the processed Statistical Neighbours dataset."""

    files = list(
        PROCESSED_DATA_DIR.glob(
            "mhclg_statistical_neighbours_2026.csv"
        )
    )

    if not files:
        raise FileNotFoundError(
            "Processed Statistical Neighbours dataset not found."
        )

    return pd.read_csv(files[0])


def check_structure(df: pd.DataFrame) -> dict:
    """Check expected dataset structure."""

    expected_columns = 2 + (EXPECTED_NEIGHBOUR_COUNT * 2)

    return {
        "expected_columns": expected_columns,
        "actual_columns": len(df.columns),
        "passed": len(df.columns) == expected_columns,
    }


def check_missing_values(df: pd.DataFrame) -> dict:
    """Check for missing values."""

    missing = df.isna().sum()

    total_missing = int(missing.sum())

    return {
        "total_missing_values": total_missing,
        "passed": total_missing == 0,
        "columns_with_missing_values": {
            str(column): int(value)
            for column, value in missing.items()
            if value > 0
        },
    }


def check_duplicate_authorities(
    df: pd.DataFrame,
) -> dict:
    """Check for duplicate local authorities."""

    duplicate_codes = int(
        df["local_authority_code"]
        .duplicated()
        .sum()
    )

    return {
        "duplicate_authority_codes": duplicate_codes,
        "passed": duplicate_codes == 0,
    }


def check_self_neighbours(
    df: pd.DataFrame,
) -> dict:
    """Check whether an authority appears as its own neighbour."""

    self_neighbours = 0

    for rank in range(1, EXPECTED_NEIGHBOUR_COUNT + 1):

        neighbour_column = (
            f"Neighbour {rank}: Code"
        )

        if neighbour_column not in df.columns:
            continue

        matches = (
            df["local_authority_code"]
            == df[neighbour_column]
        )

        self_neighbours += int(matches.sum())

    return {
        "self_neighbour_relationships": self_neighbours,
        "passed": self_neighbours == 0,
    }


def calculate_quality_score(
    checks: dict,
) -> float:
    """Calculate an overall quality score."""

    passed = sum(
        1
        for result in checks.values()
        if result["passed"]
    )

    total = len(checks)

    if total == 0:
        return 0.0

    return round(
        (passed / total) * 100,
        2,
    )


def main() -> None:
    print("CivicData Intelligence")
    print("Data Quality Engine")
    print("=" * 60)

    df = load_dataset()

    checks = {
        "structure": check_structure(df),
        "missing_values": check_missing_values(df),
        "duplicate_authorities": check_duplicate_authorities(df),
        "self_neighbours": check_self_neighbours(df),
    }

    for name, result in checks.items():

        status = (
            "PASS"
            if result["passed"]
            else "FAIL"
        )

        print(f"\n[{status}] {name}")

        for key, value in result.items():

            if key != "passed":
                print(f"  {key}: {value}")

    score = calculate_quality_score(checks)

    print("\n" + "=" * 60)
    print(f"Overall Data Quality Score: {score}%")
    print("=" * 60)


if __name__ == "__main__":
    main()