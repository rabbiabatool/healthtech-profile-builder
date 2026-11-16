import json

from mlcore import config, eda


def test_eda_writes_summary_and_figures(tmp_path):
    eda.main(out_dir=tmp_path)

    for name in (
        "eda_summary.json",
        "target_balance.png",
        "missing_values.png",
        "numeric_distributions.png",
        "no_show_rate_by_lead_time.png",
    ):
        assert (tmp_path / name).exists()

    saved = json.loads((tmp_path / "eda_summary.json").read_text(encoding="utf-8"))
    assert saved["seed"] == config.SEED
    assert saved["leakage_check"]["missing_rate_when_no_show"] == 1.0
    assert saved["leakage_check"]["missing_rate_when_attended"] == 0.0
