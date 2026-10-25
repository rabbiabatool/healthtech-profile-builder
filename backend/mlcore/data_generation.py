"""Seeded generator for fictional clinic appointments (no real people)."""
import hashlib

import numpy as np
import pandas as pd

from mlcore import config, schema

DAY_EFFECT = {"MON": 0.20, "TUE": 0.0, "WED": 0.0, "THU": -0.05, "FRI": 0.25}
TYPE_EFFECT = {
    "CHECKUP": 0.10,
    "FOLLOW_UP": 0.0,
    "VACCINATION": -0.20,
    "LAB_TEST": -0.30,
    "SPECIALIST": 0.35,
}


def _sigmoid(x):
    return 1.0 / (1.0 + np.exp(-x))


def _find_intercept(raw_logit, target_rate):
    """Shift the scores so the average probability equals target_rate."""
    low, high = -15.0, 15.0
    for _ in range(60):
        mid = (low + high) / 2
        if _sigmoid(raw_logit + mid).mean() < target_rate:
            low = mid
        else:
            high = mid
    return (low + high) / 2


def generate_appointments(
    n_patients=config.N_PATIENTS,
    n_appointments=config.N_APPOINTMENTS,
    seed=config.SEED,
):
    if n_patients < 1 or n_appointments < 1:
        raise ValueError("n_patients and n_appointments must be at least 1")

    rng = np.random.default_rng(seed)

    # --- One value per patient -------------------------------------------
    patient_age = np.clip(np.round(rng.normal(45, 16, n_patients)), 18, 95).astype(int)
    patient_distance = np.clip(np.round(rng.lognormal(2.3, 0.8, n_patients), 1), 0.5, 100.0)
    patient_effect = rng.normal(0, 0.8, n_patients)  # hidden habit; never a feature
    prior_appts = np.minimum(rng.poisson(4, n_patients), 40)
    prior_no_shows = rng.binomial(prior_appts, _sigmoid(patient_effect - 1.4))

    # --- One value per appointment ---------------------------------------
    patient_idx = rng.integers(0, n_patients, size=n_appointments)
    lead_time = np.clip(np.round(rng.gamma(1.5, 20.0, n_appointments)), 0, 180).astype(int)
    hour = rng.integers(8, 18, size=n_appointments)
    day = rng.choice(
        schema.CATEGORICAL_VALUES["day_of_week"], size=n_appointments,
        p=[0.22, 0.20, 0.20, 0.20, 0.18],
    )
    appt_type = rng.choice(
        schema.CATEGORICAL_VALUES["appointment_type"], size=n_appointments,
        p=[0.25, 0.30, 0.15, 0.15, 0.15],
    )
    reminder = (rng.random(n_appointments) < 0.60)

    age = patient_age[patient_idx]
    distance = patient_distance[patient_idx]
    reminder_f = reminder.astype(float)

    # --- The invented rule that decides who misses an appointment --------
    logit = (
        1.2 * (1 - np.exp(-lead_time / 40.0)) - 0.6
        - 0.5 * reminder_f
        - 0.6 * reminder_f * (lead_time > 30)
        + 0.012 * (40 - age)
        + 0.06 * np.abs(hour - 12.5)
        + pd.Series(day).map(DAY_EFFECT).to_numpy()
        + pd.Series(appt_type).map(TYPE_EFFECT).to_numpy()
        + 0.015 * distance
        + patient_effect[patient_idx]
        + rng.normal(0, 0.5, n_appointments)
    )

    flip = config.LABEL_FLIP_RATE
    pre_flip_rate = (config.TARGET_NO_SHOW_RATE - flip) / (1 - 2 * flip)
    logit = logit + _find_intercept(logit, pre_flip_rate)

    no_show = (rng.random(n_appointments) < _sigmoid(logit)).astype(int)
    flipped = rng.random(n_appointments) < flip
    no_show = np.where(flipped, 1 - no_show, no_show)

    # --- History features: only look backwards ---------------------------
    outcome = pd.Series(no_show)
    by_patient = outcome.groupby(patient_idx)
    earlier_appts = by_patient.cumcount().to_numpy()
    earlier_no_shows = (by_patient.cumsum() - outcome).to_numpy()
    previous_appts = np.minimum(prior_appts[patient_idx] + earlier_appts, 60)
    previous_no_shows = np.minimum(prior_no_shows[patient_idx] + earlier_no_shows, previous_appts)

    # --- Missing values and the leakage trap -----------------------------
    distance_observed = distance.astype(float)
    distance_observed[rng.random(n_appointments) < config.DISTANCE_MISSING_RATE] = np.nan

    checkin_delay = np.round(np.clip(rng.normal(6, 9, n_appointments), -15, 60), 1)
    checkin_delay = np.where(no_show == 1, np.nan, checkin_delay)

    df = pd.DataFrame({
        "appointment_id": np.char.add("APT-", np.char.zfill(np.arange(1, n_appointments + 1).astype(str), 6)),
        "patient_ref": np.char.add("PAT-", np.char.zfill(patient_idx.astype(str), 5)),
        "age": age,
        "lead_time_days": lead_time,
        "scheduled_hour": hour,
        "day_of_week": day,
        "appointment_type": appt_type,
        "reminder_sent": reminder,
        "previous_appointments": previous_appts,
        "previous_no_shows": previous_no_shows,
        "distance_km": distance_observed,
        "checkin_delay_minutes": checkin_delay,
        "no_show": no_show,
    })
    return df[schema.RAW_COLUMNS]


def dataset_hash(df):
    """A fingerprint: identical data always gives the identical hash."""
    row_hashes = pd.util.hash_pandas_object(df, index=False).to_numpy()
    return hashlib.sha256(row_hashes.tobytes()).hexdigest()


def main():
    df = generate_appointments()
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    path = config.DATA_DIR / "appointments.csv"
    df.to_csv(path, index=False)
    print(f"Wrote {len(df)} rows to {path}")
    print(f"Data version: {config.DATA_VERSION}, seed: {config.SEED}")
    print(f"No-show rate: {df[schema.TARGET_COLUMN].mean():.3f}")
    print(f"SHA-256: {dataset_hash(df)}")


if __name__ == "__main__":
    main()