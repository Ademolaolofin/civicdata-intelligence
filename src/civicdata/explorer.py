"""Read-only local explorer for validated CivicData snapshots."""

from argparse import ArgumentParser
from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from math import isfinite
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pandas as pd


DATA = Path(__file__).resolve().parents[2] / "data" / "processed"
NEIGHBOURS = "https://www.gov.uk/government/publications/local-outcomes-framework/local-government-outcomes-statistical-neighbours-model"
DEPRIVATION = "https://www.gov.uk/government/statistics/english-indices-of-deprivation-2025"
METRICS = {
    "19346": ("Good level of development", "Share of assessed children achieving a good level of development at age 5."),
    "27666": ("Free school meals development gap", "Good level of development rate for children ineligible for free school meals minus the rate for eligible children."),
}
PROFILE = {
    "imd_average_score": "IMD average score",
    "imd_rank_of_average_score": "Rank of IMD average score (1 most deprived)",
    "imd_proportion_of_lsoas_in_most_deprived_10pct_nationally": "Share of neighbourhoods in England’s most deprived 10%",
    "income_average_score": "Income deprivation score",
    "employment_average_score": "Employment deprivation score",
    "education_average_score": "Education, skills and training deprivation score",
    "health_average_score": "Health deprivation and disability score",
    "crime_average_score": "Crime deprivation score",
    "barriers_average_score": "Barriers to housing and services score",
    "living_environment_average_score": "Living environment deprivation score",
}


def read_snapshot(directory, filename, columns, key):
    path = directory / filename
    try:
        frame = pd.read_csv(path, dtype=str, keep_default_na=False)
    except FileNotFoundError:
        raise ValueError(f"Missing local snapshot: {path}") from None
    missing = set(columns) - set(frame.columns)
    if missing:
        raise ValueError(f"{filename}: missing columns {', '.join(sorted(missing))}")
    if frame.empty or frame[key].eq("").any().any() or frame.duplicated(key).any():
        raise ValueError(f"{filename}: expected nonempty, unique keys {', '.join(key)}")
    return frame


def load_data(directory):
    peers = read_snapshot(directory, "mhclg_neighbour_relationships_2026.csv",
        ["local_authority_code", "local_authority_name", "neighbour_code", "neighbour_name", "rank"],
        ["local_authority_code", "rank"])
    peers["rank"] = peers["rank"].astype(int)
    groups = peers.groupby("local_authority_code")
    if (
        not groups["rank"].agg(set).map(lambda ranks: ranks == set(range(1, 16))).all()
        or peers.duplicated(["local_authority_code", "rank"]).any()
        or peers.duplicated(["local_authority_code", "neighbour_code"]).any()
        or peers["neighbour_code"].eq(peers["local_authority_code"]).any()
        or not peers["neighbour_code"].isin(peers["local_authority_code"]).all()
    ):
        raise ValueError("Expected 15 distinct published neighbours per authority, ranked 1–15")
    authorities = (
        peers[["local_authority_code", "local_authority_name"]].drop_duplicates()
        .set_index("local_authority_code")["local_authority_name"].sort_values()
    )
    if not authorities.index.is_unique:
        raise ValueError("Conflicting names for an MHCLG authority code")
    deprivation = read_snapshot(directory, "iod_2025_lad_official_summaries.csv",
        ["authority_code", "source_authority_code", *PROFILE], ["authority_code"]
    ).set_index("authority_code")
    outcomes = read_snapshot(directory, "lof_dfe_eyfs_observations.csv",
        ["lg_inform_metric_id", "authority_code", "period", "period_type", "unit", "value",
         "source_geography", "source_provider", "source_dataset", "source_dataset_version", "source_url"],
        ["lg_inform_metric_id", "authority_code", "period"])
    for frame, columns in ((deprivation, PROFILE), (outcomes, ["value"])):
        for column in columns:
            values = frame.loc[frame[column].ne(""), column]
            try:
                valid = values.map(lambda value: isfinite(float(value))).all()
            except ValueError:
                valid = False
            if not valid:
                raise ValueError(f"Expected finite numeric values or blanks in {column}")
    if set(outcomes["lg_inform_metric_id"]) != set(METRICS):
        raise ValueError("Expected both validated DfE EYFS metrics")
    return authorities, peers, deprivation, outcomes


