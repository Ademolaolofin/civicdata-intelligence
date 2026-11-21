import runpy
from pathlib import Path

import pandas as pd
import pytest


APP = runpy.run_path(str(Path(__file__).resolve().parents[1] / "src/civicdata/explorer.py"))


@pytest.fixture
def snapshots(tmp_path):
    codes = [f"E060000{i:02d}" for i in range(16)]
    pd.DataFrame([
        (code, f"Authority {i}", peer, f"Authority {codes.index(peer)}", rank)
        for i, code in enumerate(codes)
        for rank, peer in enumerate(reversed([other for other in codes if other != code]), 1)
    ], columns=["local_authority_code", "local_authority_name", "neighbour_code", "neighbour_name", "rank"]
    ).iloc[::-1].to_csv(tmp_path / "mhclg_neighbour_relationships_2026.csv", index=False)
    pd.DataFrame([{"authority_code": codes[0], "source_authority_code": "E06000999",
                   **dict.fromkeys(APP["PROFILE"], "0.125")}]
    ).to_csv(tmp_path / "iod_2025_lad_official_summaries.csv", index=False)
    observations = [
        {"lg_inform_metric_id": metric, "authority_code": codes[i], "period": "2024/25", "time_period": "202425",
         "period_type": "Academic year", "unit": unit, "value": value,
         "source_geography": geography, "source_provider": "DfE", "source_dataset": "EYFS",
         "source_system": "Explore Education Statistics", "source_dataset_id": "eyfs",
         "source_dataset_version": "1.0.1", "source_url": "https://example.test/eyfs"}
        for metric, unit in (("19346", "Per cent"), ("27666", "Percentage point"))
        for i, geography, value in [
            (0, "Local authority", "65"), (15, "Local authority", "0"),
            (14, "Local authority district", "62"), (13, "Local authority", ""),
        ]
    ]
    pd.DataFrame(observations).to_csv(tmp_path / "lof_dfe_eyfs_observations.csv", index=False)
    return tmp_path


def test_load_and_compare_keeps_official_order_and_availability(snapshots):
    authorities, peers, deprivation, outcomes, _ = APP["load_data"](snapshots)
    target, rows, coverage, available = APP["comparison"](peers, outcomes, "E06000000", "19346", "2024/25")
    assert len(authorities) == 16 and len(deprivation) == 1
    assert target.value == "65"
    assert (coverage, available) == (1, 2)
    assert [row[0] for row in rows] == list(range(1, 16))
    assert rows[0] == (1, "Authority 15", "E06000015", "0.00", "Local authority", "Matching geography level")
    assert rows[1][-1] == "Different source geography or series metadata"
    assert rows[2][3:] == ("Unavailable", "Local authority", "Unavailable in DfE output")
    assert rows[3][-1] == "No source row"


def test_render_exposes_units_mapping_and_service_set_availability(snapshots):
    data = APP["load_data"](snapshots)
    html = APP["render"](data, {"authority": ["E06000000"], "metric": ["27666"], "period": ["2024/25"]})
    for text in ("12.5%", "E06000999", "Percentage point", "Children’s Services statistical neighbours",
                 "Adult Social Care statistical neighbours", "2 of 15", "1 qualify", "https://example.test/eyfs"):
        assert text in html
    with pytest.raises(ValueError, match="Unknown reporting period"):
        APP["render"](data, {"period": ["2099/00"]})


def test_snapshot_loader_rejects_duplicate_keys(snapshots):
    path = snapshots / "lof_dfe_eyfs_observations.csv"
    csv = path.read_text()
    path.write_text(csv + csv.splitlines()[1] + "\n")
    with pytest.raises(ValueError, match="unique keys"):
        APP["load_data"](snapshots)


def test_snapshot_loader_rejects_incomplete_peer_set(snapshots):
    path = snapshots / "mhclg_neighbour_relationships_2026.csv"
    path.write_text("\n".join(path.read_text().splitlines()[:-1]) + "\n")
    with pytest.raises(ValueError, match="15 distinct published neighbours"):
        APP["load_data"](snapshots)


def test_missing_snapshot_identifies_required_file(tmp_path):
    with pytest.raises(ValueError, match="Missing local snapshot:.*mhclg_neighbour_relationships_2026.csv"):
        APP["load_data"](tmp_path)


