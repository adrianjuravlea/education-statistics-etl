"""Optional PostgreSQL loader with transactional snapshot replacement."""
import csv
import hashlib
import json
import logging
import os
import uuid
from dataclasses import astuple
from pathlib import Path

from .config import ROOT
from .transform import DIMENSIONS, FIELDS

def load_postgres(path: Path, records: list[dict], settings, categories, *, dry_run: bool = False) -> None:
    territories = [territory["territory_id"] for territory in settings.territories.values()]
    expected = {
        (territory_id, category.education_category_id, column)
        for territory_id in territories
        for category in categories.values()
        if category.category_type != "heading"
        for column in DIMENSIONS
        if column not in {"G", "H"} or category.category_type == "territorial_total"
    }
    actual = {(row["territory_id"], row["education_category_id"], row["source_column"]) for row in records}
    dates = {row["reference_date"] for row in records}
    if len(dates) != 1 or actual != expected or len(records) != len(expected):
        raise ValueError("Database loading requires one full census snapshot with all expected observation keys")
    if dry_run:
        logging.info("Dry run complete. CSV validated, database untouched.")
        return
    dsn = os.environ.get("EDUCATION_DATABASE_URL")
    if not dsn:
        raise ValueError("Set EDUCATION_DATABASE_URL to an authorised demonstration database")
    import psycopg
    from psycopg import sql

    data = path.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    run_id = uuid.uuid4()
    quality_path = path.with_name("data_quality_report.csv")
    summary_path = path.with_name("etl_run_summary.json")
    quality = []
    if quality_path.exists() and summary_path.exists():
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        if summary.get("consolidated_csv_sha256") == digest:
            if summary["errors"]:
                raise ValueError("The matching ETL run has blocking quality errors")
            with quality_path.open(encoding="utf-8", newline="") as stream:
                quality = [{k: None if v in ("", r"\N") else v for k, v in row.items()}
                           for row in csv.DictReader(stream)]
    with psycopg.connect(dsn) as connection, connection.cursor() as cur:
        cur.execute("SELECT pg_advisory_xact_lock(hashtext('education-statistics-etl'))")
        for script in sorted((ROOT / "sql").glob("0[1-2]*.sql")):
            cur.execute(script.read_text(encoding="utf-8"))
        cur.execute((ROOT / "sql" / "03_load_staging.sql").read_text(encoding="utf-8"))
        cur.executemany(
            "INSERT INTO reference.territory VALUES (%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING",
            [tuple(value or None for value in row.values()) for row in settings.territories.values()])
        cur.executemany(
            "INSERT INTO reference.education_classification VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING",
            [(values[0], values[1] or None, *values[2:]) for values in map(astuple, categories.values())])
        columns = sql.SQL(", ").join(map(sql.Identifier, FIELDS))
        command = sql.SQL("COPY staging.education_statistics_raw ({}) FROM STDIN "
                          "WITH (FORMAT csv, HEADER true, ENCODING 'UTF8', NULL '\\N', "
                          "FORCE_NULL (parent_category_id,population_count,raw_value))").format(columns)
        with cur.copy(command) as copy:
            copy.write(data)
        cur.execute((ROOT / "sql" / "04_validate_data.sql").read_text(encoding="utf-8"))
        cur.execute("INSERT INTO qa.etl_run (run_id,source_file,csv_sha256,observation_count) VALUES (%s,%s,%s,%s) "
                    "ON CONFLICT (csv_sha256) DO UPDATE SET csv_sha256 = excluded.csv_sha256 RETURNING run_id",
                    (run_id, records[0]["source_file"], digest, len(records)))
        run_id = cur.fetchone()[0]
        script = (ROOT / "sql" / "05_load_final_tables.sql").read_text(encoding="utf-8")
        cur.execute(sql.SQL(script.replace(":'run_id'", "{}")).format(sql.Literal(run_id)))
        if quality:
            cur.execute("DELETE FROM qa.validation_results WHERE run_id = %s", (run_id,))
            keys = list(quality[0])
            insert = sql.SQL("INSERT INTO qa.validation_results (run_id,{}) VALUES ({})").format(
                sql.SQL(",").join(map(sql.Identifier, keys)), sql.SQL(",").join([sql.Placeholder()] * (len(keys)+1)))
            cur.executemany(insert, [(run_id, *(row[k] for k in keys)) for row in quality])
        cur.execute((ROOT / "sql" / "06_analytical_views.sql").read_text(encoding="utf-8"))
        cur.execute((ROOT / "sql" / "07_dashboard_view.sql").read_text(encoding="utf-8"))
    logging.info("Loaded census snapshot %s", run_id)
