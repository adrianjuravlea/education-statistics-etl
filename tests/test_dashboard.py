from types import SimpleNamespace

from education_etl.dashboard import MEASURES, pivot

def fixture():
    category_ids = ["territory_total", "education"]
    settings = SimpleNamespace(territories={"Test": {"territory_id": "ro"}})
    categories = {key: SimpleNamespace(education_category_id=key, category_type="level") for key in category_ids}
    from education_etl.dashboard import METADATA
    records = []
    for category, columns in zip(category_ids, ("BCDEFGH", "BCDEF"), strict=True):
        for col in columns:
            value, status = {"B": (8,"numeric"), "C": (None,"confidential"), "D": (None,"dash_unresolved"),
                             "E": (0,"numeric"), "F": (8,"numeric"), "G": (2,"numeric"), "H": (1,"numeric")}[col]
            records.append(dict.fromkeys(METADATA, "") | dict(reference_date="2021-12-01", territory_id="ro",
                           education_category_id=category, source_column=col, population_count=value, value_status=status))
    return records, settings, categories

def test_pivot_preserves_disjoint_margins_and_statuses():
    records, settings, categories = fixture()
    rows, issues = pivot(records, settings, categories)
    education, territorial = rows
    assert len(MEASURES) == 7 and issues[0]["severity"] == "INFO"
    assert territorial["resident_population_total"] == 11 and territorial["resident_population_total_method"] == "calculated"
    assert education["male"] is None and education["male_status"] == "confidential"
    assert education["female"] is None and education["female_status"] == "dash_unresolved"
    assert education["urban"] == 0 and education["urban_status"] == "numeric"
    assert education["under_2_years"] is None and education["under_2_years_status"] == "not_applicable"
    assert education["no_completed_education_status"] == "not_applicable"
    assert education["resident_population_total"] is None

def test_pivot_checks_coverage_duplicates_and_suppression():
    records, settings, categories = fixture()
    records[5].update(population_count=None, value_status="confidential")
    rows, issues = pivot(records, settings, categories)
    assert rows[-1]["resident_population_total"] is None
    assert rows[-1]["resident_population_total_status"] == "not_evaluable"
    for modified in (records[:7], records + records[:1], records[:-1]):
        assert any(x["severity"] == "ERROR" for x in pivot(modified, settings, categories)[1])
