from education_etl.classification import classify, load_categories
from education_etl.config import load_settings
from education_etl.extract import SourceRow

def test_repeated_field_branch_identity():
    categories = load_categories(load_settings().classification_path)
    keys = ["university","doctorate","doctorate_field_1","masters","masters_field_1","secondary",
            "upper_secondary","high_school","high_school_theology","vocational","lower_secondary"]
    rows = [SourceRow(i, categories[k].education_category_name_original, categories[k].source_indent, (), (),
                      categories[k].category_type) for i,k in enumerate(keys, 1)]
    assert [c.education_category_id for _, c in classify(rows, "ALBA", categories)] == keys
    assert categories["masters_field_1"].education_category_name_original == categories["doctorate_field_1"].education_category_name_original
    assert categories["high_school_theology"].category_path == "secondary/upper_secondary/high_school/high_school_theology"
