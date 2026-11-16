"""Single source of truth for the columns and allowed ranges.

The API validation (Phase 11) and the dashboard form (Phase 12) will both
read from here, so a range is only ever defined once.
"""

ID_COLUMNS = ["appointment_id", "patient_ref"]
TARGET_COLUMN = "no_show"
LEAKAGE_COLUMNS = ["checkin_delay_minutes"]

NUMERIC_RANGES = {
    "age": (18, 95),
    "lead_time_days": (0, 180),
    "scheduled_hour": (8, 17),
    "previous_appointments": (0, 60),
    "previous_no_shows": (0, 60),
    "distance_km": (0.0, 100.0),
}

CATEGORICAL_VALUES = {
    "day_of_week": ["MON", "TUE", "WED", "THU", "FRI"],
    "appointment_type": ["CHECKUP", "FOLLOW_UP", "VACCINATION", "LAB_TEST", "SPECIALIST"],
}

BOOLEAN_FEATURES = ["reminder_sent"]
NULLABLE_FEATURES = ["distance_km"]

FEATURE_COLUMNS = [
    "age",
    "lead_time_days",
    "scheduled_hour",
    "day_of_week",
    "appointment_type",
    "reminder_sent",
    "previous_appointments",
    "previous_no_shows",
    "distance_km",
]

NUMERIC_FEATURES = list(NUMERIC_RANGES)
CATEGORICAL_FEATURES = list(CATEGORICAL_VALUES)

RAW_COLUMNS = ID_COLUMNS + FEATURE_COLUMNS + LEAKAGE_COLUMNS + [TARGET_COLUMN]

FORBIDDEN_COLUMNS = [
    "gender", "sex", "ethnicity", "race", "religion", "disability",
    "neighbourhood", "neighborhood", "postcode", "zip_code",
    "date_of_birth", "name", "email", "phone",
]
