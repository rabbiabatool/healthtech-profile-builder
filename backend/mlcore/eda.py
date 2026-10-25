"""Repeatable exploratory data analysis: writes a JSON summary and charts."""
import json

import matplotlib

matplotlib.use("Agg")  # draw to files only, no pop-up windows
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from mlcore import config, schema  # noqa: E402
from mlcore.data_generation import dataset_hash, generate_appointments  # noqa: E402

TARGET = schema.TARGET_COLUMN


def build_summary(df):
    missing = df[schema.LEAKAGE_COLUMNS[0]].isna()
    numeric_summary = df[list(schema.NUMERIC_RANGES)].describe().round(2).to_dict()
    return {
        "data_version": config.DATA_VERSION,
        "seed": config.SEED,
        "dataset_sha256": dataset_hash(df),
        "rows": int(len(df)),
        "unique_patients": int(df["patient_ref"].nunique()),
        "no_show_rate": round(float(df[TARGET].mean()), 4),
        "missing_rate_by_column": {
            name: round(float(rate), 4) for name, rate in df.isna().mean().items()
        },
        "numeric_summary": numeric_summary,
        "leakage_check": {
            "column": schema.LEAKAGE_COLUMNS[0],
            "missing_rate_when_no_show": round(float(missing[df[TARGET] == 1].mean()), 4),
            "missing_rate_when_attended": round(float(missing[df[TARGET] == 0].mean()), 4),
        },
    }


def _save(fig, path):
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)


def make_figures(df, out_dir):
    counts = df[TARGET].value_counts().sort_index()
    fig, ax = plt.subplots(figsize=(4, 3))
    ax.bar(["Attended (0)", "No-show (1)"], counts.to_numpy())
    ax.set_ylabel("Appointments")
    ax.set_title("Target balance")
    _save(fig, out_dir / "target_balance.png")

    missing = (df.isna().mean() * 100)
    missing = missing[missing > 0].sort_values()
    fig, ax = plt.subplots(figsize=(6, 3))
    ax.barh(missing.index, missing.to_numpy())
    ax.set_xlabel("Missing values (%)")
    ax.set_title("Missing values by column")
    _save(fig, out_dir / "missing_values.png")

    fig, axes = plt.subplots(2, 3, figsize=(10, 6))
    for ax, column in zip(axes.flat, schema.NUMERIC_RANGES):
        ax.hist(df[column].dropna(), bins=30)
        ax.set_title(column)
    _save(fig, out_dir / "numeric_distributions.png")

    buckets = pd.cut(
        df["lead_time_days"],
        bins=[-1, 7, 14, 30, 60, 90, 180],
        labels=["0-7", "8-14", "15-30", "31-60", "61-90", "91-180"],
    )
    rate = df.groupby(buckets, observed=True)[TARGET].mean()
    fig, ax = plt.subplots(figsize=(6, 3))
    ax.bar(rate.index.astype(str), rate.to_numpy())
    ax.set_xlabel("Lead time (days)")
    ax.set_ylabel("No-show rate")
    ax.set_title("No-show rate by lead time")
    _save(fig, out_dir / "no_show_rate_by_lead_time.png")


def main(out_dir=config.EDA_DIR):
    out_dir.mkdir(parents=True, exist_ok=True)
    df = generate_appointments()
    summary = build_summary(df)
    with open(out_dir / "eda_summary.json", "w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2, sort_keys=True)
    make_figures(df, out_dir)
    print(f"EDA written to {out_dir}")
    print(json.dumps({k: summary[k] for k in ("rows", "unique_patients", "no_show_rate")}))
    return summary


if __name__ == "__main__":
    main()