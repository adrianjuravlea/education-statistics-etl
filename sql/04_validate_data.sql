DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM staging.education_statistics_raw) THEN
        RAISE EXCEPTION 'Staging is empty';
    END IF;
    IF EXISTS (
        SELECT 1 FROM staging.education_statistics_raw AS s
        LEFT JOIN reference.territory AS t USING (territory_id)
        LEFT JOIN reference.education_classification AS c USING (education_category_id)
        LEFT JOIN reference.statistical_indicator AS i USING (indicator_code, breakdown_type, breakdown_category, source_column)
        WHERE t.territory_id IS NULL OR c.education_category_id IS NULL OR i.source_column IS NULL
           OR s.territory_level <> t.territory_level OR s.source_sheet <> t.territory_name_original
           OR c.category_type = 'heading' OR s.parent_category_id IS DISTINCT FROM c.parent_category_id
           OR s.education_category_path <> c.category_path OR s.hierarchy_level <> c.hierarchy_level
           OR s.is_aggregate <> c.is_aggregate
           OR (s.value_status = 'confidential') IS DISTINCT FROM coalesce(btrim(s.raw_value) = '*', false)
           OR (s.value_status = 'dash_unresolved') IS DISTINCT FROM coalesce(btrim(s.raw_value) IN ('-','–','—','−'), false)
    ) THEN
        RAISE EXCEPTION 'Staged rows violate reference or source notation rules';
    END IF;
END $$;
