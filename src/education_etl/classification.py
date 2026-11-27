"""Resolve education categories using the source label, indentation and active branch."""
import csv
from dataclasses import dataclass
from pathlib import Path

from .extract import SourceRow, normalise

@dataclass(frozen=True)
class Category:
    education_category_id: str
    parent_category_id: str
    education_category_name_original: str
    education_category_name_en: str
    hierarchy_level: int
    category_path: str
    category_type: str
    display_order: int
    is_aggregate: bool
    source_indent: int

def load_categories(path: Path) -> dict[str, Category]:
    with path.open(encoding="utf-8", newline="") as stream:
        result = {}
        for row in csv.DictReader(stream):
            for name in ("hierarchy_level", "display_order", "source_indent"):
                row[name] = int(row[name])
            row["is_aggregate"] = row["is_aggregate"] == "true"
            category = Category(**row)
            if category.education_category_id in result:
                raise ValueError(f"Duplicate category {category.education_category_id}")
            result[category.education_category_id] = category
    return result

def classify(rows: list[SourceRow], sheet: str, categories: dict[str, Category]):
    stack: list[Category] = []
    by_label: dict[str, list[Category]] = {}
    for category in categories.values():
        by_label.setdefault(normalise(category.education_category_name_original), []).append(category)
    for row in rows:
        label = normalise(row.label)
        if label == sheet:
            yield row, categories.get("territory_total")
            continue
        candidates = by_label.get(label, [])
        candidate = next((item for item in candidates if item.source_indent == row.indent
                          and (not item.parent_category_id or
                               any(parent.education_category_id == item.parent_category_id for parent in stack))), None)
        if candidate:
            stack = stack[:candidate.hierarchy_level]
            stack.append(candidate)
        else:
            while stack and stack[-1].source_indent >= row.indent:
                stack.pop()
        yield row, candidate
