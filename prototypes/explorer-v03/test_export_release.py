"""Regression checks for zero and missing values in a prototype data release."""

import json
from pathlib import Path
import runpy

import pandas as pd
import pytest


@pytest.fixture
def exporter(monkeypatch):
    root = Path(__file__).resolve().parents[2]
    if not (root / "src/civicdata/ingestion/build_dfe_children_neighbours.py").is_file():
        pytest.skip("Requires the v0.2 comparator implementation from PR #4")
    monkeypatch.syspath_prepend(str(root / "src"))
    return runpy.run_path(str(Path(__file__).with_name("export_release.py")))


@pytest.mark.parametrize("missing", ["", None, float("nan"), pd.NA])
def test_zero_and_missing_values_in_release(exporter, monkeypatch, missing):
    app = exporter["explorer"]
    if not all((app.DATA / filename).is_file() for filename in (
        "mhclg_neighbour_relationships_2026.csv", "iod_2025_lad_official_summaries.csv",
        "lof_dfe_eyfs_observations.csv", exporter["SNAPSHOT_NAME"],
    )):
        pytest.skip("Requires the validated Explorer snapshots and the built DfE comparator")
    authorities, peers, deprivation, outcomes, dataset = app.load_data(app.DATA)
    outcomes = outcomes.assign(value=outcomes["value"].astype(object))
    sample = outcomes["lg_inform_metric_id"].eq("19346") & outcomes["period"].eq("2024/25")
    outcomes.loc[sample & outcomes["authority_code"].isin(["E06000001", "E08000024"]), "value"] = 0
    outcomes.loc[sample & outcomes["authority_code"].eq("E06000003"), "value"] = missing
    target_missing = (
        outcomes["lg_inform_metric_id"].eq("27666") & outcomes["period"].eq("2024/25")
        & outcomes["authority_code"].eq("E06000001")
    )
    outcomes.loc[target_missing, "value"] = missing
    monkeypatch.setattr(app, "load_data", lambda _: (authorities, peers, deprivation, outcomes, dataset))

    release = json.loads(json.dumps(exporter["export"](), allow_nan=False))
    development, gap = (metric["periods"][-1] for metric in release["metrics"])
    assert development["value"] == 0
    assert gap["value"] is None
    for model in ("mhclg", "dfe"):
        comparison = development["comparators"][model]
        peers_by_code = {peer["code"]: peer for peer in comparison["peers"]}
        assert peers_by_code["E08000024"]["value"] == "0.00"
        assert peers_by_code["E08000024"]["status"] == "Matching geography level"
        assert gap["comparators"][model]["comparable"] == 0
    dfe = development["comparators"]["dfe"]
    assert next(peer for peer in dfe["peers"] if peer["code"] == "E06000003")["value"] == "Unavailable"
    assert (dfe["available"], dfe["comparable"]) == (9, 9)
