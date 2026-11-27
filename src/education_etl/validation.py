"""Validate coverage, provenance, logical keys and published marginal distributions."""
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import date
from itertools import product

from .extract import DASHES
from .transform import DIMENSIONS, FIELDS, KEY, MAX_COUNT, SOURCE_KEY, parse_count

NAMES = [
    "Worksheet coverage", "Worksheet structure", "Source metadata", "Territorial identifiers",
    "Education identifiers", "Classification integrity", "Observation key uniqueness", "Count domain",
    "Confidentiality", "Dash preservation", "Sex margins", "Residence margins",
    "Education aggregation", "Territorial aggregation", "Mandatory dimensions", "Unexpected labels",
    "Unexpected values", "Source reconciliation", "Source cell uniqueness", "PostgreSQL compatibility",
    "Dashboard coverage and reconciliation",
]

@dataclass(frozen=True)
class Result:
    rule_id: str
    rule_name: str
    severity: str
    territory_id: str = ""
    education_category_id: str = ""
    source_sheet: str = ""
    source_row: int | str = ""
    affected_columns: str = ""
    expected_value: object = None
    observed_value: object = None
    difference: int | None = None
    message: str = ""

def issue(number: int, severity: str, message: str, record: dict | None = None, **details) -> dict:
    record = record or {}
    location = {key: record.get(key, "") for key in ("territory_id", "education_category_id", "source_sheet", "source_row")}
    return asdict(Result(f"DQ{number:03}", NAMES[number - 1], severity, message=message, **(location | details)))

def compare(number: int, total: dict | None, members: list[dict | None], columns: str, scope: dict) -> dict:
    if any(row is None or row["value_status"] != "numeric" for row in [total, *members]):
        return issue(number, "NOT_EVALUABLE", "At least one comparable observation is absent or nonnumeric",
                     scope, affected_columns=columns)
    observed = int(total["population_count"])
    expected = sum(int(row["population_count"]) for row in members)
    return issue(number, "INFO" if observed == expected else "WARNING",
                 "Published total reconciles" if observed == expected else "Published totals differ",
                 scope, affected_columns=columns, expected_value=expected, observed_value=observed,
                 difference=observed - expected)

def read_records(frame) -> list[dict]:
    return frame.astype(object).where(frame.notna(), None).to_dict("records")

def validate_records(records: list[dict], settings, categories) -> list[dict]:
    results = []
    if not records:
        return [issue(15, "ERROR", "No observations available")]
    territories = {row["territory_id"]: row for row in settings.territories.values()}
    key_counts = Counter(tuple(row.get(k) for k in KEY) for row in records)
    source_counts = Counter(tuple(row.get(k) for k in SOURCE_KEY) for row in records)
    for row in records:
        source = row.get("source_column")
        raw = row.get("raw_value")
        count = row.get("population_count")
        status = row.get("value_status")
        category = categories.get(row.get("education_category_id"))
        territory = territories.get(row.get("territory_id"))
        required = set(FIELDS) - {"parent_category_id", "population_count", "raw_value"}
        if any(row.get(key) in (None, "") for key in required):
            results.append(issue(15, "ERROR", "Missing required fields", row))
        if territory is None or any(row.get(key) != territory[ref] for key, ref in
                                    (("territory_level", "territory_level"), ("territory_name", "territory_name_normalised"),
                                     ("source_sheet", "territory_name_original"))):
            results.append(issue(4, "ERROR", "Territory or worksheet disagrees with the reference mapping", row))
        if category is None or category.category_type == "heading" or (
            category.parent_category_id != (row.get("parent_category_id") or "") or
            category.category_path != row.get("education_category_path") or
            category.category_type != row.get("category_type") or
            str(category.hierarchy_level) != str(row.get("hierarchy_level")) or
            str(category.is_aggregate).lower() != str(row.get("is_aggregate")).lower()
        ):
            results.append(issue(5, "ERROR", "Invalid analytical category or classification attributes", row))
        if key_counts[tuple(row.get(k) for k in KEY)] > 1:
            results.append(issue(7, "ERROR", "Duplicate observation key", row))
        if source_counts[tuple(row.get(k) for k in SOURCE_KEY)] > 1:
            results.append(issue(19, "ERROR", "Duplicate output cell provenance", row))
        if status == "numeric" and (count is None or not str(count).isdigit() or int(count) > MAX_COUNT):
            results.append(issue(8, "ERROR", "Count must be an integer in the nonnegative bigint range", row))
        parsed, expected_status = parse_count(raw)
        if expected_status == "confidential" or status == "confidential":
            if expected_status != status or count is not None:
                results.append(issue(9, "ERROR", "Confidential marker must have a null population count", row))
        if expected_status == "dash_unresolved" or status == "dash_unresolved":
            if expected_status != status or count is not None:
                results.append(issue(10, "ERROR", "Unresolved dash must have a null population count", row))
        try:
            day = date.fromisoformat(row["reference_date"])
            compatible = (day.isoformat() == row["reference_date"] and 0 < int(row["source_row"]) <= 1048576
                          and DIMENSIONS.get(source) == tuple(row[k] for k in ("indicator_code", "breakdown_type", "breakdown_category"))
                          and (source not in {"G", "H"} or row["education_category_id"] == "territory_total")
                          and status in {"numeric", "blank", "dash_unresolved", "confidential"}
                          and status == expected_status and
                          (str(count) == str(parsed) if status == "numeric" else count is None)
                          and all("\x00" not in str(value) for value in row.values()))
        except (KeyError, TypeError, ValueError):
            compatible = False
        if not compatible:
            results.append(issue(20, "ERROR", "Observation violates the PostgreSQL import contract", row))
    return results