@pytest.mark.parametrize(("code", "reason", "note"), [
    ("E06000013", "Selected authority value is unavailable", "Selected observation is from"),
    ("E06000012", "Selected authority has no source row", "No observation provenance for this authority and year."),
])
def test_peer_availability_without_numeric_target(snapshots, code, reason, note):
    data = APP["load_data"](snapshots)
    _, rows, comparable, available = APP["comparison"](data[1], data[3], code, "19346", "2024/25")
    assert (comparable, available) == (0, 3)
    assert sum(row[-1] == reason for row in rows) == available
    html = APP["render"](data, {"authority": [code]})
    assert "3 of 15" in html and "Comparison unavailable" in html
    assert note in html and "Dataset metadata:" in html


@pytest.mark.parametrize(("column", "value", "error"), [
    ("source_geography", "Region", "source_geography"),
    ("period_type", "Calendar year", "period_type"),
    ("unit", "", "unit for metric"),
    ("unit", "Percentage point", "unit for metric"),
    ("period", "2024-25", "period label"),
    ("period", "2024/26", "period identifier"),
    ("time_period", "202324", "period identifier"),
    *[(column, " ", f"provenance: {column}") for column in APP["EYFS_PROVENANCE"]],
    ("source_dataset_version", "2.0.0", "consistent DfE EYFS dataset provenance"),
    ("value", "NaN", "finite numeric values"),
])
def test_invalid_eyfs_snapshot(snapshots, column, value, error):
    path = snapshots / "lof_dfe_eyfs_observations.csv"
    observations = pd.read_csv(path, dtype=str, keep_default_na=False)
    observations.loc[0, column] = value
    observations.to_csv(path, index=False)
    with pytest.raises(ValueError, match=error):
        APP["load_data"](snapshots)


@pytest.fixture(scope="module")
def production_snapshots():
    directory = APP["DATA"]
    required = [
        directory / "mhclg_neighbour_relationships_2026.csv",
        directory / "iod_2025_lad_official_summaries.csv",
        directory / "lof_dfe_eyfs_observations.csv",
    ]
    missing = [path.name for path in required if not path.is_file()]
    if missing:
        pytest.skip(f"Local Explorer snapshots unavailable: {', '.join(missing)}")
    return APP["load_data"](directory)


def test_production_relationships_match_workbook(production_snapshots):
    authorities, peers, *_ = production_snapshots
    assert len(authorities) == 317 and len(peers) == 4755
    workbook = APP["DATA"].parent / "raw" / "mhclg_statistical_neighbours_2026.xlsx"
    if not workbook.is_file():
        pytest.skip(f"Local published MHCLG workbook unavailable: {workbook.name}")
    wide = pd.read_excel(workbook, sheet_name="Statistical Neighbours", header=10, dtype=str)
    wide = wide.set_index("Local Authority: Code").dropna(subset=["Local Authority: Name"])
    assert wide.index.is_unique and set(wide.index) == set(authorities.index)
    for rank in range(1, 16):
        actual = peers.loc[peers["rank"].eq(rank)].set_index("local_authority_code")
        for tested, published in [("neighbour_code", "Code"), ("neighbour_name", "Name")]:
            assert actual[tested].to_dict() == wide[f"Neighbour {rank}: {published}"].to_dict()


def test_production_coverage_and_comparability(production_snapshots):
    authorities, peers, deprivation, outcomes, provenance = production_snapshots
    assert len(authorities) == 317 and len(peers) == 4755
    assert len(deprivation) == 296 and set(deprivation.index) <= set(authorities.index)
    assert set(outcomes["authority_code"]) == set(authorities.index)
    assert set(outcomes["source_geography"]) == {"Local authority", "Local authority district"}
    assert provenance.source_dataset_version == "1.0.1"
    assert outcomes.groupby(["lg_inform_metric_id", "period"]).size().to_dict() == {
        (metric, year): count
        for metric in ("19346", "27666")
        for year, count in zip(("2021/22", "2022/23", "2023/24", "2024/25"), (311, 313, 315, 317))
    }
    missing = outcomes.loc[outcomes["value"].eq("")]
    assert len(missing) == 4 and set(missing["authority_code"]) == {"E06000053"}
    assert set(missing["lg_inform_metric_id"]) == {"27666"}
    target, rows, comparable, available = APP["comparison"](peers, outcomes, "E06000001", "19346", "2024/25")
    assert target.source_geography == "Local authority"
    assert (comparable, available) == (15, 15)
    assert rows[0][:3] == (1, "Sunderland", "E08000024")
    target, _, comparable, available = APP["comparison"](peers, outcomes, "E06000053", "27666", "2024/25")
    assert target.value == "" and comparable == 0 and available == 15
