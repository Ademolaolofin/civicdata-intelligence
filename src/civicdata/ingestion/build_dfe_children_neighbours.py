"""Validate the May 2025 DfE comparator workbook and write a versioned snapshot."""

from argparse import ArgumentParser
from collections import defaultdict
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import re
from tempfile import NamedTemporaryFile

from openpyxl import load_workbook


ROOT = Path(__file__).resolve().parents[3]
WORKBOOK = ROOT / "data/raw/dfe/childrens_services_statistical_neighbours_2025_05.xlsx"
SNAPSHOT_NAME = "dfe_children_neighbours_2025_05_v1.json"
RELEASE = {
    "model": "DfE Children’s Services statistical neighbours",
    "publisher": "Department for Education",
    "workbook_version": "v1",
    "publication_date": "2025-05-28",
    "geography_vintage": "April 2023 upper-tier local authorities in England",
    "release_url": "https://www.gov.uk/government/publications/local-authority-interactive-tool-lait",
    "workbook_url": "https://assets.publishing.service.gov.uk/media/682dd813e9440506ee95390e/Children_s_services_statistical_neighbour_benchmarking_tool.xlsx",
    "sha256": "8ede025998c03ae4aff25b5db8b3cc1a85887e2acef3b42f9109c9dc4b78a89a",
    "relationship_sheet": "ModelLong",
}
EDGE_FIELDS = ("la_code", "la_name", "SN", "SN_code", "SN_name", "SN_prox")
LOOKUP_FIELDS = ("la_code", "old_la_code", "la_name", "region_code", "region_name")
PROXIMITIES = {"extremely close", "very close", "close", "somewhat close", "not close"}


def sheet_rows(sheet, header_row, columns):
    header, *records = sheet.iter_rows(min_row=header_row, max_col=len(columns), values_only=True)
    if header != columns:
        raise ValueError(f"{sheet.title}: unexpected source columns")
    for row in records:
        if all(value is None for value in row):
            continue
        if row[0] == "Back to Index" and all(value is None for value in row[1:]):
            continue
        if not isinstance(row[0], str) or not re.fullmatch(r"E[0-9]{8}", row[0]):
            raise ValueError(f"{sheet.title}: invalid authority code")
        yield row


def normalise_proximity(value):
    if not isinstance(value, str) or value.strip().casefold() not in PROXIMITIES:
        raise ValueError("Unknown DfE proximity category")
    return value.strip().casefold()


def validate_snapshot(snapshot):
    if snapshot["release"] != RELEASE:
        raise ValueError("Unexpected DfE release metadata")
    authorities = snapshot["authorities"]
    lookup = {row["la_code"]: row["la_name"] for row in authorities}
    if len(authorities) != 153 or len(lookup) != 153:
        raise ValueError("Expected 153 unique DfE authority codes")
    if len({row["old_la_code"] for row in authorities}) != 153 or any(
        not isinstance(code, str) or not re.fullmatch(r"E[0-9]{8}", code) or not name
        for code, name in lookup.items()
    ) or any(type(row["old_la_code"]) is not int for row in authorities):
        raise ValueError("Invalid DfE authority lookup identifiers")
    ranks = defaultdict(set)
    pairs = set()
    for edge in snapshot["relationships"]:
        target, peer, rank = (edge[key] for key in ("la_code", "SN_code", "SN"))
        if target == peer or target not in lookup or peer not in lookup:
            raise ValueError("Invalid directed DfE authority relationship")
        if edge["la_name"] != lookup[target] or edge["SN_name"] != lookup[peer]:
            raise ValueError("DfE relationship names differ from the authority lookup")
        if type(rank) is not int or rank in ranks[target] or (target, peer) in pairs:
            raise ValueError("Invalid or duplicate DfE rank or directed pair")
        normalise_proximity(edge["SN_prox"])
        ranks[target].add(rank)
        pairs.add((target, peer))
    if len(pairs) != 1530 or ranks.keys() != lookup.keys() or any(
        rank_set != set(range(1, 11)) for rank_set in ranks.values()
    ):
        raise ValueError("Expected 1,530 directed relationships with ranks 1–10 per authority")
    return snapshot


def parse_workbook(content):
    if sha256(content).hexdigest() != RELEASE["sha256"]:
        raise ValueError("Workbook SHA-256 differs from the pinned May 2025 DfE release")
    workbook = load_workbook(BytesIO(content), read_only=True, data_only=True)
    try:
        edges = list(sheet_rows(workbook["ModelLong"], 4, EDGE_FIELDS))
        lookup = list(sheet_rows(workbook["LALookup"], 3, LOOKUP_FIELDS))
        wide_fields = ("la_code", "la_name") + tuple(
            column for rank in range(1, 11) for column in (f"SN_{rank}", f"SN_{rank}P")
        )
        wide = list(sheet_rows(workbook["ModelWide"], 5, wide_fields))
        long_edges = {(a, rank, peer, normalise_proximity(prox)) for a, _, rank, peer, _, prox in edges}
        wide_edges = {
            (row[0], rank, row[2 * rank], normalise_proximity(row[2 * rank + 1]))
            for row in wide for rank in range(1, 11)
        }
        if len(wide) != 153 or long_edges != wide_edges:
            raise ValueError("DfE ModelLong and ModelWide disagree on membership, rank or proximity")
        return validate_snapshot({
            "release": RELEASE.copy(),
            "authorities": [dict(zip(LOOKUP_FIELDS, row)) for row in sorted(lookup)],
            "relationships": [dict(zip(EDGE_FIELDS, row)) for row in sorted(edges, key=lambda row: (row[0], row[2]))],
        })
    finally:
        workbook.close()


def read_snapshot(path):
    try:
        return validate_snapshot(json.loads(path.read_text(encoding="utf-8")))
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"{path.name}: invalid DfE snapshot ({exc})") from exc


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--workbook", type=Path, default=WORKBOOK)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "data/processed")
    args = parser.parse_args()
    try:
        snapshot = parse_workbook(args.workbook.read_bytes())
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    args.output_dir.mkdir(parents=True, exist_ok=True)
    path = args.output_dir / SNAPSHOT_NAME
    with NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n", dir=path.parent, delete=False) as output:
        temporary = Path(output.name)
        try:
            json.dump(snapshot, output, ensure_ascii=False, indent=2)
            output.write("\n")
            output.close()
            temporary.replace(path)
        finally:
            output.close()
            temporary.unlink(missing_ok=True)
    print(f"{path}: 153 authorities, 1,530 validated directed relationships")


if __name__ == "__main__":
    main()
