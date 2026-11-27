import pytest
from education_etl.classification import load_categories
from education_etl.config import load_settings
from education_etl.validation import compare, validate_run

def record(value, status="numeric"):
    return {"value_status": status, "population_count": value}

@pytest.mark.parametrize("rule", [11,12,13,14])
def test_aggregate_paths_and_confidentiality(rule):
    assert compare(rule, record(5), [record(2), record(3)], "B", {})["severity"] == "INFO"
    assert compare(rule, record(6), [record(2), record(3)], "B", {})["difference"] == 1
    report = compare(rule, record(6), [record(None, "confidential"), record(3)], "B", {})
    assert report["severity"] == "NOT_EVALUABLE"
    assert report["difference"] is None

def test_missing_territorial_coverage():
    config = load_settings()
    results = validate_run([], [], [], [], config, load_categories(config.classification_path))
    assert next(r for r in results if r["rule_id"] == "DQ001")["severity"] == "ERROR"
