"""Export the single-authority proof-of-concept release from validated snapshots."""

from hashlib import sha256
import json
from pathlib import Path
import sys

import pandas as pd


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "src"))

from civicdata import explorer
from civicdata.ingestion.build_dfe_children_neighbours import SNAPSHOT_NAME, read_snapshot


def export():
    authority = "E06000001"
    authorities, mhclg, deprivation, outcomes, dataset = explorer.load_data(explorer.DATA)
    # Explorer's comparison expects empty strings for unavailable source values.
    # Normalise pandas missing scalars and numeric inputs before using that contract.
    outcomes = outcomes.assign(
        value=outcomes["value"].map(lambda value: "" if pd.isna(value) else str(value))
    )
    dfe_release, dfe = explorer.children_comparator(
        read_snapshot(explorer.DATA / SNAPSHOT_NAME)
    )
    files = (
        "mhclg_neighbour_relationships_2026.csv", "iod_2025_lad_official_summaries.csv",
        "lof_dfe_eyfs_observations.csv", SNAPSHOT_NAME,
    )
    hashes = {name: sha256((explorer.DATA / name).read_bytes()).hexdigest() for name in files}
    release_id = sha256("".join(hashes.values()).encode()).hexdigest()[:16]
    metrics = []
    for metric, (label, definition) in explorer.METRICS.items():
        observations = outcomes.loc[
            outcomes["authority_code"].eq(authority) & outcomes["lg_inform_metric_id"].eq(metric)
        ].sort_values("period")
        if observations.empty:
            raise ValueError(f"Missing approved demonstration observations: {metric}")
        periods = []
        for observation in observations.itertuples(index=False):
            comparators = {}
            for model, peers, expected in (("mhclg", mhclg, 15), ("dfe", dfe, 10)):
                _, rows, comparable, available = explorer.comparison(
                    peers, outcomes, authority, metric, observation.period, children=model == "dfe"
                )
                if len(rows) != expected:
                    raise ValueError(f"Unexpected {model} coverage for the demonstration authority")
                comparators[model] = {
                    "available": available,
                    "comparable": comparable,
                    "peers": [
                        dict(zip(("rank", "name", "code", "value", "geography", "status", "proximity"), row))
                        for row in rows
                    ],
                }
            periods.append({
                "label": observation.period,
                "value": None if observation.value == "" else float(observation.value),
                "geography": observation.source_geography,
                "comparators": comparators,
            })
        metrics.append({
            "id": metric, "label": label, "definition": definition,
            "unit": explorer.EYFS_UNITS[metric], "periods": periods,
        })
    profile = deprivation.loc[authority]
    return {
        "schema": 1,
        "id": release_id,
        "inputHashes": hashes,
        "authority": {"code": authority, "name": authorities.loc[authority], "type": "Unitary authority"},
        "eyfsSource": {
            "name": dataset.source_dataset, "publisher": dataset.source_provider,
            "version": dataset.source_dataset_version, "url": dataset.source_url,
        },
        "models": {
            "mhclg": {
                "label": "MHCLG · broad Local Outcomes Framework", "release": "2026",
                "geography": "English local authorities", "url": explorer.NEIGHBOURS,
            },
            "dfe": {
                "label": "DfE · Children’s Services", "release": dfe_release["publication_date"],
                "geography": dfe_release["geography_vintage"], "url": dfe_release["release_url"],
            },
        },
        "deprivation": {
            "score": float(profile.imd_average_score),
            "rank": int(profile.imd_rank_of_average_score),
            "sourceCode": profile.source_authority_code,
            "release": "2025",
            "geography": "2024 local authority district",
            "url": explorer.DEPRIVATION,
        },
        "metrics": metrics,
    }


if __name__ == "__main__":
    path = HERE / ".build/release.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    release = export()
    path.write_text(json.dumps(release, ensure_ascii=False, allow_nan=False, indent=2) + "\n", encoding="utf-8")
    print(f"Exported release {release['id']} for {release['authority']['code']}")
