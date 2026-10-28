# Data card: synthetic clinic appointments

## Purpose
Teaching dataset for a scheduling-operations example: estimating the likelihood
that a fictional appointment is a no-show. It is NOT a medical dataset.

## Provenance
Generated entirely by `backend/mlcore/data_generation.py` using a fixed seed
(42). No real people, no scraped data, no external dataset. Version:
`synthetic-appointments-1.0.0`.

## Licence
Generated data is dedicated to the public domain (CC0). Code licence is stated
in the repository root.

## Schema
| Column | Type | Used as feature | Notes |
|---|---|---|---|
| appointment_id | string | No | identifier |
| patient_ref | string | No | only used to keep a patient's rows in one split |
| age | int 18-95 | Yes | adult scope; fairness risk, see below |
| lead_time_days | int 0-180 | Yes | days between booking and appointment |
| scheduled_hour | int 8-17 | Yes | clinic hours |
| day_of_week | MON-FRI | Yes | |
| appointment_type | CHECKUP, FOLLOW_UP, VACCINATION, LAB_TEST, SPECIALIST | Yes | |
| reminder_sent | boolean | Yes | |
| previous_appointments | int 0-60 | Yes | history before this appointment |
| previous_no_shows | int 0-60 | Yes | history before this appointment |
| distance_km | float 0-100 | Yes | about 8% missing |
| checkin_delay_minutes | float | NO | leakage trap: known only after the appointment |
| no_show | 0/1 | Target | about 20% positive |

## How the labels are made
Outcomes come from an invented scoring rule plus noise: a non-linear lead-time
effect, an interaction (reminders help more for long lead times), small
weekday, hour and appointment-type effects, distance, age, a hidden
per-patient habit, random noise, and about 3% of labels deliberately flipped.
The intercept is tuned so about 20% of appointments are no-shows.

## Class imbalance
About 20% no-shows. Accuracy alone is misleading (always predicting "attends"
scores about 80%), so Phase 10 uses PR-AUC as the primary metric.

## Missing values
Only `distance_km` is missing (about 8%, completely at random). The pipeline
imputes it using training data only. `checkin_delay_minutes` is empty exactly
when the patient did not attend, which is why it must never be a feature.

## Observed values (from docs/ml/eda/eda_summary.json)
| Item | Value |
|---|---|
| Rows | 20000 |
| Unique patients | 5765 |
| No-show rate | 0.1991 |
| Dataset SHA-256 | e86a485d5b11cb669df9c2c0e09496edaf29f4f7a557868e2542c876ad4f377b |

## Bias and fairness
Gender, ethnicity, religion, disability, neighbourhood and similar attributes
are deliberately excluded. Age is included because it is common in scheduling
data, but it is a fairness risk: a real system could treat age groups unfairly.
Phase 10 reports metrics by age band.

## Limitations
Because we invented the rules that create the labels, a model can only learn
our assumptions. Metrics show how well it recovers an invented pattern, not how
it would perform in a real clinic. No clinical validity, no diagnosis, not for
decisions about anyone's care.

## Reproduce
From the `backend` folder:
`python -m mlcore.data_generation` and `python -m mlcore.eda`