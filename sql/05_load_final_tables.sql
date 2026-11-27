-- Set psql variable run_id to a UUID already registered in qa.etl_run.
-- This replaces only census snapshots present in staging. Keep the staging lock until commit.
DELETE FROM education.population_statistics AS p
USING (SELECT DISTINCT reference_date FROM staging.education_statistics_raw) AS s
WHERE p.reference_date = s.reference_date;
INSERT INTO education.population_statistics
SELECT s.*, :'run_id'::uuid FROM staging.education_statistics_raw AS s;
