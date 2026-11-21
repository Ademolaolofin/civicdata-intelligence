"""Source checks for the bounded Hartlepool demonstration."""

import json
from pathlib import Path
import runpy
from shutil import copy2

import pytest


MODULE = runpy.run_path(str(Path(__file__).with_name("pilot_release.py")))


@pytest.fixture
def snapshot():
    directory = MODULE["RAW"]
    if not (directory / "nspl-2026-08.json").is_file():
        pytest.skip("Requires the official local Hartlepool postcode fixture")
    return directory


def test_official_postcodes_and_deprivation(snapshot):
    pilot = MODULE["build"](snapshot)
    assert pilot["postcodes"] == {
        "TS24 0XZ": {"area": None, "terminated": 202508},
        "TS24 8AY": {"area": "E01011974", "terminated": None},
    }
    assert pilot["areas"] == {"E01011974": {"name": "Hartlepool 015B", "rank": 678, "decile": 1}}
    assert pilot["deprivation"]["sha256"] == MODULE["WORKBOOK_HASH"]


@pytest.mark.parametrize(("field", "value"), [("lad26cd", "E06000002"), ("lsoa21cd", "E01000001")])
def test_lookup_conflicting_geography_is_rejected(snapshot, tmp_path, field, value):
    lookup = json.loads((snapshot / "nspl-2026-08.json").read_bytes())
    current = next(item["attributes"] for item in lookup["features"] if item["attributes"]["doterm"] is None)
    current[field] = value
    (tmp_path / "nspl-2026-08.json").write_text(json.dumps(lookup), encoding="utf-8")
    copy2(snapshot / "imd-2025-file1.xlsx", tmp_path)
    with pytest.raises(ValueError, match="geography"):
        MODULE["build"](tmp_path)
