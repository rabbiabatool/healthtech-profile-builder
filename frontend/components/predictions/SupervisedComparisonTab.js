"use client";

import { useEffect, useState } from "react";
import { fetchSupervisedComparison } from "../../lib/mlClient";
import styles from "./predictions.module.css";

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

  const { comparison_table, tuning, dataset, disclaimer, feature_importances } = data;

  return (
    <div>
      <aside className={styles.banner} aria-label="Educational disclaimer">
        <strong>Benchmarking Notice:</strong> {disclaimer}
      </aside>

      <section className={styles.card}>
        <h2>Multi-Algorithm Supervised Comparison</h2>
        <p>
          Comparative evaluation of 5 algorithms across identical Stratified Group splits. 
          Dataset: <strong>{dataset?.n_appointments?.toLocaleString()} appointments</strong> across <strong>{dataset?.n_patients?.toLocaleString()} patients</strong> with zero group leakage.
        </p>

        <div className={styles.tableWrapper}>
          <table className={styles.table}>
            <thead>
              <tr>
                <th>Model</th>
                <th>Family</th>
                <th>Train Acc</th>
                <th>Val Acc</th>
                <th>Test Acc</th>
                <th>Precision</th>
                <th>Recall</th>
                <th>F1 Score</th>
                <th>ROC-AUC</th>
                <th>PR-AUC</th>
                <th>Overfit Gap</th>
              </tr>
            </thead>
            <tbody>
              {comparison_table?.map((row) => (
                <tr key={row.model_key}>
                  <td><strong>{row.model_name}</strong></td>
                  <td>{row.family}</td>
                  <td>{(row.train_accuracy * 100).toFixed(1)}%</td>
                  <td>{(row.val_accuracy * 100).toFixed(1)}%</td>
                  <td>{(row.test_accuracy * 100).toFixed(1)}%</td>
                  <td>{row.precision.toFixed(3)}</td>
                  <td>{row.recall.toFixed(3)}</td>
                  <td><strong>{row.f1.toFixed(3)}</strong></td>
                  <td>{row.roc_auc.toFixed(3)}</td>
                  <td>{row.pr_auc.toFixed(3)}</td>
                  <td>
                    <span className={row.overfitting_gap_pct > 10 ? styles.badgeLow : styles.badgeHigh}>
                      {row.overfitting_gap_pct.toFixed(1)}%
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {tuning && (
        <section className={styles.card}>
          <h2>Hyperparameter Tuning Experiment ({tuning.tuned_algorithm})</h2>
          <p>
            <strong>Optimization Strategy:</strong> {tuning.cv_folds}-Fold StratifiedGroupKFold GridSearchCV optimizing for {tuning.scoring_metric.toUpperCase()}.
          </p>
          <div className={styles.facts}>
            <div>
              <dt>Best F1 CV Score</dt>
              <dd><strong>{tuning.best_cv_score?.toFixed(4)}</strong></dd>
            </div>
            <div>
              <dt>Tuned Test F1</dt>
              <dd><strong>{tuning.tuned_test_f1?.toFixed(4)}</strong></dd>
            </div>
            <div>
              <dt>Total Candidates Evaluated</dt>
              <dd>{tuning.total_candidates_evaluated}</dd>
            </div>
          </div>
          <div className={styles.recBox}>
            <strong>Optimal Hyperparameters:</strong>
            <code> {JSON.stringify(tuning.best_params)}</code>
          </div>
        </section>
      )}

      {feature_importances && feature_importances.length > 0 && (
        <section className={styles.card}>
          <h2>Top Predictive Features</h2>
          <p>Features ranked by predictive importance across the tuned model:</p>
          <div className={styles.tableWrapper}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th>Rank</th>
                  <th>Feature</th>
                  <th>Importance Score</th>
                </tr>
              </thead>
              <tbody>
                {feature_importances.slice(0, 5).map((feat, idx) => (
                  <tr key={feat.feature}>
                    <td>#{idx + 1}</td>
                    <td><strong>{feat.feature}</strong></td>
                    <td>{feat.importance.toFixed(4)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </div>
  );
}

