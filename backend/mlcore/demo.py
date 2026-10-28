"""Prints a real request and response using the saved model:  python -m mlcore.demo"""
import json

from mlcore import registry

SAMPLE_REQUEST = {
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


def main(artifact_dir=None):
    loaded = registry.load_model(artifact_dir)
    response = registry.predict_one(loaded, SAMPLE_REQUEST)
    print("POST /api/v1/ml/no-show/predict")
    print(json.dumps(SAMPLE_REQUEST, indent=2))
    print("\n200 OK")
    print(json.dumps(response, indent=2))
    return response


if __name__ == "__main__":
    main()