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
        {"lg_inform_metric_id": metric, "authority_code": codes[i], "period": "2024/25",
         "period_type": "Academic year", "unit": unit, "value": value,
         "source_geography": geography, "source_provider": "DfE", "source_dataset": "EYFS",
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
    authorities, peers, deprivation, outcomes = APP["load_data"](snapshots)
    target, rows, coverage = APP["comparison"](peers, outcomes, "E06000000", "19346", "2024/25")
    assert len(authorities) == 16 and len(deprivation) == 1
    assert target.value == "65"
    assert coverage == 1 and [row[0] for row in rows] == list(range(1, 16))
    assert rows[0] == (1, "Authority 15", "E06000015", "0.00", "Local authority", "Matching geography level")
    assert rows[1][-1] == "Different source geography or series metadata"
    assert rows[2][3:] == ("Unavailable", "Local authority", "Unavailable in DfE output")
    assert rows[3][-1] == "No source row"


def test_render_exposes_units_mapping_and_service_set_availability(snapshots):
    data = APP["load_data"](snapshots)
    html = APP["render"](data, {"authority": ["E06000000"], "metric": ["27666"], "period": ["2024/25"]})
    for text in ("12.5%", "E06000999", "Percentage point", "Children’s Services statistical neighbours",
                 "Adult Social Care statistical neighbours", "1 of 15", "https://example.test/eyfs"):
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