def comparison(peers, outcomes, authority, metric, period):
    series = outcomes.loc[
        outcomes["lg_inform_metric_id"].eq(metric) & outcomes["period"].eq(period)
    ].set_index("authority_code")
    target = series.loc[authority] if authority in series.index else None
    ranked = peers.loc[peers["local_authority_code"].eq(authority)].sort_values("rank")
    rows = []
    comparable = 0
    for peer in ranked.itertuples(index=False):
        value, geography, status = "—", "—", "No source row"
        if peer.neighbour_code in series.index:
            record = series.loc[peer.neighbour_code]
            geography = record.source_geography
            value = display_value(record.value)
            if not record.value:
                status = "Unavailable in DfE output"
            elif target is None:
                status = "Selected authority has no source row"
            elif (
                record.source_geography != target.source_geography
                or record.unit != target.unit
                or record.source_dataset_version != target.source_dataset_version
                or record.period_type != target.period_type
            ):
                status = "Different source geography or series metadata"
            else:
                status = "Matching geography level"
                comparable += 1
        rows.append((peer.rank, peer.neighbour_name, peer.neighbour_code, value, geography, status))
    return target, rows, comparable


def display_value(value):
    return f"{float(value):.2f}" if value else "Unavailable"


def html_table(headers, rows):
    headings = "".join(f'<th scope="col">{escape(header)}</th>' for header in headers)
    body = "".join(
        "<tr>" + "".join(f"<td>{escape(str(value))}</td>" for value in row) + "</tr>"
        for row in rows
    )
    return f'<div class="scroll" tabindex="0"><table><thead><tr>{headings}</tr></thead><tbody>{body}</tbody></table></div>'


def select(name, label, options, selected):
    choices = "".join(
        f'<option value="{escape(key)}" {"selected" if key == selected else ""}>{escape(text)}</option>'
        for key, text in options
    )
    return f'<label>{label}<select name="{name}">{choices}</select></label>'


def render(data, query):
    authorities, peers, deprivation, outcomes = data
    default = "E06000001" if "E06000001" in authorities else authorities.index[0]
    authority = query.get("authority", [default])[0]
    metric = query.get("metric", ["19346"])[0]
    if authority not in authorities or metric not in METRICS:
        raise ValueError("Unknown authority or metric")
    periods = sorted(outcomes.loc[outcomes["lg_inform_metric_id"].eq(metric), "period"].unique(), reverse=True)
    if not periods:
        raise ValueError("No periods available for this metric")
    period = query.get("period", [periods[0]])[0]
    if period not in periods:
        raise ValueError("Unknown reporting period for this metric")
    title, definition = METRICS[metric]
    target, peer_rows, comparable = comparison(peers, outcomes, authority, metric, period)
    history = outcomes.loc[
        outcomes["authority_code"].eq(authority) & outcomes["lg_inform_metric_id"].eq(metric)
    ].set_index("period")
    outcome_rows = [
        (year, display_value(history.at[year, "value"]), history.at[year, "source_geography"])
        if year in history.index else (year, "No source row", "—")
        for year in periods
    ]
    source = target if target is not None else outcomes.loc[
        outcomes["lg_inform_metric_id"].eq(metric) & outcomes["period"].eq(period)
    ].iloc[0]
    selected = "No source row" if target is None else display_value(target.value)
    source_url = source.source_url if urlsplit(source.source_url).scheme == "https" else ""
    source_geography = "—" if target is None else target.source_geography
    profile = "<p>No matching deprivation record for this authority code.</p>"
    if authority in deprivation.index:
        row = deprivation.loc[authority]
        profile_rows = [
            (label, f"{float(row[key]):.1%}" if row[key] and "_proportion_" in key else row[key] or "Unavailable")
            for key, label in PROFILE.items()
        ]
        profile = (
            f"<p>Source geography: 2024 local authority district · <strong>{escape(row.source_authority_code)}</strong></p>"
            + (f"<p>Published code linked to CivicData authority {escape(authority)} by the existing geography mapping.</p>"
               if row.source_authority_code != authority else "")
            + html_table(["Measure", "Published value"], profile_rows)
        )
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>CivicData Explorer</title><style>{STYLE}</style></head><body>
<header><div class="wrap mast"><strong>CivicData Explorer</strong><span>Local Outcomes Framework · v0.1</span></div></header>
<main class="wrap">
<h1>{escape(authorities[authority])}</h1><p class="sub">{escape(authority)} · English local authority</p>
<form method="get">
{select("authority", "Authority", ((code, f"{name} ({code})") for code, name in authorities.items()), authority)}
{select("metric", "EYFS measure", ((key, item[0]) for key, item in METRICS.items()), metric)}
{select("period", "Academic year", ((year, year) for year in periods), period)}
<button type="submit">Apply filters</button></form>
<div class="grid">
<section><h2>{title}</h2><p>{definition}</p>
<p class="value">{selected} <small>{escape(source.unit) if target is not None and target.value else ""}</small></p>
<p>{escape(period)} · {escape(source_geography)}</p>
{html_table(["Academic year", "Value", "Source geography"], outcome_rows)}
<p><a href="{escape(source_url)}">{escape(source.source_provider)} · {escape(source.source_dataset)}</a>
 · release {escape(source.source_dataset_version)} · {escape(source.unit)}</p>
