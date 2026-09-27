from pathlib import Path

import requests


PROJECT_ROOT = Path(__file__).resolve().parents[3]

RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"

IOD_2025_URL = (
    "https://assets.publishing.service.gov.uk/"
    "media/691ded56d140bbbaa59a2a7d/"
    "File_7_IoD2025_All_Ranks_Scores_Deciles_Population_Denominators.csv"
)


IOD_2025_FILENAME = "iod_2025_file_7.csv"


def download_iod_2025() -> Path:
    """Download the English Indices of Deprivation 2025 File 7 dataset."""

    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)

    output_path = RAW_DATA_DIR / IOD_2025_FILENAME

    print("Downloading English Indices of Deprivation 2025...")
    print(f"Source: {IOD_2025_URL}")

    response = requests.get(IOD_2025_URL, timeout=120)
    response.raise_for_status()

    output_path.write_bytes(response.content)

    print(f"Saved to: {output_path}")
    print(f"Downloaded size: {output_path.stat().st_size:,} bytes")

    return output_path


if __name__ == "__main__":
    download_iod_2025()