from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[3]

PROCESSED_DATA_DIR = (
    PROJECT_ROOT / "data" / "processed"
)

OUTPUT_DIR = (
    PROJECT_ROOT / "data" / "processed"
)


def load_neighbour_data() -> pd.DataFrame:
    """Load the processed MHCLG neighbour dataset."""

    file_path = (
        PROCESSED_DATA_DIR
        / "mhclg_statistical_neighbours_2026.csv"
    )

    if not file_path.exists():
        raise FileNotFoundError(
            f"Dataset not found: {file_path}"
        )

    return pd.read_csv(file_path)


def build_relationship_table(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """Convert the wide neighbour table into long format."""

    relationships = []

    for _, row in df.iterrows():

        authority_code = row[
            "local_authority_code"
        ]

        authority_name = row[
            "local_authority_name"
        ]

        for rank in range(1, 16):

            neighbour_code_column = (
                f"Neighbour {rank}: Code"
            )

            neighbour_name_column = (
                f"Neighbour {rank}: Name"
            )

            neighbour_code = row[
                neighbour_code_column
            ]

            neighbour_name = row[
                neighbour_name_column
            ]

            relationships.append(
                {
                    "local_authority_code":
                        authority_code,

                    "local_authority_name":
                        authority_name,

                    "neighbour_code":
                        neighbour_code,

                    "neighbour_name":
                        neighbour_name,

                    "rank":
                        rank,
                }
            )

    return pd.DataFrame(relationships)


def main() -> None:
    print("CivicData Intelligence")
    print("Relationship Engine")
    print("=" * 60)

    df = load_neighbour_data()

    print(
        f"Input authorities: {len(df):,}"
    )

    relationships = build_relationship_table(df)

    print(
        f"Relationships created: "
        f"{len(relationships):,}"
    )

    output_path = (
        OUTPUT_DIR
        / "mhclg_neighbour_relationships_2026.csv"
    )

    relationships.to_csv(
        output_path,
        index=False,
    )

    print("\nOutput:")
    print(output_path)

    print("\nFirst 10 relationships:")
    print(
        relationships.head(10).to_string(
            index=False
        )
    )


if __name__ == "__main__":
    main()