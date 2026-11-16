
import pytest

from mlcore.data_generation import generate_appointments
from mlcore.supervised_workbench import train_and_evaluate_all


@pytest.fixture(scope="module")
def small_df():
    return generate_appointments(n_patients=500, n_appointments=2000, seed=13)


@pytest.fixture(scope="module")
def workbench_results(small_df, tmp_path_factory):
    temp_dir = tmp_path_factory.mktemp("workbench_artifacts")
    docs_dir = temp_dir / "docs"
    return train_and_evaluate_all(
        df=small_df,
        seed=13,
        run_tuning=True,
        artifact_dir=temp_dir,
        docs_dir=docs_dir,
    )


def test_workbench_trains_all_required_algorithms(workbench_results):
    comparison = workbench_results["comparison_table"]
    model_keys = {row["model_key"] for row in comparison}
    # Must train at least Logistic Regression, Random Forest, Gradient Boosting, plus Dummy and Tuned
    expected_models = {
        "dummy",
        "logistic_regression",
        "random_forest",
        "gradient_boosting",
        "tuned_random_forest",
    }
    assert expected_models.issubset(model_keys), f"Missing models: {expected_models - model_keys}"
    assert len(comparison) >= 4


def test_each_model_has_complete_classification_metrics(workbench_results):
    for row in workbench_results["comparison_table"]:
        assert 0.0 <= row["test_pr_auc"] <= 1.0
        assert 0.0 <= row["test_roc_auc"] <= 1.0
        assert 0.0 <= row["test_f1"] <= 1.0
        assert 0.0 <= row["test_precision"] <= 1.0
        assert 0.0 <= row["test_recall"] <= 1.0
        assert 0.0 <= row["test_specificity"] <= 1.0
        assert 0.0 <= row["test_brier"] <= 1.0
        assert "train_val_pr_auc_gap" in row


def test_confusion_matrices_are_valid_and_sum_to_test_size(workbench_results):
    test_rows = workbench_results["dataset"]["splits"]["test"]["rows"]
    for row in workbench_results["comparison_table"]:
        cm = row["confusion_matrix_test"]
        total = cm["tn"] + cm["fp"] + cm["fn"] + cm["tp"]
        assert total == test_rows, f"Confusion matrix total {total} != {test_rows}"


def test_hyperparameter_tuning_experiment(workbench_results):
    tuning = workbench_results["tuning"]
    assert tuning["algorithm"] == "RandomForestClassifier"
    assert tuning["search_method"] == "GridSearchCV"
    assert tuning["scoring"] == "average_precision (PR-AUC)"
    assert tuning["best_params"] is not None
    assert "model__max_depth" in tuning["best_params"]
    assert "model__n_estimators" in tuning["best_params"]
    assert tuning["best_cv_score"] > 0.15
    assert len(tuning["trials"]) > 0


def test_overfitting_analysis_is_present(workbench_results):
    for name, detail in workbench_results["models_detail"].items():
        gap = detail["overfitting_gap"]
        assert "pr_auc_gap" in gap
        assert "f1_gap" in gap
        assert "accuracy_gap" in gap


def test_error_analysis_inspects_false_positives_and_negatives(workbench_results):
    lr_detail = workbench_results["models_detail"]["logistic_regression"]
    errors = lr_detail["error_analysis"]
    assert errors is not None
    assert "false_positives" in errors
    assert "false_negatives" in errors
    assert errors["false_positives"]["count"] > 0
    assert errors["false_negatives"]["count"] > 0
    assert "explanation" in errors["false_positives"]
    assert "explanation" in errors["false_negatives"]
