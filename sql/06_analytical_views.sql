CREATE OR REPLACE VIEW education.completed_education AS
SELECT * FROM education.population_statistics
WHERE indicator_code = 'completed_education' AND breakdown_type = 'overall' AND category_type = 'level';

CREATE OR REPLACE VIEW education.completed_education_by_sex AS
SELECT * FROM education.population_statistics
WHERE indicator_code = 'completed_education' AND breakdown_type = 'sex' AND education_category_id = 'territory_total';

CREATE OR REPLACE VIEW education.completed_education_by_residence AS
SELECT * FROM education.population_statistics
WHERE indicator_code = 'completed_education' AND breakdown_type = 'residence' AND education_category_id = 'territory_total';

CREATE OR REPLACE VIEW education.without_completed_education AS
SELECT * FROM education.population_statistics WHERE indicator_code = 'no_completed_education';

CREATE OR REPLACE VIEW qa.issues_by_territory AS
SELECT run_id, territory_id, severity, rule_id, count(*) AS issue_count
FROM qa.validation_results WHERE severity <> 'INFO'
GROUP BY run_id, territory_id, severity, rule_id;

CREATE OR REPLACE VIEW qa.missingness_by_territory AS
SELECT reference_date, territory_level, territory_id, value_status, count(*) AS source_cell_count
FROM education.population_statistics WHERE value_status <> 'numeric'
GROUP BY reference_date, territory_level, territory_id, value_status;
