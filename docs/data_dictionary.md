# Consolidated data dictionary

CSV output has a fixed 22-column schema, UTF-8, CRLF and standard quoting. The quoted token `\N` carries SQL NULL in the three nullable fields. Load them with `FORCE_NULL` in PostgreSQL CSV mode. The literal dash and asterisk are kept in raw_value.

| Fields | Meaning and type |
|---|---|
| reference_date | ISO date, required |
| territory_id, territory_name, territory_level | Internal territory key, display name, national/county/municipality |
| education_category_id, parent_category_id | Classification key and nullable immediate parent key |
| education_category_name_original, education_category_name_en | Exact source row label and descriptive English member |
| education_category_path, category_type, hierarchy_level, is_aggregate | Stable path, analytical classification type, integer depth, Boolean aggregate flag |
| indicator_code, breakdown_type, breakdown_category | Statistical indicator and one overall/sex/residence margin |
| population_count | Nullable nonnegative bigint |
| value_status | numeric, confidential, dash_unresolved or blank |
| raw_value | Nullable original source cell rendered as text |
| source_file, source_sheet, source_row, source_column | Workbook basename, exact tab label, one-based row number and Excel column letter |

The statistical key combines date, territory, category, indicator, breakdown type and breakdown member. The source key combines file, worksheet, row and column. The separate source ledger adds source_label, cell_type, value_status and disposition for each statistical cell. Dimension configuration includes reference identifiers, parent keys and English translations.

## Dashboard CSV

The 31-column dashboard schema uses `reference_date, territory_id, education_category_id` as its unique key. Twelve leading columns carry date, territory and hierarchy metadata. Bigint columns `total, male, female, urban, rural, no_completed_education, under_2_years` each have a paired text status. The calculated `resident_population_total` uses PostgreSQL numeric, with a status and method. The final columns are source_file and source_sheet. Nulls use quoted `\N` with PostgreSQL CSV FORCE_NULL on nullable fields.

The seven input cells retain their existing numeric, blank, confidential or dash_unresolved statuses. G and H outside territorial totals use not_applicable. Missing applicable observations use missing_observation and fail DQ021. The Table 3.01 B, G and H measures partition the population by age and completed education. If all three are numeric, the territorial resident total is B + G + H, with method calculated. The workbook has no separate reported resident-total column. Unavailable components yield not_evaluable and a null total. Education rows use not_applicable and a null total. Filter one territorial and one classification level before aggregating. Sex and residence are separate marginal distributions.
