CREATE TABLE IF NOT EXISTS reference.territory (
    territory_id text PRIMARY KEY,
    territory_name_original text NOT NULL,
    territory_name_normalised text NOT NULL,
    territory_level text NOT NULL CHECK (territory_level IN ('national','county','municipality')),
    parent_territory_id text REFERENCES reference.territory DEFERRABLE INITIALLY DEFERRED
);
CREATE TABLE IF NOT EXISTS reference.education_classification (
    education_category_id text PRIMARY KEY,
    parent_category_id text REFERENCES reference.education_classification DEFERRABLE INITIALLY DEFERRED,
    education_category_name_original text NOT NULL,
    education_category_name_en text NOT NULL,
    hierarchy_level integer NOT NULL CHECK (hierarchy_level >= 0),
    category_path text NOT NULL UNIQUE,
    category_type text NOT NULL,
    display_order integer NOT NULL UNIQUE,
    is_aggregate boolean NOT NULL,
    source_indent integer NOT NULL CHECK (source_indent >= 0)
);
CREATE TABLE IF NOT EXISTS reference.statistical_indicator (
    indicator_code text NOT NULL,
    breakdown_type text NOT NULL,
    breakdown_category text NOT NULL,
    source_column text NOT NULL UNIQUE,
    PRIMARY KEY (indicator_code, breakdown_type, breakdown_category),
    UNIQUE (indicator_code, breakdown_type, breakdown_category, source_column)
);
INSERT INTO reference.statistical_indicator VALUES
    ('completed_education','overall','total','B'),
    ('completed_education','sex','male','C'),
    ('completed_education','sex','female','D'),
    ('completed_education','residence','urban','E'),
    ('completed_education','residence','rural','F'),
    ('no_completed_education','overall','total','G'),
    ('under_age_two','overall','total','H')
ON CONFLICT DO NOTHING;
CREATE TABLE IF NOT EXISTS qa.etl_run (
    run_id uuid PRIMARY KEY,
    loaded_at timestamptz NOT NULL DEFAULT now(),
    source_file text NOT NULL,
    csv_sha256 text NOT NULL UNIQUE,
    observation_count integer NOT NULL CHECK (observation_count > 0)
);
CREATE TABLE IF NOT EXISTS staging.education_statistics_raw (
reference_date date NOT NULL,
territory_id text NOT NULL,
territory_name text NOT NULL,
territory_level text NOT NULL,
education_category_id text NOT NULL,
parent_category_id text,
education_category_name_original text NOT NULL,
education_category_name_en text NOT NULL,
education_category_path text NOT NULL,
category_type text NOT NULL,
hierarchy_level integer NOT NULL CHECK (hierarchy_level >= 0),
is_aggregate boolean NOT NULL,
indicator_code text NOT NULL,
breakdown_type text NOT NULL,
breakdown_category text NOT NULL,
population_count bigint CHECK (population_count >= 0),
value_status text NOT NULL CHECK (value_status IN ('numeric', 'confidential', 'dash_unresolved', 'blank')),
raw_value text,
source_file text NOT NULL,
source_sheet text NOT NULL,
source_row integer NOT NULL CHECK (source_row > 0),
source_column text NOT NULL CHECK (source_column IN ('B','C','D','E','F','G','H')),
CHECK ((value_status = 'numeric') = (population_count IS NOT NULL)),
CHECK (source_column NOT IN ('G','H') OR education_category_id = 'territory_total'),
PRIMARY KEY (reference_date, territory_id, education_category_id, indicator_code, breakdown_type, breakdown_category),
UNIQUE (source_file, source_sheet, source_row, source_column)
);
CREATE TABLE IF NOT EXISTS education.population_statistics (
    LIKE staging.education_statistics_raw INCLUDING ALL,
    run_id uuid NOT NULL REFERENCES qa.etl_run,
    FOREIGN KEY (territory_id) REFERENCES reference.territory,
    FOREIGN KEY (education_category_id) REFERENCES reference.education_classification,
    FOREIGN KEY (parent_category_id) REFERENCES reference.education_classification,
    FOREIGN KEY (indicator_code, breakdown_type, breakdown_category, source_column)
        REFERENCES reference.statistical_indicator (indicator_code, breakdown_type, breakdown_category, source_column)
);
CREATE INDEX IF NOT EXISTS population_indicator_territory ON education.population_statistics (indicator_code, territory_id);
CREATE TABLE IF NOT EXISTS qa.validation_results (
    validation_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    run_id uuid NOT NULL REFERENCES qa.etl_run,
    rule_id text NOT NULL,
    rule_name text NOT NULL,
    severity text NOT NULL CHECK (severity IN ('ERROR','WARNING','INFO','NOT_EVALUABLE')),
    territory_id text REFERENCES reference.territory,
    education_category_id text REFERENCES reference.education_classification,
    source_sheet text,
    source_row integer,
    affected_columns text,
    expected_value text,
    observed_value text,
    difference bigint,
    message text NOT NULL
);
CREATE INDEX IF NOT EXISTS validation_territory ON qa.validation_results (territory_id, severity);
