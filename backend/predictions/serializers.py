import math
from collections.abc import Mapping

from rest_framework import serializers

from mlcore import schema


class StrictIntegerField(serializers.IntegerField):
    """Whole numbers only: no strings like "34", no 34.5, no true/false."""

    def to_internal_value(self, data):
        if isinstance(data, bool) or not isinstance(data, int):
            self.fail("invalid")
        return super().to_internal_value(data)


class StrictFloatField(serializers.FloatField):
    """Numbers only (not strings or booleans), and never NaN or infinity."""

    def to_internal_value(self, data):
        if isinstance(data, bool) or not isinstance(data, (int, float)):
            self.fail("invalid")
        value = super().to_internal_value(data)
        if not math.isfinite(value):
            self.fail("invalid")
        return value


class StrictBooleanField(serializers.BooleanField):
    """Only real JSON true/false, not "yes", 1 or "true"."""

    def to_internal_value(self, data):
        if not isinstance(data, bool):
            self.fail("invalid")
        return data


def _integer(name):
    low, high = schema.NUMERIC_RANGES[name]
    return StrictIntegerField(min_value=low, max_value=high)


class PredictionInputSerializer(serializers.Serializer):
    age = _integer("age")
    lead_time_days = _integer("lead_time_days")
    scheduled_hour = _integer("scheduled_hour")
    day_of_week = serializers.ChoiceField(choices=schema.CATEGORICAL_VALUES["day_of_week"])
    appointment_type = serializers.ChoiceField(choices=schema.CATEGORICAL_VALUES["appointment_type"])
    reminder_sent = StrictBooleanField()
    previous_appointments = _integer("previous_appointments")
    previous_no_shows = _integer("previous_no_shows")
    distance_km = StrictFloatField(
        min_value=schema.NUMERIC_RANGES["distance_km"][0],
        max_value=schema.NUMERIC_RANGES["distance_km"][1],
        allow_null=True,
    )

    def to_internal_value(self, data):
        unknown = {}
        if isinstance(data, Mapping):
            unknown = {name: ["Unknown field."] for name in sorted(data) if name not in self.fields}
        try:
            validated = super().to_internal_value(data)
        except serializers.ValidationError as error:
            errors = dict(error.detail) if isinstance(error.detail, dict) else {"non_field_errors": error.detail}
            errors.update(unknown)
            raise serializers.ValidationError(errors)
        if unknown:
            raise serializers.ValidationError(unknown)
        return validated

    def validate(self, attrs):
        if attrs["previous_no_shows"] > attrs["previous_appointments"]:
            raise serializers.ValidationError(
                {"previous_no_shows": "Cannot be greater than previous_appointments."}
            )
        return attrs
