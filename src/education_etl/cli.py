"""Run and validate the census ETL from PowerShell or a POSIX shell."""
import argparse
import csv
import hashlib
import logging
import time
import uuid
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from .classification import load_categories
from .config import ROOT, load_settings
from .dashboard import FIELDS as DASHBOARD_FIELDS, pivot
from .extract import inspect_workbook
from .export import write_csv, write_json, write_quality
from .logging_config import configure
from .transform import FIELDS, transform
from .validation import read_records, validate_records, validate_run

def load_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream, strict=True)
        if reader.fieldnames != FIELDS:
            raise ValueError("CSV header does not match the import contract")
        output = []
        for index, row in enumerate(reader, 2):
            if None in row or None in row.values():
                raise ValueError(f"CSV row {index} has an unexpected number of columns")
            output.append({key: None if value == r"\N" else value for key, value in row.items()})
        return output

def run(path: Path, output: Path, settings, categories, inspect_only: bool = False) -> dict:
    started = time.monotonic()
    stamp = datetime.now(timezone.utc).isoformat()
    sheets = inspect_workbook(path)
    frame, ledger, unmatched = transform(path, sheets, settings, categories)
    records = read_records(frame)
    output.mkdir(parents=True, exist_ok=True)
    inventories = [sheet.inventory for sheet in sheets]
    inventory_fields = list(dict.fromkeys(key for row in inventories for key in row))
    write_csv(output / "worksheet_inventory.csv", inventories, inventory_fields)
    if inspect_only:
        return {"worksheets_discovered": len(sheets), "worksheets_rejected": sum(bool(s.issues) for s in sheets),
                "source_data_rows": sum(s.inventory["data_rows"] for s in sheets),
                "source_confidential_values": sum(s.inventory["confidential_values"] for s in sheets),
                "source_dash_values": sum(s.inventory["dash_values"] for s in sheets)}
    results = validate_run(records, sheets, ledger, unmatched, settings, categories)
    dashboard, dashboard_results = pivot(records, settings, categories)
    results.extend(dashboard_results)
    dispositions = Counter(c["disposition"] for c in ledger)
    statuses = Counter(r["value_status"] for r in records)
    errors = sum(r["severity"] == "ERROR" for r in results)
    warnings = sum(r["severity"] == "WARNING" for r in results)
    rejected = sum(bool(s.issues) or s.name not in settings.territories for s in sheets)
    summary = {"run_id": str(uuid.uuid4()), "execution_utc": stamp, "source_file": path.name,
               "source_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
               "source_information": next((s.inventory["source_note"] for s in sheets if s.inventory.get("source_note")), ""),
               "worksheets_discovered": len(sheets), "worksheets_processed": len(sheets) - rejected,
               "worksheets_rejected": rejected, "source_data_rows": sum(s.inventory["data_rows"] for s in sheets),
               "source_confidential_values": sum(s.inventory["confidential_values"] for s in sheets),
               "source_dash_values": sum(s.inventory["dash_values"] for s in sheets),
               "output_observations": len(records), "numeric_observations": statuses["numeric"],
               "confidential_observations": statuses["confidential"], "dash_observations": statuses["dash_unresolved"],
               "blank_observations": statuses["blank"], "structural_cells": dispositions["structural"],
               "rejected_cells": dispositions["rejected"], "errors": errors, "warnings": warnings,
               "status": "ERROR" if errors else "WARNING" if warnings else "OK",
               "duration_seconds": round(time.monotonic() - started, 3)}
    consolidated = output / "education_statistics_2021.csv"
    write_csv(consolidated, records, FIELDS)
    summary["consolidated_csv_sha256"] = hashlib.sha256(consolidated.read_bytes()).hexdigest()
    dashboard_path = output / "education_statistics_dashboard_2021.csv"
    write_csv(dashboard_path, dashboard, DASHBOARD_FIELDS)
    summary["dashboard_records"] = len(dashboard)
    summary["dashboard_csv_sha256"] = hashlib.sha256(dashboard_path.read_bytes()).hexdigest()
    cell_fields = ["source_file", "source_sheet", "source_row", "source_column", "source_label", "raw_value", "cell_type", "value_status", "disposition"]
    write_csv(output / "source_cell_inventory.csv", ledger, cell_fields)
    write_csv(output / "rejected_records.csv", [row for row in ledger if row["disposition"] == "rejected"], cell_fields)
    write_json(output / "etl_run_summary.json", summary)
    write_quality(output, results, summary)
    return summary

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("inspect", "run", "validate", "load-postgres"):
        command = commands.add_parser(name)
        command.add_argument("--input", type=Path, required=True)
        command.add_argument("--config", type=Path, default=ROOT / "config" / "etl_config.json")
        command.add_argument("--log-level", choices=["DEBUG", "INFO", "WARNING", "ERROR"], default="INFO")
        command.add_argument("--strict", action="store_true")
        if name in {"inspect", "run"}:
            command.add_argument("--output-dir", type=Path, default=ROOT / "output")
        if name == "load-postgres":
            command.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    configure(args.log_level, ROOT / "logs" / "etl.log" if args.command == "run" else None)
    try:
        settings = load_settings(args.config)
        categories = load_categories(settings.classification_path)
        if args.command in {"inspect", "run"}:
            summary = run(args.input, args.output_dir, settings, categories, args.command == "inspect")
            logging.info("%s", summary)
            if summary.get("errors") or summary.get("worksheets_rejected"):
                return 2
            return 2 if args.strict and summary.get("warnings") else 0
        records = load_csv(args.input)
        results = validate_records(records, settings, categories)
        for result in results:
            logging.error("%s", result)
        if results:
            return 2
        if args.command == "load-postgres":
            from .database import load_postgres
            load_postgres(args.input, records, settings, categories, dry_run=args.dry_run)
        logging.info("Validated %d observations", len(records))
        return 0
    except Exception as error:
        logging.error("%s: %s", type(error).__name__, error)
        logging.debug("Traceback", exc_info=True)
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
