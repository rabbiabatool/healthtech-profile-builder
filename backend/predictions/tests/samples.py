"""Shared example inputs for the predictions tests (not a test file itself)."""

VALID = {
    "age": 34,
    "lead_time_days": 45,
    "scheduled_hour": 16,
    "day_of_week": "MON",
    "appointment_type": "FOLLOW_UP",
    "reminder_sent": False,
    "previous_appointments": 6,
    "previous_no_shows": 2,
    "distance_km": 12.5,
}


def changed(**changes):
    payload = dict(VALID)
    payload.update(changes)
    return payload


def missing(name):
    payload = dict(VALID)
    del payload[name]
    return payload
