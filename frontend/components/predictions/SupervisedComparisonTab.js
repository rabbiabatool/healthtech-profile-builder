"use client";

import { useEffect, useState } from "react";
import { fetchSupervisedComparison } from "../../lib/mlClient";
import styles from "./predictions.module.css";

const fmt = (val, digits = 3) =>
  val !== undefined && val !== null && !isNaN(val) ? Number(val).toFixed(digits) : "—";

const fmtPct = (val, digits = 1) =>
  val !== undefined && val !== null && !isNaN(val) ? `${(Number(val) * 100).toFixed(digits)}%` : "—";

export default function SupervisedComparisonTab() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchSupervisedComparison()
      .then(({ status, data: resData }) => {
        if (status === 200) {
          setData(resData);
        } else {
          setError(`Failed to load comparison data (status ${status}).`);
        }
      })
      .catch((err) => setError(err.message || "Network error"))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return <div className={styles.card}><p>Loading supervised model comparison benchmark...</p></div>;
  }

  if (error || !data) {
    return (
      <div className={styles.card}>
        <p className={styles.error}>{error || "Unable to display comparison benchmark."}</p>
      </div>
    );
  }

  const { comparison_table, tuning, dataset, disclaimer, models_detail } = data;

  return (
    <div>
      <aside className={styles.banner} aria-label="Educational disclaimer">
        <strong>Benchmarking Notice:</strong> {disclaimer ?? "Educational prototype comparing multiple ML algorithms across identical splits."}
      </aside>

      <section className={styles.card}>
        <h2>Multi-Algorithm Supervised Comparison</h2>
        <p>
          Comparative evaluation of models across identical Stratified Group splits. 
          Dataset: <strong>{dataset?.n_appointments?.toLocaleString() ?? "20,000"} appointments</strong> across <strong>{dataset?.n_patients?.toLocaleString() ?? "2,500"} patients</strong> with zero group leakage.
        </p>

        <div className={styles.tableWrapper}>
          <table className={styles.table}>
            <thead>
              <tr>
                <th>Model</th>
                <th>Precision</th>
                <th>Recall</th>
                <th>F1 Score</th>
                <th>ROC-AUC</th>
                <th>PR-AUC</th>
                <th>Train PR-AUC</th>
                <th>Val PR-AUC</th>
                <th>Overfit Gap (PR)</th>
                <th>Brier Score</th>
              </tr>
            </thead>
            <tbody>
              {comparison_table?.map((row) => {
                const gap = row.train_val_pr_auc_gap ?? (row.train_pr_auc - row.val_pr_auc);
                const isOverfitted = gap > 0.15;
                return (
                  <tr key={row.model_key ?? row.model_name}>
                    <td><strong>{row.model_name}</strong></td>
                    <td>{fmt(row.test_precision ?? row.precision)}</td>
                    <td>{fmt(row.test_recall ?? row.recall)}</td>
                    <td><strong>{fmt(row.test_f1 ?? row.f1)}</strong></td>
                    <td>{fmt(row.test_roc_auc ?? row.roc_auc)}</td>
                    <td><strong>{fmt(row.test_pr_auc ?? row.pr_auc)}</strong></td>
                    <td>{fmt(row.train_pr_auc)}</td>
                    <td>{fmt(row.val_pr_auc)}</td>
                    <td>
                      <span className={isOverfitted ? styles.badgeLow : styles.badgeHigh}>
                        {fmt(gap)}
                      </span>
                    </td>
                    <td>{fmt(row.test_brier, 4)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>

      {tuning && (
        <section className={styles.card}>
          <h2>Hyperparameter Tuning Experiment ({tuning.algorithm ?? "Random Forest"})</h2>
          <p>
            <strong>Optimization Strategy:</strong> {tuning.search_method ?? "GridSearchCV"} using {tuning.cv_strategy ?? "3-Fold StratifiedGroupKFold"} optimizing for {tuning.scoring ?? "PR-AUC"}.
          </p>
          <div className={styles.facts}>
            <div>
              <dt>Best CV PR-AUC Score</dt>
              <dd><strong>{fmt(tuning.best_cv_score, 4)}</strong></dd>
            </div>
            <div>
              <dt>Total Configurations Tested</dt>
              <dd>{tuning.trials?.length ?? 12} candidates</dd>
            </div>
          </div>
          <div className={styles.recBox}>
            <strong>Optimal Hyperparameters:</strong>
            <code> {JSON.stringify(tuning.best_params)}</code>
          </div>
        </section>
      )}

      {models_detail && (
        <section className={styles.card}>
          <h2>Confusion Matrices on Test Split</h2>
          <p>Confusion matrix breakdown (True Negatives, False Positives, False Negatives, True Positives):</p>
          <div className={styles.tableWrapper}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th>Model</th>
                  <th>True Negatives (TN)</th>
                  <th>False Positives (FP)</th>
                  <th>False Negatives (FN)</th>
                  <th>True Positives (TP)</th>
                  <th>Specificity</th>
                </tr>
              </thead>
              <tbody>
                {comparison_table?.map((row) => {
                  const cm = row.confusion_matrix_test ?? {};
                  return (
                    <tr key={`cm-${row.model_key}`}>
                      <td><strong>{row.model_name}</strong></td>
                      <td>{cm.tn?.toLocaleString() ?? "—"}</td>
                      <td>{cm.fp?.toLocaleString() ?? "—"}</td>
                      <td>{cm.fn?.toLocaleString() ?? "—"}</td>
                      <td>{cm.tp?.toLocaleString() ?? "—"}</td>
                      <td>{fmt(row.test_specificity)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </div>
  );
}
