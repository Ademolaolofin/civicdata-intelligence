from pathlib import Path
import hashlib
import re
import urllib.request

import pandas as pd
from bs4 import BeautifulSoup


PROJECT_ROOT = Path(__file__).resolve().parents[3]

OUTPUT_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "lof_metric_catalogue.csv"
)

OUTCOMES_OUTPUT_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "lof_outcomes.csv"
)

SOURCE_URL = (
    "https://www.gov.uk/government/publications/"
    "local-outcomes-framework/"
    "local-outcomes-framework-priority-outcomes-and-metrics--2"
)

SOURCE_ORGANISATION = (
    "Ministry of Housing, Communities and Local Government"
)

SOURCE_PUBLICATION = "Local Outcomes Framework"

SOURCE_UPDATED = "2026-09-14"


CATALOGUE_COLUMNS = [
    "outcome_id",
    "outcome_name",
    "metric_id",
    "metric_name",
    "metric_type",
    "metric_status",
    "source_organisation",
    "source_dataset",
    "source_url",
    "geography",
    "update_frequency",
    "lg_inform_available",
    "lg_inform_metric_id",
    "lg_inform_metric_title",
    "lg_inform_collection",
    "lg_inform_unit",
    "lg_inform_polarity",
    "lg_inform_period",
    "lg_inform_metric_uri",
    "notes",
    ]


OUTCOME_COLUMNS = [
    "outcome_id",
    "outcome_name",
    "outcome_description",
    "outcome_category",
    "source_publication",
    "source_url",
    "source_updated",
]


def clean_text(value: str) -> str:
    """Normalise whitespace while preserving source wording."""

    if not value:
        return ""

    return re.sub(
        r"\s+",
        " ",
        value,
    ).strip()


def generate_metric_id(
    metric_name: str,
) -> str:
    """
    Generate a reproducible CivicData identifier from the
    official metric wording.

    The identifier is not an MHCLG metric ID.
    """

    normalised = clean_text(
        metric_name
    ).lower()

    digest = hashlib.sha1(
        normalised.encode("utf-8")
    ).hexdigest()[:12]

    return f"lof_metric_{digest}"


def extract_outcome_number(
    heading: str,
) -> int:
    """Extract the numeric outcome identifier."""

    match = re.match(
        r"^\s*(\d+)\.",
        heading,
    )

    if not match:
        raise ValueError(
            f"Could not identify outcome number: {heading}"
        )

    return int(match.group(1))


def extract_outcome_name(
    heading: str,
) -> str:
    """Remove the numeric prefix from an outcome heading."""

    return clean_text(
        re.sub(
            r"^\s*\d+\.\s*",
            "",
            heading,
        )
    )


def classify_outcome(
    outcome_name: str,
) -> str:
    """
    Preserve the distinction between standard and contextual
    outcomes from the official LOF wording.
    """

    if "contextual outcome" in outcome_name.lower():
        return "contextual outcome"

    return "priority outcome"


def remove_placeholder_text(
    metric_text: str,
) -> str:
    """Remove placeholder annotations from metric wording."""

    text = re.sub(
        r"\[\s*placeholder(?:,\s*ready by launch)?\s*\]",
        "",
        metric_text,
        flags=re.IGNORECASE,
    )

    return clean_text(text)


def identify_metric_status(
    metric_text: str,
) -> str:
    """Classify explicitly identified placeholders."""

    if re.search(
        r"\[\s*placeholder",
        metric_text,
        flags=re.IGNORECASE,
    ):
        return "placeholder"

    return "available"


def identify_source_organisation(
    list_item,
) -> str | None:
    """
    Capture the source label displayed by MHCLG.

    This deliberately uses the page's own source label rather
    than trying to infer a department from the destination URL.
    """

    links = list_item.find_all(
        "a",
        href=True,
    )

    if not links:
        return None

    source_labels = [
        clean_text(link.get_text(" ", strip=True))
        for link in links
        if clean_text(
            link.get_text(" ", strip=True)
        )
    ]

    if not source_labels:
        return None

    return "; ".join(
        dict.fromkeys(source_labels)
    )


