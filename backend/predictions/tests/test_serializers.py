import pytest

from mlcore import schema
from predictions.serializers import PredictionInputSerializer
from predictions.tests.samples import VALID, changed, missing

BAD_CASES = [
    ("age_too_low", changed(age=17), "age"),
    ("age_too_high", changed(age=96), "age"),
    ("age_string", changed(age="34"), "age"),
    ("age_float", changed(age=34.5), "age"),
    ("age_bool", changed(age=True), "age"),
    ("age_null", changed(age=None), "age"),
    ("age_missing", missing("age"), "age"),
    ("age_huge", changed(age=10**30), "age"),
    ("lead_negative", changed(lead_time_days=-1), "lead_time_days"),
    ("lead_too_long", changed(lead_time_days=181), "lead_time_days"),
    ("hour_early", changed(scheduled_hour=7), "scheduled_hour"),
    ("hour_late", changed(scheduled_hour=18), "scheduled_hour"),
    ("day_unknown", changed(day_of_week="SUN"), "day_of_week"),
    ("day_lowercase", changed(day_of_week="mon"), "day_of_week"),
    ("day_number", changed(day_of_week=1), "day_of_week"),
    ("type_unknown", changed(appointment_type="SURGERY"), "appointment_type"),
    ("type_very_long", changed(appointment_type="A" * 10000), "appointment_type"),
    ("reminder_string", changed(reminder_sent="yes"), "reminder_sent"),
    ("reminder_number", changed(reminder_sent=1), "reminder_sent"),
    ("history_negative", changed(previous_appointments=-1), "previous_appointments"),
    ("history_too_big", changed(previous_appointments=61), "previous_appointments"),
    ("no_shows_exceed_history", changed(previous_appointments=2, previous_no_shows=3), "previous_no_shows"),
    ("distance_negative", changed(distance_km=-0.1), "distance_km"),
    ("distance_too_far", changed(distance_km=100.1), "distance_km"),
    ("distance_string", changed(distance_km="far"), "distance_km"),
    ("distance_bool", changed(distance_km=True), "distance_km"),
    ("distance_infinite", changed(distance_km=float("inf")), "distance_km"),
    ("distance_nan", changed(distance_km=float("nan")), "distance_km"),
    ("distance_missing", missing("distance_km"), "distance_km"),
    ("unknown_field", changed(gender="F"), "gender"),
    ("leakage_column", changed(checkin_delay_minutes=3.0), "checkin_delay_minutes"),
]


@pytest.mark.parametrize(
    "payload,field", [case[1:] for case in BAD_CASES], ids=[case[0] for case in BAD_CASES]
)
def test_invalid_input_is_rejected_and_names_the_field(payload, field):
    serializer = PredictionInputSerializer(data=payload)
    assert not serializer.is_valid()
    assert field in serializer.errors


def test_a_normal_request_is_valid():
    serializer = PredictionInputSerializer(data=VALID)
    assert serializer.is_valid(), serializer.errors


def test_distance_may_be_null():
    serializer = PredictionInputSerializer(data=changed(distance_km=None))
    assert serializer.is_valid(), serializer.errors
    assert serializer.validated_data["distance_km"] is None


@pytest.mark.parametrize(
    "overrides",
    [
        {"age": 18}, {"age": 95}, {"lead_time_days": 0}, {"lead_time_days": 180},
        {"scheduled_hour": 8}, {"scheduled_hour": 17}, {"distance_km": 0}, {"distance_km": 100},
        {"previous_appointments": 0, "previous_no_shows": 0},
        {"previous_appointments": 5, "previous_no_shows": 5},
    ],
)
def test_values_exactly_on_the_boundary_are_accepted(overrides):
    serializer = PredictionInputSerializer(data=changed(**overrides))
    assert serializer.is_valid(), serializer.errors


def test_empty_and_non_object_bodies_are_rejected():
    empty = PredictionInputSerializer(data={})
    assert not empty.is_valid()
    assert set(empty.errors) == set(schema.FEATURE_COLUMNS)
    not_an_object = PredictionInputSerializer(data=[])
    assert not not_an_object.is_valid()
    assert "non_field_errors" in not_an_object.errors


def test_serializer_fields_and_ranges_come_from_the_schema():
    serializer = PredictionInputSerializer()
    assert set(serializer.fields) == set(schema.FEATURE_COLUMNS)
    for name, (low, high) in schema.NUMERIC_RANGES.items():
        field = serializer.fields[name]
        assert field.min_value == low and field.max_value == high