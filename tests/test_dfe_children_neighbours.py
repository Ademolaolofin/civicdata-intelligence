from collections import Counter
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import runpy

import openpyxl
import pytest


ROOT = Path(__file__).resolve().parents[1]
BUILDER = runpy.run_path(str(ROOT / "src/civicdata/ingestion/build_dfe_children_neighbours.py"))
APP = runpy.run_path(str(ROOT / "src/civicdata/explorer.py"))


def test_rejects_an_unpinned_workbook():
    with pytest.raises(ValueError, match="SHA-256"):
        BUILDER["parse_workbook"](b"different release")


def test_rejects_unexpected_workbook_headers():
    workbook = openpyxl.Workbook()
    with pytest.raises(ValueError, match="unexpected source columns"):
        list(BUILDER["sheet_rows"](workbook.active, 1, BUILDER["EDGE_FIELDS"]))


@pytest.fixture(scope="module")
def published():
    path = BUILDER["WORKBOOK"]
    if not path.exists():
        pytest.skip(f"Official DfE workbook unavailable: {path.name}")
    return BUILDER["parse_workbook"](path.read_bytes())


def test_all_official_relationships_and_lookup_codes(published):
    workbook = openpyxl.load_workbook(BUILDER["WORKBOOK"], read_only=True, data_only=True)
    try:
        long = list(workbook["ModelLong"].iter_rows(min_row=5, max_row=1534, values_only=True))
        wide = list(workbook["ModelWide"].iter_rows(min_row=6, max_row=158, values_only=True))
        lookup = list(workbook["LALookup"].iter_rows(min_row=4, max_row=156, values_only=True))
    finally:
        workbook.close()
    actual = [tuple(row[k] for k in BUILDER["EDGE_FIELDS"]) for row in published["relationships"]]
    assert len(actual) == 1530 and set(actual) == set(long)
    assert Counter(Counter(row[0] for row in actual).values()) == {10: 153}
    assert {(row[0], row[2], row[3], row[5].strip().casefold()) for row in actual} == {
        (row[0], rank, row[2 * rank], row[2 * rank + 1].strip().casefold())
        for row in wide for rank in range(1, 11)
    }
    assert {tuple(row[k] for k in BUILDER["LOOKUP_FIELDS"]) for row in published["authorities"]} == set(lookup)
    assert published["release"]["sha256"] == sha256(BUILDER["WORKBOOK"].read_bytes()).hexdigest()
    assert published["release"]["publication_date"] == "2025-05-28"


@pytest.mark.parametrize(("change", "error"), [
    ({"SN": 2}, "duplicate DfE rank"),
    ({"SN_code": "E06000001"}, "Invalid directed"),
    ({"SN_prox": "Unknown"}, "Unknown DfE proximity"),
])
def test_rejects_invalid_relationship_artifact(published, tmp_path, change, error):
    invalid = deepcopy(published)
    invalid["relationships"][0].update(change)
    path = tmp_path / BUILDER["SNAPSHOT_NAME"]
    path.write_text(json.dumps(invalid), encoding="utf-8")
    with pytest.raises(ValueError, match=error):
        BUILDER["read_snapshot"](path)


@pytest.fixture(scope="module")
def explorer_data():
    directory = APP["DATA"]
    try:
        return APP["load_data"](directory)
    except ValueError as exc:
        if str(exc).startswith("Missing local snapshot"):
            pytest.skip(str(exc))
        raise


def test_model_selection_preserves_mhclg_default(explorer_data, published):
    children = APP["children_comparator"](published)
    default = APP["render"](explorer_data, {}, children)
    assert "2026 broad comparator set" in default and "15 of 15" in default
    assert "Sunderland" in default and "Published proximity" not in default
    selected = APP["render"](explorer_data, {"comparator": ["dfe"]}, children)
    assert "April 2023 upper-tier" in selected and "2025-05-28" in selected
    assert "Published proximity" in selected and "Redcar and Cleveland" in selected
    assert "10 of 10" in selected and "2026 broad comparator set" not in selected
    assert "Deprivation profile" in selected and "Good level of development" in selected


def test_coverage_and_successor_geography_are_distinct(explorer_data, published):
    children = APP["children_comparator"](published)
    render = APP["render"]
    def page(code):
        return render(explorer_data, {"comparator": ["dfe"], "authority": [code]}, children)

    assert "outside DfE Children’s Services comparator coverage" in page("E07000008")
    for old, new in APP["DFE_BOUNDARY_SUCCESSORS"].items():
        html = page(new)
        assert old in html and "Unresolved geography difference" in html
        assert "Published proximity" not in html
        assert old in set(children[1]["local_authority_code"])
    html = render(explorer_data, {"comparator": ["dfe"], "authority": ["E06000053"], "metric": ["27666"]}, children)
    assert "selected authority has no numeric observation" in html


def test_published_legacy_peer_rank_is_retained_without_outcome_join(explorer_data, published):
    _, peers = APP["children_comparator"](published)
    edge = peers.loc[
        peers["neighbour_code"].eq("E08000016")
        & peers["local_authority_code"].isin(explorer_data[0].index)
    ].iloc[0]
    _, rows, comparable, available = APP["comparison"](
        peers, explorer_data[3], edge.local_authority_code, "19346", "2024/25", children=True
    )
    row = next(row for row in rows if row[2] == "E08000016")
    assert row[:5] == (edge["rank"], "Barnsley", "E08000016", "—", "—")
    assert "outcome join withheld" in row[5] and row[6] == edge.proximity
    assert comparable <= available <= 9


def test_dfe_selection_without_local_snapshot(explorer_data):
    html = APP["render"](explorer_data, {"comparator": ["dfe"]})
    assert "model snapshot is unavailable locally" in html
    assert "2026 broad comparator set" not in html


@pytest.mark.parametrize(("target_level", "peer_level"), [
    ("Local authority district", "Local authority district"),
    ("Local authority district", "Local authority"),
    ("Local authority", "Local authority district"),
])
def test_district_level_observations_do_not_qualify_for_dfe_model(
    explorer_data, published, target_level, peer_level
):
    children = APP["children_comparator"](published)
    authorities, mhclg, deprivation, outcomes, dataset = explorer_data
    changed = outcomes.copy()
    changed.loc[:, "source_geography"] = peer_level
    changed.loc[changed["authority_code"].eq("E06000001"), "source_geography"] = target_level
    _, rows, comparable, available = APP["comparison"](
        children[1], changed, "E06000001", "19346", "2024/25", children=True
    )
    assert (comparable, available) == (0, 10)
    assert all(row[5] == "Different source geography or series metadata" for row in rows)
    data = authorities, mhclg, deprivation, changed, dataset
    query = {"comparator": ["dfe"]}
    html = APP["render"](data, query, children)
    assert "10 of 10" in html
    if target_level == "Local authority district":
        assert "outside the DfE model geography level" in html
    else:
        assert "0 qualify for comparison" in html
    assert "Different source geography or series metadata" in html
