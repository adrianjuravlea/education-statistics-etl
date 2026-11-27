import pytest
from education_etl.transform import parse_count

@pytest.mark.parametrize(("raw","cell_type","expected"), [
    ("*", "s", (None, "confidential")), ("−", "s", (None, "dash_unresolved")),
    (None, "n", (None, "blank")), (0, "n", (0, "numeric")),
    (" 42.0 ", "s", (42, "numeric")), (-1, "n", (None, "invalid")),
    (1.5, "n", (None, "invalid")), ("words", "s", (None, "invalid")),
    ("#N/A", "e", (None, "invalid")), ("=1+2", "f", (None, "invalid")),
    (True, "b", (None, "invalid")), ("9223372036854775808", "s", (None, "invalid")),
])
def test_values(raw, cell_type, expected):
    assert parse_count(raw, cell_type) == expected
