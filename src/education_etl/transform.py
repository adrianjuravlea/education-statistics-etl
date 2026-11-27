"""Transform source cells into marginal observations and retain a complete cell ledger."""
from decimal import Decimal, InvalidOperation
import re
from pathlib import Path

import pandas as pd

from .classification import Category, classify
from .config import Settings
from .extract import DASHES, Sheet, normalise

DIMENSIONS = {
    "B": ("completed_education", "overall", "total"),
    "C": ("completed_education", "sex", "male"),
    "D": ("completed_education", "sex", "female"),
    "E": ("completed_education", "residence", "urban"),
    "F": ("completed_education", "residence", "rural"),
    "G": ("no_completed_education", "overall", "total"),
    "H": ("under_age_two", "overall", "total"),
}
FIELDS = """reference_date territory_id territory_name territory_level education_category_id parent_category_id
education_category_name_original education_category_name_en education_category_path category_type hierarchy_level
is_aggregate indicator_code breakdown_type breakdown_category population_count value_status raw_value source_file
source_sheet source_row source_column""".split()
KEY = ["reference_date", "territory_id", "education_category_id", "indicator_code", "breakdown_type", "breakdown_category"]
SOURCE_KEY = ["source_file", "source_sheet", "source_row", "source_column"]
MAX_COUNT = 2**63 - 1

def parse_count(value: object, cell_type: str = "") -> tuple[int | None, str]:
    cleaned = normalise(value)
    if cell_type in {"e", "f"} or isinstance(value, bool):
        return None, "invalid"
    if not cleaned:
        return None, "blank"
    if cleaned == "*":
        return None, "confidential"
    if cleaned in DASHES:
        return None, "dash_unresolved"
    if not re.fullmatch(r"[+-]?[0-9]+(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?", cleaned):
        return None, "invalid"
    try:
        number = Decimal(cleaned)
        if 0 <= number <= MAX_COUNT and number == number.to_integral_value():
            return int(number), "numeric"
    except InvalidOperation:
        pass
    return None, "invalid"

def transform(path: Path, sheets: list[Sheet], settings: Settings, categories: dict[str, Category]):
    records, ledger = [], []
    unmatched = []
    for sheet in sheets:
        territory = settings.territories.get(sheet.name)
        seen = set()
        for row, category in classify(sheet.rows, sheet.name, categories):
            if category is None or (row.kind == "heading") != (category.category_type == "heading"):
                unmatched.append((sheet.name, row.number, row.label))
                category = None
            if category:
                seen.add(category.education_category_id)
            if row.kind == "heading":
                continue
            for column, value, cell_type in zip(DIMENSIONS, row.values, row.types, strict=True):
                count, status = parse_count(value, cell_type)
                structural = column in "GH" and normalise(row.label) != sheet.name
                use = not sheet.issues and territory is not None and category is not None and not structural and status != "invalid"
                raw = str(value) if value is not None else None
                provenance = dict(zip(SOURCE_KEY, (path.name, sheet.name, row.number, column), strict=True))
                ledger.append({**provenance, "source_label": row.label, "raw_value": raw, "cell_type": cell_type,
                               "value_status": status, "disposition": "exported" if use else
                               "structural" if structural and status in {"blank", "dash_unresolved"} else "rejected"})
                if status == "invalid" or structural and status not in {"blank", "dash_unresolved"}:
                    sheet.inventory["unexpected_values"].append(f"{column}{row.number}: {raw!r}")
                if not use:
                    continue
                indicator, breakdown, member = DIMENSIONS[column]
                records.append(dict(zip(FIELDS, (
                    sheet.inventory.get("reference_date"), territory["territory_id"], territory["territory_name_normalised"],
                    territory["territory_level"], category.education_category_id, category.parent_category_id or None,
                    row.label, category.education_category_name_en, category.category_path, category.category_type,
                    category.hierarchy_level, category.is_aggregate, indicator, breakdown, member, count, status, raw,
                    *provenance.values()), strict=True)))
        sheet.inventory["missing_categories"] = sorted(categories.keys() - seen)
    frame = pd.DataFrame(records, columns=FIELDS)
    frame["population_count"] = pd.array([r["population_count"] for r in records], dtype="Int64")
    return frame, ledger, unmatched
