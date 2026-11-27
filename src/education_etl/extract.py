"""Inventory source worksheets using the printed column identifiers and notes."""
import re
import unicodedata
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from openpyxl import load_workbook
from openpyxl.utils import get_column_letter

DASHES = {"-", "–", "—", "−"}
MONTHS = "ianuarie februarie martie aprilie mai iunie iulie august septembrie octombrie noiembrie decembrie".split()

def normalise(value: object) -> str:
    return " ".join(unicodedata.normalize("NFC", str(value)).split()) if value is not None else ""

@dataclass(frozen=True)
class SourceRow:
    number: int
    label: str
    indent: int
    values: tuple
    types: tuple[str, ...]
    kind: str

@dataclass
class Sheet:
    name: str
    inventory: dict
    rows: list[SourceRow]
    issues: list[str]

def inspect_workbook(path: Path) -> list[Sheet]:
    workbook = load_workbook(path, data_only=False)
    try:
        return [inspect_sheet(ws) for ws in workbook]
    finally:
        workbook.close()

def inspect_sheet(ws) -> Sheet:
    matrix = list(ws.iter_rows())
    populated = [(i, row) for i, row in enumerate(matrix, 1) if any(c.value is not None for c in row)]
    columns = sorted({c.column for _, row in populated for c in row if c.value is not None})
    marker = [i for i, row in populated if [normalise(c.value) for c in row[:8]] == list("A1234567")]
    notes = [(i, normalise(row[0].value)) for i, row in populated
             if normalise(row[0].value).casefold().startswith(("sursa:", "*"))]
    rows: list[SourceRow] = []
    issues: list[str] = []
    metadata = {}
    if len(marker) != 1:
        issues.append("Expected a unique A/1–7 column-identifier row")
    else:
        anchor = marker[0]
        header = [tuple(c.value for c in row[:8]) for i, row in populated if i < anchor]
        title = next((normalise(v) for row in header for v in row
                      if "POPULATIA REZIDENTA DUPA" in normalise(v)), "")
        match = re.search(r"\b(\d{1,2}) (" + "|".join(MONTHS) + r") (\d{4})\b", title.casefold())
        reference_date = ""
        if match:
            day, month, year = match.groups()
            try:
                reference_date = date(int(year), MONTHS.index(month) + 1, int(day)).isoformat()
            except ValueError:
                pass
        metadata = {"title": title, "reference_date": reference_date,
                    "source_note": next((v for _, v in notes if v.casefold().startswith("sursa:")), ""),
                    "confidentiality_note": next((v for _, v in notes if v.startswith("*")), ""),
                    "header_rows": header}
        header_expected = ("NIVELUL DE EDUCATIE", "POPULATIA REZIDENTA DE 2 ANI SI PESTE CARE A ABSOLVIT",
                           "Masculin", "Feminin", "Urban", "Rural",
                           "POPULATIA REZIDENTA DE 2 ANI SI PESTE CARE NU A ABSOLVIT", "NU ESTE CAZUL")
        for index, expected in enumerate(header_expected):
            if not any(normalise(row[index]).startswith(expected) for row in header):
                issues.append(f"Missing expected header in column {get_column_letter(index + 1)}")
        if columns != list(range(1, 9)):
            issues.append("Expected populated columns A:H")
        end = next((i for i, _ in notes if i > anchor), ws.max_row + 1)
        for i, row in populated:
            if not anchor < i < end:
                continue
            label = row[0].value
            values = tuple(c.value for c in row[1:8])
            if not isinstance(label, str) or not normalise(label):
                issues.append(f"Data area row {i} has no valid label")
                label = str(label or "")
            indent = len(label) - len(label.lstrip())
            kind = "heading" if normalise(label) == "I. INVATAMANT UNIVERSITAR" and all(v is None for v in values) else "data"
            rows.append(SourceRow(i, label, indent, values, tuple(c.data_type for c in row[1:8]), kind))
        if sum(normalise(row.label) == ws.title for row in rows) != 1:
            issues.append("Missing or duplicate territorial total row")
        if any(i >= end and i not in {n for n, _ in notes} for i, _ in populated):
            issues.append("Unexpected populated row after source notes")
    data = [row for row in rows if row.kind == "data"]
    inventory = {"worksheet": ws.title, "dimensions": ws.dimensions, "declared_rows": ws.max_row,
                 "declared_columns": ws.max_column, "populated_rows": [i for i, _ in populated],
                 "populated_columns": [get_column_letter(c) for c in columns],
                 "merged_ranges": sorted(str(m) for m in ws.merged_cells.ranges),
                 "data_rows": len(data), "classification_headings": len(rows) - len(data),
                 "blank_rows": ws.max_row - len(populated),
                 "confidential_values": sum(normalise(v) == "*" for r in data for v in r.values),
                 "dash_values": sum(normalise(v) in DASHES for r in data for v in r.values),
                 "unexpected_values": [], "structure_issues": issues, "status": "rejected" if issues else "processed",
                 **metadata}
    return Sheet(ws.title, inventory, rows, issues)
