"""Build the bounded Hartlepool postcode/IMD fixture from official source files."""

from argparse import ArgumentParser
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import re

from openpyxl import load_workbook
import requests


RAW = Path(__file__).resolve().parents[2] / "data/raw/hartlepool-pilot"
LOOKUP = "https://services1.arcgis.com/ESMARspQHYMw9BZ9/arcgis/rest/services/National_Statistics_Postcode_Lookup_(August_2026)_for_the_United_Kingdom_(Hosted_Table)/FeatureServer/0"
IMD = "https://www.gov.uk/government/statistics/english-indices-of-deprivation-2025"
WORKBOOK = "https://assets.publishing.service.gov.uk/media/691dece32c6b98ecdbc500d5/File_1_IoD2025_Index_of_Multiple_Deprivation.xlsx"
WORKBOOK_HASH = "e2b10ed1b4d00c02cba12770a0d854b53f7ba7a103df8125744bedad4779866b"
PUBLIC_POSTCODES = {"TS24 8AY", "TS24 0XZ"}
HARTLEPOOL = "E06000001"


def fetch():
    lookup_response = requests.get(f"{LOOKUP}/query", params={
        "where": "pcds IN ('TS24 8AY','TS24 0XZ')",
        "outFields": "pcds,doterm,lsoa21cd,lad26cd",
        "returnGeometry": "false",
        "f": "json",
    }, timeout=25)
    lookup_response.raise_for_status()
    result = lookup_response.json()
    if "features" not in result or result.get("exceededTransferLimit"):
        raise ValueError("Unexpected ONS response")
    workbook = requests.get(WORKBOOK, timeout=25)
    workbook.raise_for_status()
    if sha256(workbook.content).hexdigest() != WORKBOOK_HASH:
        raise ValueError("Unexpected IMD File 1 workbook version")
    RAW.mkdir(parents=True, exist_ok=True)
    # Store raw response and pinned file locally. The browser consumes neither.
    (RAW / "nspl-2026-08.json").write_bytes(lookup_response.content)
    (RAW / "imd-2025-file1.xlsx").write_bytes(workbook.content)
    (RAW / "retrieved-at.txt").write_text(datetime.now(timezone.utc).isoformat(), encoding="utf-8")


def build(raw=RAW):
    postcode_path = raw / "nspl-2026-08.json"
    workbook_path = raw / "imd-2025-file1.xlsx"
    response = postcode_path.read_bytes()
    workbook_digest = sha256(workbook_path.read_bytes()).hexdigest()
    if workbook_digest != WORKBOOK_HASH:
        raise ValueError("Unexpected IMD File 1 workbook version")
    data = json.loads(response)
    if "features" not in data or data.get("exceededTransferLimit"):
        raise ValueError("Incomplete ONS postcode snapshot")
    rows = [feature["attributes"] for feature in data["features"]]
    if len(rows) != len(PUBLIC_POSTCODES) or {row["pcds"] for row in rows} != PUBLIC_POSTCODES:
        raise ValueError("Unexpected or duplicate postcode in bounded ONS snapshot")
    if any(row["lad26cd"] != HARTLEPOOL or not re.fullmatch(r"E010\d{5}", row["lsoa21cd"]) for row in rows):
        raise ValueError("Unexpected geography in bounded ONS snapshot")
    if any(row["doterm"] is not None and (
        type(row["doterm"]) is not int or not 1 <= row["doterm"] % 100 <= 12
    ) for row in rows):
        raise ValueError("Invalid ONS termination month")
    needed = {row["lsoa21cd"] for row in rows if row["doterm"] is None}
    if not needed:
        raise ValueError("No current postcode in pilot snapshot")
    source = load_workbook(workbook_path, read_only=True, data_only=True)
    try:
        found = [row for row in source["IMD25"].values if row and row[0] in needed]
    finally:
        source.close()
    if len(found) != len(needed) or {row[0] for row in found} != needed:
        raise ValueError("Missing or duplicate IMD geography")
    areas = {}
    for code, name, district, _, rank, decile, *_ in found:
        if district != HARTLEPOOL or type(rank) is not int or not 1 <= rank <= 32844 \
                or type(decile) is not int or not 1 <= decile <= 10:
            raise ValueError("IMD geography or observation does not match the pilot contract")
        areas[code] = {"name": name, "rank": rank, "decile": decile}
    return {
        "lookup": {"version": "August 2026", "url": LOOKUP, "sha256": sha256(response).hexdigest()},
        "deprivation": {"version": "2025", "url": IMD, "sha256": workbook_digest},
        "retrievedAt": (raw / "retrieved-at.txt").read_text(encoding="utf-8").strip(),
        "postcodes": {row["pcds"]: {
            "area": row["lsoa21cd"] if row["doterm"] is None else None,
            "terminated": row["doterm"],
        } for row in sorted(rows, key=lambda row: row["pcds"])},
        "areas": areas,
    }


if __name__ == "__main__":
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--fetch", action="store_true", help="Fetch fixed public-venue fixture sources")
    if parser.parse_args().fetch:
        fetch()
    pilot = build()
    print(f"Validated {len(pilot['postcodes'])} public postcode fixtures and {len(pilot['areas'])} IMD neighbourhood")