def identify_source_url(
    list_item,
) -> str | None:
    """Capture linked source URL from the official LOF page."""

    links = list_item.find_all(
        "a",
        href=True,
    )

    if not links:
        return None

    urls = []

    for link in links:
        href = link.get("href")

        if not href:
            continue

        if href.startswith("/"):
            href = (
                "https://www.gov.uk"
                f"{href}"
            )

        urls.append(href)

    if not urls:
        return None

    return "; ".join(
        dict.fromkeys(urls)
    )


def fetch_source() -> BeautifulSoup:
    """Download the current official MHCLG LOF metrics page."""

    print("\nDownloading official LOF metric definitions...")

    request = urllib.request.Request(
        SOURCE_URL,
        headers={
            "User-Agent": (
                "CivicData-Intelligence/0.1 "
                "(public-data research project)"
            )
        },
    )

    with urllib.request.urlopen(
        request,
        timeout=30,
    ) as response:
        html = response.read()

    print(
        f"Downloaded {len(html):,} bytes"
    )

    return BeautifulSoup(
        html,
        "html.parser",
    )


def find_content_root(
    soup: BeautifulSoup,
):
    """Locate the main GOV.UK publication content."""

    main = soup.find("main")

    if main is None:
        raise ValueError(
            "Could not locate GOV.UK main content."
        )

    return main


def extract_outcomes(
    main,
) -> pd.DataFrame:
    """Extract the 16 official LOF priority outcomes."""

    rows = []

    headings = main.find_all("h2")

    for heading in headings:
        heading_text = clean_text(
            heading.get_text(
                " ",
                strip=True,
            )
        )

        if not re.match(
            r"^\d+\.",
            heading_text,
        ):
            continue

        outcome_id = extract_outcome_number(
            heading_text
        )

        if not 1 <= outcome_id <= 16:
            continue

        outcome_name = extract_outcome_name(
            heading_text
        )

        description = None

        sibling = heading.find_next_sibling()

        while sibling is not None:
            if sibling.name in {
                "h2",
                "h3",
            }:
                break

            if sibling.name == "p":
                candidate = clean_text(
                    sibling.get_text(
                        " ",
                        strip=True,
                    )
                )

                if candidate:
                    description = candidate
                    break

            sibling = sibling.find_next_sibling()

        rows.append(
            {
                "outcome_id": outcome_id,
                "outcome_name": outcome_name,
                "outcome_description": description,
                "outcome_category": classify_outcome(
                    outcome_name
                ),
                "source_publication": SOURCE_PUBLICATION,
                "source_url": SOURCE_URL,
                "source_updated": SOURCE_UPDATED,
            }
        )

    outcomes = pd.DataFrame(
        rows,
        columns=OUTCOME_COLUMNS,
    )

    return outcomes


