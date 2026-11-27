"""Pivot validated observations without imputing unavailable components."""
from collections import Counter

from .transform import MAX_COUNT
from .validation import issue

KEY = ("reference_date", "territory_id", "education_category_id")
METADATA = """reference_date territory_id territory_name territory_level education_category_id
parent_category_id education_category_name_original education_category_name_en education_category_path
hierarchy_level category_type is_aggregate source_file source_sheet""".split()
MEASURES = dict(zip("BCDEFGH", ["total","male","female","urban","rural","no_completed_education","under_2_years"], strict=True))
DERIVED = "resident_population_total"
FIELDS = [*METADATA[:-2], *MEASURES.values(), DERIVED,
          *(name + "_status" for name in MEASURES.values()), DERIVED + "_status",
          DERIVED + "_method", *METADATA[-2:]]

def pivot(records: list[dict], settings, categories) -> tuple[list[dict], list[dict]]:
    rows: dict[tuple, dict] = {}
    facts = Counter()
    findings = []
    for record in records:
        key = tuple(record[field] for field in KEY)
        column = record["source_column"]
        if column not in MEASURES or column in "GH" and key[2] != "territory_total":
            findings.append(issue(21, "ERROR", "Unexpected dashboard measure placement", record))
            continue
        name = MEASURES[column]
        row = rows.setdefault(key, {field: record[field] for field in METADATA})
        if name in row or any(row[field] != record[field] for field in METADATA):
            findings.append(issue(21, "ERROR", "Duplicate measure or inconsistent dashboard metadata", record))
        row[name] = record["population_count"]
        row[name + "_status"] = record["value_status"]
        facts[(key, column, record["population_count"], record["value_status"])] += 1

    observed = set(rows)
    days = {key[0] for key in observed}
    expected = {(day, territory["territory_id"], category.education_category_id)
                for day in days for territory in settings.territories.values()
                for category in categories.values() if category.category_type != "heading"}
    if not observed or observed != expected or len(days) != 1:
        findings.append(issue(21, "ERROR", "Dashboard worksheet or classification coverage mismatch",
                              expected_value=len(expected), observed_value=len(observed)))

    reconstructed = Counter()
    for key, row in sorted(rows.items()):
        territorial = key[2] == "territory_total"
        for column, name in MEASURES.items():
            status_field = name + "_status"
            if name not in row:
                applicable = territorial or column not in "GH"
                row[name] = None
                row[status_field] = "missing_observation" if applicable else "not_applicable"
                if applicable:
                    findings.append(issue(21, "ERROR", f"Dashboard measure missing: {name}", row))
            else:
                reconstructed[(key, column, row[name], row[status_field])] += 1
                value = row[name]
                status = row[status_field]
                if status not in {"numeric", "blank", "confidential", "dash_unresolved"} or (
                    status == "numeric" and (type(value) is not int or not 0 <= value <= MAX_COUNT)
                    or status != "numeric" and value is not None
                ):
                    findings.append(issue(21, "ERROR", f"Invalid value/status pair: {name}", row))
        components = ("total", "no_completed_education", "under_2_years")
        row[DERIVED] = None
        row[DERIVED + "_method"] = None
        row[DERIVED + "_status"] = "not_evaluable" if territorial else "not_applicable"
        if territorial and all(row[name + "_status"] == "numeric" and type(row[name]) is int for name in components):
            row[DERIVED] = sum(row[name] for name in components)
            row[DERIVED + "_status"] = "numeric"
            row[DERIVED + "_method"] = "calculated"

    if facts != reconstructed or sum(facts.values()) != len(records):
        findings.append(issue(21, "ERROR", "Long-to-wide observation reconciliation failed"))
    if not findings:
        findings.append(issue(21, "INFO", "Full coverage and long-to-wide value/status reconciliation passed",
                              expected_value=len(records), observed_value=sum(reconstructed.values())))
    return [rows[key] for key in sorted(rows)], findings
