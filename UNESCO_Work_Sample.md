# Work sample for UNESCO vacancy 24494

## Education statistics ETL and quality assessment

This demonstration processes Table 3.1 of Romania’s final 2021 Population and Housing Census. The source reports resident population counts by completed education, sex and residence area at 1 December 2021 across the national total, 41 counties and Bucharest Municipality.

The Python CLI uses openpyxl to identify multisheet headers, source notes, statistical cells and classification headings, and pandas to represent nullable counts. A controlled mapping preserves the Romanian category hierarchy and repeated fields under different university levels. The pipeline extracts separate sex and residence marginal distributions, preserves confidential and unresolved cells as distinct statuses, and retains complete statistical-cell provenance.

The 21-rule quality framework verifies worksheet coverage, structure, classification integrity, both source-to-output and dashboard reconciliation, identifiers and SQL compatibility. It compares complete sex and residence margins, configured non-overlapping education branches, and national versus subnational values. Unavailable values prevent comparison. The project includes optional PostgreSQL views and a transactional snapshot loader.

The actual run processed all 43 worksheets and generated 10,621 observations and 2,107 dashboard records. The outputs preserve 168 confidential counts with null values and 107 unresolved dashes. The source ledger retains another 4,128 structural dashes. Of 6,067 QA outcomes, 5,710 completed with INFO and 357 were not evaluable. No error or warning was reported. All 23 pytest cases passed, including real-workbook integration, repeatability and CSV compatibility. PostgreSQL dry-run passed. Live loading remains unverified.

The files demonstrate the skills relevant to UIS vacancy 24494 in parsing complex census tables, maintaining education classifications, representing confidentiality, reproducibly validating data, and preparing results for downstream analysis. The supplied census workbook is attributed to Romania’s National Institute of Statistics. This ETL is a newly developed work sample. The translated classification is source-specific and does not assert an ISCED correspondence.

Publication is pending manual upload. [Target GitHub repository](https://github.com/adrianjuravlea/education-statistics-etl)