def validate_run(records, sheets, ledger, unmatched, settings, categories):
    results = validate_records(records, settings, categories)
    by_sheet = {sheet.name: sheet for sheet in sheets}
    coverage = set(by_sheet) == set(settings.territories)
    results.append(issue(1, "INFO" if coverage else "ERROR", "Territorial sheet coverage",
                         expected_value=len(settings.territories), observed_value=len(by_sheet),
                         source_sheet=", ".join(sorted(set(by_sheet) ^ set(settings.territories)))))
    for category in categories.values():
        parent = categories.get(category.parent_category_id)
        expected_path = f"{parent.category_path}/" if parent else ""
        if ((category.parent_category_id and parent is None) or
            category.hierarchy_level != (parent.hierarchy_level + 1 if parent else 0) or
            category.category_path != expected_path + category.education_category_id):
            results.append(issue(6, "ERROR", "Invalid parent, depth or path", {"education_category_id": category.education_category_id}))
    for sheet in sheets:
        territory = settings.territories.get(sheet.name, {})
        context = {"source_sheet": sheet.name, "territory_id": territory.get("territory_id", "")}
        structure = [*sheet.issues, *(f"Missing category: {c}" for c in sheet.inventory.get("missing_categories", []))]
        results.append(issue(2, "ERROR" if structure else "INFO",
                             "; ".join(structure) or "Recognised header and classification structure", context))
        metadata = sheet.inventory
        correct = (all(metadata.get(k) for k in ("reference_date", "source_note", "confidentiality_note")) and
                   "confidential" in metadata.get("confidentiality_note", "").casefold())
        results.append(issue(3, "INFO" if correct else "ERROR",
                             "Source date, attribution and confidentiality note present" if correct else "Source metadata missing or invalid", context))
        if not territory:
            results.append(issue(4, "ERROR", "Worksheet has no controlled territory identifier", context))
    dates = {sheet.inventory.get("reference_date") for sheet in sheets} - {"", None}
    if len(dates) != 1:
        results.append(issue(3, "ERROR", "Workbook must have one common reference date"))
    contexts = {sheet: territory["territory_id"] for sheet, territory in settings.territories.items()}
    for sheet, row, label in unmatched:
        results.append(issue(16, "ERROR", "Source label or hierarchy was not recognised",
                             {"source_sheet": sheet, "source_row": row, "territory_id": contexts.get(sheet, "")},
                             affected_columns="A", observed_value=label))
    for cell in ledger:
        context = {**cell, "territory_id": contexts.get(cell["source_sheet"], "")}
        if cell["value_status"] == "invalid" or cell["disposition"] == "rejected" and cell["source_column"] in {"G", "H"}:
            results.append(issue(17, "ERROR", "Unexpected source value or structure", context,
                                 affected_columns=cell["source_column"], observed_value=cell["raw_value"]))
        elif cell["disposition"] == "exported" and cell["value_status"] == "blank":
            results.append(issue(17, "WARNING", "Applicable source cell is blank", context,
                                 affected_columns=cell["source_column"]))
    expected = Counter(tuple(cell[k] for k in SOURCE_KEY) for cell in ledger if cell["disposition"] == "exported")
    actual = Counter(tuple(row[k] for k in SOURCE_KEY) for row in records)
    ledger_counts = Counter(tuple(cell[k] for k in SOURCE_KEY) for cell in ledger)
    if any(n > 1 for n in ledger_counts.values()):
        results.append(issue(19, "ERROR", "Duplicate cells in extraction ledger"))
    cells = sum(s.inventory["data_rows"] * 7 for s in sheets)
    reconciled = expected == actual and len(ledger) == cells
    results.append(issue(18, "INFO" if reconciled else "ERROR", "Source-cell ledger reconciled" if reconciled else "Cell reconciliation failed",
                         expected_value=cells, observed_value=len(ledger)))
    index = {(r["reference_date"], r["territory_id"], r["education_category_id"], r["source_column"]): r for r in records}
    groups = sorted({key[:3] for key in index})
    for group in groups:
        total = index.get((*group, "B"))
        scope = total or {"territory_id": group[1], "education_category_id": group[2]}
        for rule, members in ((11, "CD"), (12, "EF")):
            results.append(compare(rule, total, [index.get((*group, c)) for c in members], "B" + members, scope))
    children = defaultdict(list)
    for category in categories.values():
        children[category.parent_category_id].append(category.education_category_id)
    for (day, terr, category_id), column in product(groups, "BCDEF"):
        if category_id not in settings.exhaustive_parents:
            continue
        anchor = index.get((day, terr, category_id, column))
        results.append(compare(13, anchor, [index.get((day, terr, child, column)) for child in children[category_id]],
                               column, anchor or {"territory_id": terr, "education_category_id": category_id}))
    members = [r["territory_id"] for r in settings.territories.values() if r["parent_territory_id"] == "ro"]
    for (day, territory_id, category_id, column), total in sorted(index.items()):
        if territory_id == "ro":
            results.append(compare(14, total, [index.get((day, member, category_id, column)) for member in members], column, total))
    present = {r["rule_id"] for r in results}
    for number in range(1, 21):
        if f"DQ{number:03}" not in present:
            results.append(issue(number, "INFO", "Check completed without issues"))
    return results
