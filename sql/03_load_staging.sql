-- Run after 01 and 02, inside the transaction described in docs/database_model.md.
LOCK TABLE staging.education_statistics_raw IN ACCESS EXCLUSIVE MODE;
TRUNCATE staging.education_statistics_raw;
-- In psql run the following as one line, using a path visible to the client:
-- \copy staging.education_statistics_raw FROM 'output/education_statistics_2021.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8', NULL '\N', FORCE_NULL (parent_category_id,population_count,raw_value))
