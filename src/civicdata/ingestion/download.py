from pathlib import Path
from datetime import datetime, timezone
import json

import requests


PROJECT_ROOT = Path(__file__).resolve().parents[3]
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"
SOURCES_FILE = PROJECT_ROOT / "data" / "sources.json"


def download_file(
    url: str,
    filename: str,
    publisher: str,
    dataset: str,
) -> Path:
    """Download a public dataset and record its provenance."""

    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)

    destination = RAW_DATA_DIR / filename

    response = requests.get(url, timeout=60)
    response.raise_for_status()

    destination.write_bytes(response.content)

    record_source(
        url=url,
        filename=filename,
        publisher=publisher,
        dataset=dataset,
    )

    print(f"Downloaded: {destination}")

    return destination


def record_source(
    url: str,
    filename: str,
    publisher: str,
    dataset: str,
) -> None:
    """Record dataset provenance in sources.json."""

    if SOURCES_FILE.exists():
        with SOURCES_FILE.open("r", encoding="utf-8") as file:
            metadata = json.load(file)
    else:
        metadata = {
            "project": "CivicData Intelligence",
            "version": "0.1",
            "sources": [],
        }

    metadata["sources"].append(
        {
            "dataset": dataset,
            "publisher": publisher,
            "url": url,
            "filename": filename,
            "downloaded_at": datetime.now(timezone.utc).isoformat(),
        }
    )

    with SOURCES_FILE.open("w", encoding="utf-8") as file:
        json.dump(metadata, file, indent=2)


if __name__ == "__main__":
    print("CivicData Intelligence data acquisition layer")