def extract_metrics(
    main,
    outcomes: pd.DataFrame,
) -> pd.DataFrame:
    """
    Extract metrics under Outcome metrics and Output metrics
    sections for each official LOF outcome.
    """

    rows = []

    for _, outcome in outcomes.iterrows():
        outcome_id = int(
            outcome["outcome_id"]
        )

        outcome_name = outcome[
            "outcome_name"
        ]

        target_heading = None

        for heading in main.find_all("h2"):
            heading_text = clean_text(
                heading.get_text(
                    " ",
                    strip=True,
                )
            )

            if not re.match(
                rf"^{outcome_id}\.",
                heading_text,
            ):
                continue

            target_heading = heading
            break

        if target_heading is None:
            continue

        current_metric_type = None

        element = target_heading.find_next_sibling()

        while element is not None:
            if element.name == "h2":
                break

            text = clean_text(
                element.get_text(
                    " ",
                    strip=True,
                )
            )

            if not text:
                element = element.find_next_sibling()
                continue

            lower_text = text.lower()

            if (
                element.name in {"h3", "p"}
                and lower_text.startswith(
                    "outcome metrics"
                )
            ):
                current_metric_type = (
                    "outcome metric"
                )

                element = element.find_next_sibling()
                continue

            if (
                element.name in {"h3", "p"}
                and lower_text.startswith(
                    "output metrics"
                )
            ):
                current_metric_type = (
                    "output metric"
                )

                element = element.find_next_sibling()
                continue

            if (
                current_metric_type
                and element.name in {
                    "ul",
                    "ol",
                }
            ):
                for list_item in element.find_all(
                    "li",
                    recursive=False,
                ):
                    raw_metric_text = clean_text(
                        list_item.get_text(
                            " ",
                            strip=True,
                        )
                    )

                    if not raw_metric_text:
                        continue

                    metric_status = (
                        identify_metric_status(
                            raw_metric_text
                        )
                    )

                    metric_name = (
                        remove_placeholder_text(
                            raw_metric_text
                        )
                    )

                    # Remove source labels enclosed in
                    # trailing parentheses from the display
                    # wording where possible.
                    metric_name = re.sub(
                        r"\s*\([^()]*\)\s*$",
                        "",
                        metric_name,
                    ).strip()

                    source_org = (
                        identify_source_organisation(
                            list_item
                        )
                    )

                    source_url = (
                        identify_source_url(
                            list_item
                        )
                    )

                    rows.append(
                        {
                            "outcome_id": outcome_id,
                            "outcome_name": outcome_name,
                            "metric_id": (
                                generate_metric_id(
                                    metric_name
                                )
                            ),
                            "metric_name": metric_name,
                            "metric_type": current_metric_type,
                            "metric_status": metric_status,
                            "source_organisation": source_org,
                            "source_dataset": None,
                            "source_url": source_url,
                            "geography": None,
                            "update_frequency": None,
                            "lg_inform_available": None,
                            "lg_inform_metric_id": None,
                            "lg_inform_metric_title": None,
                            "lg_inform_collection": None,
                            "lg_inform_unit": None,
                            "lg_inform_polarity": None,
                            "lg_inform_period": None,
                            "lg_inform_metric_uri": None,
                            "notes": (
                            "Extracted from the official "
                                "MHCLG Local Outcomes Framework "
                                "priority outcomes and metrics "
                                "publication."
                            ),
                        }
                    )

            element = element.find_next_sibling()

    catalogue = pd.DataFrame(
        rows,
        columns=CATALOGUE_COLUMNS,
    )

    return catalogue


def validate_outcomes(
    outcomes: pd.DataFrame,
) -> None:
    """Validate the extracted outcome structure."""

    print("\n=== OUTCOME VALIDATION ===")

    print(
        f"Outcomes extracted: "
        f"{len(outcomes):,}"
    )

    print(
        f"Unique outcome IDs: "
        f"{outcomes['outcome_id'].nunique():,}"
    )

    duplicate_ids = outcomes[
        "outcome_id"
    ].duplicated().sum()

    print(
        f"Duplicate outcome IDs: "
        f"{duplicate_ids:,}"
    )

    expected_ids = set(
        range(1, 17)
    )

    actual_ids = set(
        outcomes["outcome_id"].tolist()
    )

    missing_ids = sorted(
        expected_ids - actual_ids
    )

    if missing_ids:
        raise ValueError(
            "Missing LOF outcomes: "
            f"{missing_ids}"
        )

    if duplicate_ids:
        raise ValueError(
            "Duplicate LOF outcome IDs found."
        )

    if len(outcomes) != 16:
        raise ValueError(
            "Expected exactly 16 LOF outcomes."
        )

    print("Outcome validation PASS")


