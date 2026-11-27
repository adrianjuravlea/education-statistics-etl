CREATE OR REPLACE VIEW education.dashboard_2021 AS
WITH pivoted AS (
SELECT reference_date, territory_id, territory_name, territory_level, education_category_id, parent_category_id, education_category_name_original, education_category_name_en, education_category_path, hierarchy_level, category_type, is_aggregate, source_file, source_sheet,
    max(population_count) FILTER (WHERE source_column = 'B') AS total,
    max(population_count) FILTER (WHERE source_column = 'C') AS male,
    max(population_count) FILTER (WHERE source_column = 'D') AS female,
    max(population_count) FILTER (WHERE source_column = 'E') AS urban,
    max(population_count) FILTER (WHERE source_column = 'F') AS rural,
    max(population_count) FILTER (WHERE source_column = 'G') AS no_completed_education,
    max(population_count) FILTER (WHERE source_column = 'H') AS under_2_years,
    coalesce(max(value_status) FILTER (WHERE source_column = 'B'),
        CASE WHEN education_category_id <> 'territory_total' AND 'B' IN ('G','H')
             THEN 'not_applicable' ELSE 'missing_observation' END) AS total_status,
    coalesce(max(value_status) FILTER (WHERE source_column = 'C'),
        CASE WHEN education_category_id <> 'territory_total' AND 'C' IN ('G','H')
             THEN 'not_applicable' ELSE 'missing_observation' END) AS male_status,
    coalesce(max(value_status) FILTER (WHERE source_column = 'D'),
        CASE WHEN education_category_id <> 'territory_total' AND 'D' IN ('G','H')
             THEN 'not_applicable' ELSE 'missing_observation' END) AS female_status,
    coalesce(max(value_status) FILTER (WHERE source_column = 'E'),
        CASE WHEN education_category_id <> 'territory_total' AND 'E' IN ('G','H')
             THEN 'not_applicable' ELSE 'missing_observation' END) AS urban_status,
    coalesce(max(value_status) FILTER (WHERE source_column = 'F'),
        CASE WHEN education_category_id <> 'territory_total' AND 'F' IN ('G','H')
             THEN 'not_applicable' ELSE 'missing_observation' END) AS rural_status,
    coalesce(max(value_status) FILTER (WHERE source_column = 'G'),
        CASE WHEN education_category_id <> 'territory_total' AND 'G' IN ('G','H')
             THEN 'not_applicable' ELSE 'missing_observation' END) AS no_completed_education_status,
    coalesce(max(value_status) FILTER (WHERE source_column = 'H'),
        CASE WHEN education_category_id <> 'territory_total' AND 'H' IN ('G','H')
             THEN 'not_applicable' ELSE 'missing_observation' END) AS under_2_years_status
FROM education.population_statistics
WHERE reference_date = DATE '2021-12-01'
GROUP BY reference_date, territory_id, territory_name, territory_level, education_category_id, parent_category_id, education_category_name_original, education_category_name_en, education_category_path, hierarchy_level, category_type, is_aggregate, source_file, source_sheet
)
SELECT reference_date, territory_id, territory_name, territory_level, education_category_id, parent_category_id, education_category_name_original, education_category_name_en, education_category_path, hierarchy_level, category_type, is_aggregate,
    total, male, female, urban, rural, no_completed_education, under_2_years,
    CASE WHEN education_category_id = 'territory_total' AND total_status = 'numeric'
             AND no_completed_education_status = 'numeric' AND under_2_years_status = 'numeric'
         THEN total::numeric + no_completed_education + under_2_years END AS resident_population_total,
    total_status, male_status, female_status, urban_status, rural_status, no_completed_education_status, under_2_years_status,
    CASE WHEN education_category_id = 'territory_total' AND total_status = 'numeric'
             AND no_completed_education_status = 'numeric' AND under_2_years_status = 'numeric' THEN 'numeric'
         WHEN education_category_id <> 'territory_total' THEN 'not_applicable'
         ELSE 'not_evaluable' END AS resident_population_total_status,
    CASE WHEN education_category_id = 'territory_total' AND total_status = 'numeric'
             AND no_completed_education_status = 'numeric' AND under_2_years_status = 'numeric' THEN 'calculated' END AS resident_population_total_method,
    source_file, source_sheet
FROM pivoted;
