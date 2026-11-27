from openpyxl import Workbook
from education_etl.extract import inspect_sheet, normalise

def test_merged_multilevel_header_and_shifted_rows():
    ws = Workbook().active
    ws.title = "ROMANIA"
    ws["B2"] = "POPULATIA REZIDENTA DUPA NIVELUL DE EDUCATIE, LA 1 DECEMBRIE 2021"
    ws.merge_cells("B2:R2")
    ws.append(["NIVELUL DE EDUCATIE", "POPULATIA REZIDENTA DE 2 ANI SI PESTE CARE A ABSOLVIT",
               "DIN CARE:", None, None, None, "POPULATIA REZIDENTA DE 2 ANI SI PESTE CARE NU A ABSOLVIT", "NU ESTE CAZUL"])
    ws.merge_cells("C3:F3")
    ws.append([None, None, "SEXE", None, "MEDIU DE REZIDENTA"])
    ws.append([None, None, "Masculin", "Feminin", "Urban", "Rural"])
    ws.append(list("A1234567"))
    ws["A10"] = "ROMANIA"
    ws["B10"] = 0
    ws["C10"] = "*"
    ws["F10"] = "-"
    ws["A14"] = "Sursa: INS"
    ws["A15"] = "* - valoare confidentiala"
    sheet = inspect_sheet(ws)
    assert not sheet.issues
    assert sheet.inventory["reference_date"] == "2021-12-01"
    assert sheet.inventory["confidential_values"] == sheet.inventory["dash_values"] == 1
    assert sheet.inventory["blank_rows"] > 0
    assert sheet.inventory["merged_ranges"] == ["B2:R2", "C3:F3"]
    assert sheet.rows[0].number == 10

def test_unexpected_structure_and_unicode():
    ws = Workbook().active
    assert inspect_sheet(ws).inventory["status"] == "rejected"
    assert normalise("  A\u0306  \u00a0 școală\n  primară") == "Ă școală primară"
