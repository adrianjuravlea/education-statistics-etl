import os
from collections import Counter
from pathlib import Path

import pytest

from education_etl.classification import load_categories
from education_etl.cli import load_csv, run
from education_etl.config import ROOT, load_settings
from education_etl.database import load_postgres
from education_etl.transform import KEY
from education_etl.validation import validate_records

SOURCE = Path(os.environ.get("EDUCATION_TEST_WORKBOOK", ROOT.parent / "Tabel-3.01.xlsx"))

@pytest.mark.skipif(not SOURCE.exists(), reason="Supply the authorised census workbook")
def test_actual_workbook_and_compatible_csv(tmp_path):
    settings = load_settings()
    categories = load_categories(settings.classification_path)
    summary = run(SOURCE, tmp_path, settings, categories)
    assert summary["worksheets_processed"] == 43
    assert summary["source_confidential_values"] == 168
    assert summary["source_dash_values"] == 4235
    assert summary["output_observations"] == 10621 and summary["errors"] == 0
    path = tmp_path / "education_statistics_2021.csv"
    rows = load_csv(path)
    assert validate_records(rows, settings, categories) == []
    assert len({tuple(row[k] for k in KEY) for row in rows}) == len(rows)
    assert Counter(row["value_status"] for row in rows) == {"numeric": 10346, "confidential": 168, "dash_unresolved": 107}
    assert all(row["population_count"] is None for row in rows if row["value_status"] != "numeric")
    assert any(r["rule_id"] == "DQ007" for r in validate_records(rows[:1] * 2, settings, categories))
    assert {row["education_category_id"] for row in rows if row["source_column"] in "GH"} == {"territory_total"}
    load_postgres(path, rows, settings, categories, dry_run=True)
    with pytest.raises(ValueError, match="full census snapshot"):
        load_postgres(path, rows[:-1], settings, categories, dry_run=True)
    repeat = tmp_path / "repeat"
    run(SOURCE, repeat, settings, categories)
    assert path.read_bytes() == (repeat / path.name).read_bytes()
