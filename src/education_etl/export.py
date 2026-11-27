"""Write deterministic spreadsheet-compatible reports and PostgreSQL CSV files."""
import csv
import html
import json
from collections import Counter
from dataclasses import fields
from pathlib import Path

from .validation import Result

def write_csv(path: Path, rows: list[dict], columns: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, columns, lineterminator="\r\n", quoting=csv.QUOTE_ALL)
        writer.writeheader()
        for row in rows:
            # PostgreSQL COPY uses an explicit null token and FORCE_NULL on nullable columns.
            writer.writerow({key: encode(row.get(key)) for key in columns})

def encode(value):
    if value is None:
        return r"\N"
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, ensure_ascii=False, default=str)
    return value

def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")

def summarise(results):
    def breakdown(key):
        groups = {}
        for row in results:
            groups.setdefault(row[key] or "workbook", Counter())[row["severity"]] += 1
        return groups
    return {"severity": Counter(r["severity"] for r in results), "rule": breakdown("rule_id"),
            "territory": breakdown("territory_id")}

def write_quality(output: Path, results: list[dict], run: dict) -> None:
    columns = [f.name for f in fields(Result)]
    write_csv(output / "data_quality_report.csv", results, columns)
    summary = summarise(results)
    write_json(output / "data_quality_summary.json", summary)
    def table(columns, values):
        cell = lambda value: html.escape(str(value if value is not None else ""))
        headings = "".join(f"<th>{cell(c.replace('_', ' ').title())}</th>" for c in columns)
        body = "".join("<tr>" + "".join(f"<td>{cell(v)}</td>" for v in row) + "</tr>" for row in values)
        return f"<table><thead><tr>{headings}</tr></thead><tbody>{body}</tbody></table>"
    details = [r for r in results if r["severity"] != "INFO"]
    severities = ["ERROR", "WARNING", "NOT_EVALUABLE", "INFO"]
    panels = "".join(
        f"<h2>Results by {key}</h2>" + table([key, *severities],
        ([label, *(counts.get(s, 0) for s in severities)] for label, counts in summary[key].items()))
        for key in ("rule", "territory")
    )
    page = """<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width">
    <title>Education statistics data quality report</title><style>
    body{margin:3rem auto;padding:0 1.3rem;max-width:1240px;background:#f4f7fa;color:#193146;font:15px system-ui}
    h1,h2{color:#133e54} table{border-collapse:collapse;width:100%;background:white} td,th{padding:.5rem;text-align:left;
    border-bottom:1px solid #dce4eb} th{background:#12465d;color:white} .scroll{overflow:auto} caption{text-align:left}
    </style><h1>Education statistics data quality report</h1><p>Romanian Population and Housing Census 2021, Table 3.1.</p>
    <p>Warnings flag published comparisons or source completeness for review. Errors also cover extraction,
    mapping and import contract failures. Unavailable components prevent numerical reconciliation.</p>"""
    page += table(["metric", "value"], run.items()) + panels
    page += "<h2>Non-passing checks</h2><div class='scroll'>" + table(columns, ([r[c] for c in columns] for r in details)) + "</div></html>"
    (output / "data_quality_report.html").write_text(page, encoding="utf-8")
