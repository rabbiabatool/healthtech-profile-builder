"""Charts for the model card. Saved as PNG files, no pop-up windows."""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from sklearn.metrics import precision_recall_curve  # noqa: E402


def _save(fig, path):
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)


def plot_pr_curves(y_true, probabilities, path):
    fig, ax = plt.subplots(figsize=(5, 4))
    for name, prob in probabilities.items():
        precision, recall, _ = precision_recall_curve(y_true, prob)
        ax.plot(recall, precision, label=name)
    ax.axhline(y_true.mean(), linestyle="--", color="grey", label="base rate (dummy)")
    ax.set_xlabel("Recall")
    ax.set_ylabel("Precision")
    ax.set_title("Precision-recall curves (test set)")
    ax.legend()
    _save(fig, path)


def plot_calibration(points, path):
    fig, ax = plt.subplots(figsize=(4.5, 4))
    ax.plot([0, 1], [0, 1], linestyle="--", color="grey", label="perfect calibration")
    ax.plot(points["mean_predicted"], points["fraction_positive"], marker="o", label="improved model")
    ax.set_xlabel("Mean predicted probability")
    ax.set_ylabel("Fraction that were no-shows")
    ax.set_title("Calibration (test set)")
    ax.legend()
    _save(fig, path)


def plot_confusion(operating, path):
    matrix = [[operating["tn"], operating["fp"]], [operating["fn"], operating["tp"]]]
    fig, ax = plt.subplots(figsize=(4.5, 3.8))
    ax.imshow(matrix, cmap="Blues")
    for row in range(2):
        for col in range(2):
            ax.text(col, row, matrix[row][col], ha="center", va="center")
    ax.set_xticks([0, 1], ["Predicted attend", "Predicted no-show"])
    ax.set_yticks([0, 1], ["Attended", "No-show"])
    ax.set_title("Confusion matrix at the chosen threshold")
    _save(fig, path)


def plot_importance(rows, path):
    ordered = sorted(rows, key=lambda row: row["mean_drop_in_pr_auc"])
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.barh([row["feature"] for row in ordered], [row["mean_drop_in_pr_auc"] for row in ordered])
    ax.set_xlabel("Drop in PR-AUC when the feature is shuffled (validation)")
    ax.set_title("Permutation importance")
    _save(fig, path)


def make_all(report, arrays, out_dir):
    out_dir.mkdir(parents=True, exist_ok=True)
    y_test = arrays["y_test"]
    probs = arrays["probs"]
    plot_pr_curves(
        y_test, {"baseline": probs["baseline"], "improved": probs["improved"]}, out_dir / "pr_curves.png"
    )
    plot_calibration(report["test"]["calibration"], out_dir / "calibration.png")
    plot_confusion(report["test"]["operating_point"]["improved"], out_dir / "confusion_matrix.png")
    plot_importance(report["validation"]["permutation_importance"], out_dir / "permutation_importance.png")