<p>Unavailable means the DfE output contains a row with a blank value. It does not retain a reason for suppression or missingness.</p>
</section>
<section><h2>Deprivation profile</h2><p><a href="{DEPRIVATION}">English Indices of Deprivation 2025 · File 10</a></p>{profile}</section>
</div>
<section><h2>Statistical neighbours</h2>
<p><a href="{NEIGHBOURS}">MHCLG Local Outcomes Framework · 2026 broad comparator set</a></p>
<p><strong>{comparable} of {len(peer_rows)}</strong> published peers have a numeric value with matching geography level and series metadata.
Displayed peer values retain their source geography. Use caution when interpreting geography or boundary changes.</p>
{html_table(["Published rank", "Authority", "Code", f"Value ({source.unit})", "Source geography", "Comparison status"], peer_rows)}
<dl><dt>Children’s Services statistical neighbours</dt><dd>Unavailable in the local snapshots.</dd>
<dt>Adult Social Care statistical neighbours</dt><dd>Unavailable in the local snapshots.</dd></dl>
</section></main></body></html>"""


STYLE = """
:root{font:16px/1.55 system-ui,sans-serif;color:#182847;background:#eef2f7}
*{box-sizing:border-box}body{margin:0}header{background:#152544;color:white}
.wrap{width:min(1190px,94%);margin:auto}.mast{display:flex;flex-wrap:wrap;gap:.5rem 1.5rem;padding:1rem 0}
.mast span,.sub{color:#526480}.mast span{color:#d3e0f3}main{padding:1.6rem 0 3rem}
h1{font-size:clamp(2rem,5vw,3.5rem);line-height:1.1;margin:0}h2{font-size:1.3rem;margin-top:0}
.sub{margin:.4rem 0 1.2rem}form,section{background:white;border:1px solid #d2dcec;border-radius:.8rem;padding:1.3rem}
form{display:flex;flex-wrap:wrap;align-items:end;gap:1rem;margin-bottom:1rem}
label{display:grid;gap:.3rem;font-weight:650;max-width:100%;flex:1 1 12rem}
select,button{font:inherit;border-radius:.35rem;padding:.55rem .7rem;min-width:0;color:inherit;border:1px solid #8494ad}
select{appearance:none;background:white url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='16' height='16'%3E%3Cpath fill='none' stroke='%23182847' stroke-width='2' d='m3 6 5 5 5-5'/%3E%3C/svg%3E") no-repeat right .6rem center;padding-right:2rem}
button{background:#115e59;color:white;cursor:pointer}.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:1rem;margin-bottom:1rem}
.value{font-size:2.5rem;font-weight:750;color:#115e59;margin:.2rem 0}.value small{font-size:1rem}
.scroll{overflow:auto}table{width:100%;border-collapse:collapse;text-align:left}
th,td{padding:.48rem .55rem;border-bottom:1px solid #dbe4ef}th{background:#edf4fb}
a{color:#075985}dt{font-weight:650}dd{margin:0 0 .6rem}
@media(max-width:760px){.grid{grid-template-columns:1fr}}
"""


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=DATA, help="Directory containing the processed CSVs")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    try:
        data = load_data(args.data_dir)
    except ValueError as exc:
        parser.error(str(exc))

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            url = urlsplit(self.path)
            if url.path != "/":
                self.send_error(404)
                return
            try:
                body = render(data, parse_qs(url.query, keep_blank_values=True)).encode("utf-8")
            except ValueError as exc:
                self.send_error(400, str(exc))
                return
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    with ThreadingHTTPServer(("127.0.0.1", args.port), Handler) as server:
        print(f"CivicData Explorer: http://127.0.0.1:{server.server_port}/", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
