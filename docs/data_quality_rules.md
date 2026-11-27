# Data quality rules

Each result contains the rule ID and name, severity, territory, category, source coordinates, affected columns, observed and expected values, difference and a message. Where present, difference is published total minus sum of reported components. INFO includes completed checks. NOT_EVALUABLE identifies unavailable comparisons. WARNING identifies source completeness or a published numerical comparison that merits review. ERROR identifies a blocking workbook, extraction, classification, key or import-contract problem.

| Rules | Contract |
|---|---|
| DQ001–DQ003 | Expected tab coverage, recognisable workbook structure and source metadata |
| DQ004–DQ006 | Controlled territory and classification IDs, parent and category path consistency |
| DQ007–DQ010 | Stable unique keys, nonnegative integer counts, null suppressed and dash counts |
| DQ011–DQ012 | Completed education total equals each complete sex and residence margin |
| DQ013 | Parent total compared to direct children only on listed exhaustive education branches |
| DQ014 | National total compared with all 41 counties and Bucharest for the same published series |
| DQ015–DQ017 | Required dimensions, recognised labels, and valid source value types |
| DQ018–DQ020 | Source ledger reconciliation, unique cell provenance and PostgreSQL import compatibility |
| DQ021 | Dashboard key coverage and long-to-wide reconciliation of applicable counts and statuses |

Checks using unavailable data omit both numerical results and differences. The actual workbook produced 5,710 INFO and 357 NOT_EVALUABLE outcomes, with zero errors and warnings. No source totals were corrected.
