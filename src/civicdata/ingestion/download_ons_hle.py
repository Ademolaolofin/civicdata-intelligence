from pathlib import Path

import pandas as pd
import requests


PROJECT_ROOT = Path(__file__).resolve().parents[3]

RAW_DIR = PROJECT_ROOT / "data" / "raw"

OUTPUT_PATH = (
    RAW_DIR / "ons_healthy_life_expectancy_2022_2024.xlsx"
)

SOURCE_URL = (
    "https://www.ons.gov.uk/file?uri="
    "%2Fpeoplepopulationandcommunity%2Fhealthandsocialcare"
    "%2Fhealthandlifeexpectancies%2Fdatasets"
    "%2Fhealthstatelifeexpectancyallagesuk%2Fcurrent"
    "%2Fhealthylifeexpectancyuk.xlsx"
)

EXPECTED_CONTENT_TYPE = (
    "application/vnd.openxmlformats-officedocument."
    "spreadsheetml.sheet"
)


def download_workbook():
    print("Downloading official ONS Healthy Life Expectancy workbook...")

    response = requests.get(
        SOURCE_URL,
        timeout=180,
    )

    response.raise_for_status()

    content_type = response.headers.get(
        "content-type",
        "",
    )

    print(f"HTTP status  : {response.status_code}")
    print(f"Content type : {content_type}")
    print(f"Bytes        : {len(response.content):,}")

    if (
        EXPECTED_CONTENT_TYPE not in content_type
        and "spreadsheet" not in content_type.lower()
    ):
        raise ValueError(
            "ONS download did not return an Excel workbook. "
            f"Content-Type: {content_type}"
        )

    if len(response.content) < 100_000:
        raise ValueError(
            "Downloaded workbook is unexpectedly small."
        )

    RAW_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    OUTPUT_PATH.write_bytes(
        response.content
    )

    print(f"Saved        : {OUTPUT_PATH}")


def inspect_workbook():
    print()
    print("Inspecting workbook...")
    print("=" * 75)

    workbook = pd.ExcelFile(
        OUTPUT_PATH,
        engine="openpyxl",
    )

    print(f"Sheet count: {len(workbook.sheet_names)}")

    print()
    print("SHEETS")
    print("=" * 75)

    for number, sheet_name in enumerate(
        workbook.sheet_names,
        start=1,
    ):
        print(f"{number:>2}. {sheet_name}")

    print()
    print("SHEET PREVIEWS")
    print("=" * 75)

    for sheet_name in workbook.sheet_names:
        print()
        print("-" * 75)
        print(f"SHEET: {sheet_name}")

        try:
            preview = pd.read_excel(
                OUTPUT_PATH,
                sheet_name=sheet_name,
                header=None,
                nrows=15,
                engine="openpyxl",
            )

            print(
                f"Preview shape: "
                f"{preview.shape[0]} rows x "
                f"{preview.shape[1]} columns"
            )

            preview = preview.dropna(
                axis=1,
                how="all",
            )

            print(
                preview.to_string(
                    index=True,
                    header=False,
                )
            )

        except Exception as exc:
            print(
                f"Could not preview sheet: "
                f"{type(exc).__name__}: {exc}"
            )

    print()
    print("Inspection complete.")


def main():
    print("CivicData ONS Healthy Life Expectancy discovery")
    print("=" * 75)

    download_workbook()
    inspect_workbook()


if __name__ == "__main__":
    main()
