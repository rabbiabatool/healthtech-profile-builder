from mlcore import schema


def test_feature_columns_have_no_duplicates():
    assert len(schema.FEATURE_COLUMNS) == len(set(schema.FEATURE_COLUMNS))


def test_feature_groups_cover_exactly_the_feature_columns():
    grouped = (
        set(schema.NUMERIC_FEATURES)
        | set(schema.CATEGORICAL_FEATURES)
        | set(schema.BOOLEAN_FEATURES)
    )
    assert grouped == set(schema.FEATURE_COLUMNS)


def test_features_never_include_ids_target_or_leakage_columns():
    forbidden = set(schema.ID_COLUMNS) | set(schema.LEAKAGE_COLUMNS) | {schema.TARGET_COLUMN}
    assert forbidden.isdisjoint(schema.FEATURE_COLUMNS)


def test_raw_columns_are_unique_and_exclude_forbidden_names():
    assert len(schema.RAW_COLUMNS) == len(set(schema.RAW_COLUMNS))
    assert set(schema.FORBIDDEN_COLUMNS).isdisjoint(schema.RAW_COLUMNS)


def test_ranges_are_sensible_and_nullable_columns_are_features():
    for low, high in schema.NUMERIC_RANGES.values():
        assert low < high
    assert set(schema.NULLABLE_FEATURES) <= set(schema.FEATURE_COLUMNS)