def validate_catalogue(
    catalogue: pd.DataFrame,
) -> None:
    """Validate the extracted LOF metric catalogue."""

    print("\n=== LOF CATALOGUE VALIDATION ===")

    missing_columns = [
        column
        for column in CATALOGUE_COLUMNS
        if column not in catalogue.columns
    ]

    if missing_columns:
        raise ValueError(
            "Missing catalogue columns: "
            f"{missing_columns}"
        )

    required_fields = [
        "outcome_id",
        "outcome_name",
        "metric_id",
        "metric_name",
        "metric_type",
        "metric_status",
    ]

    missing_required = {
        column: int(
            catalogue[column]
            .isna()
            .sum()
        )
        for column in required_fields
        if catalogue[column]
        .isna()
        .any()
    }

    if missing_required:
        raise ValueError(
            "Required catalogue fields contain "
            f"missing values: {missing_required}"
        )

    duplicate_relationships = (
        catalogue.duplicated(
            subset=[
                "outcome_id",
                "metric_id",
            ]
        ).sum()
    )

    if duplicate_relationships:
        raise ValueError(
            "Duplicate outcome-metric relationships: "
            f"{duplicate_relationships}"
        )

    print(
        f"Catalogue rows: "
        f"{len(catalogue):,}"
    )

    print(
        f"Outcomes represented by metrics: "
        f"{catalogue['outcome_id'].nunique():,}"
    )

    print(
        f"Unique metrics: "
        f"{catalogue['metric_id'].nunique():,}"
    )

    print(
        "Outcome-metric relationships: "
        f"{len(catalogue):,}"
    )

    print(
        "\nMetric types:"
    )

    for metric_type, count in (
        catalogue[
            "metric_type"
        ].value_counts().items()
    ):
        print(
            f"  {metric_type}: {count:,}"
        )

    print(
        "\nMetric status:"
    )

    for status, count in (
        catalogue[
            "metric_status"
        ].value_counts().items()
    ):
        print(
            f"  {status}: {count:,}"
        )

    print(
        "\nMetrics by outcome:"
    )

    outcome_counts = (
        catalogue.groupby(
            [
                "outcome_id",
                "outcome_name",
            ]
        )
        .size()
        .reset_index(
            name="metric_count"
        )
    )

    for _, row in (
        outcome_counts.iterrows()
    ):
        print(
            f"  {int(row['outcome_id']):02d} "
            f"{row['outcome_name']}: "
            f"{row['metric_count']}"
        )

    print(
        "\nCatalogue validation PASS"
    )


def save_outputs(
    outcomes: pd.DataFrame,
    catalogue: pd.DataFrame,
) -> None:
    """Save reproducible LOF reference outputs."""

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    outcomes[
        OUTCOME_COLUMNS
    ].to_csv(
        OUTCOMES_OUTPUT_PATH,
        index=False,
    )

    catalogue[
        CATALOGUE_COLUMNS
    ].to_csv(
        OUTPUT_PATH,
        index=False,
    )

    print(
        "\nOutcomes saved to: "
        f"{OUTCOMES_OUTPUT_PATH}"
    )

    print(
        "Metric catalogue saved to: "
        f"{OUTPUT_PATH}"
    )


def show_sample(
    catalogue: pd.DataFrame,
) -> None:
    """Display Economic Prosperity as a useful validation sample."""

    sample = catalogue[
        catalogue[
            "outcome_id"
        ] == 15
    ][
        [
            "metric_type",
            "metric_status",
            "metric_name",
            "source_organisation",
        ]
    ]

    print(
        "\n=== OUTCOME 15 SAMPLE ==="
    )

    print(
        sample.to_string(
            index=False
        )
    )


def main() -> None:
    """Build the CivicData official LOF reference catalogue."""

    print(
        "\n=== CIVICDATA LOCAL OUTCOMES "
        "FRAMEWORK CATALOGUE ==="
    )

    print(
        f"\nOfficial source updated: "
        f"{SOURCE_UPDATED}"
    )

    soup = fetch_source()

    main_content = find_content_root(
        soup
    )

    outcomes = extract_outcomes(
        main_content
    )

    validate_outcomes(
        outcomes
    )

    catalogue = extract_metrics(
        main_content,
        outcomes,
    )

    if catalogue.empty:
        raise ValueError(
            "No LOF metrics were extracted."
        )

    validate_catalogue(
        catalogue
    )

    save_outputs(
        outcomes,
        catalogue,
    )

    show_sample(
        catalogue
    )

    print(
        "\n=== COMPLETE ==="
    )

    print(
        f"Official LOF outcomes: "
        f"{len(outcomes):,}"
    )

    print(
        f"Unique metrics: "
        f"{catalogue['metric_id'].nunique():,}"
    )

    print(
        "Catalogue source: MHCLG"
    )


if __name__ == "__main__":
    main()