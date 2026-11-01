import styles from "./predictions.module.css";
import { asPercent } from "./predictorConfig";

export default function AboutModel({ info, mode }) {
  const test = info.metrics_summary?.test;
  const dummy = info.metrics_summary?.test_dummy;
  const cuts = info.risk_band_cutpoints;

  return (
    <details className={styles.about}>
      <summary>About this model</summary>
      <p>{info.model_type}.</p>
      <ul>
        <li>Model version: {info.model_version}</li>
        <li>
          Trained on {info.rows.toLocaleString()} fictional appointments. About{" "}
          {asPercent(info.class_balance)} of them were no-shows.
        </li>
        {test && dummy && (
          <li>
            Accuracy of its ranking (PR-AUC, a score for how well a model finds no-shows): {test.pr_auc} on
            held-out test data, compared with {dummy.pr_auc} for simply guessing the average. The model is
            only modestly better than chance.
          </li>
        )}
        {cuts && (
          <li>
            Risk bands: higher at or above {asPercent(cuts.HIGH)}, middle at or above {asPercent(cuts.MEDIUM)},
            otherwise lower.
          </li>
        )}
      </ul>

      <h3>Limitations</h3>
      <ul>
        {info.limitations.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>

      {mode === "admin" && info.selection_note && (
        <>
          <h3>Why this model was chosen</h3>
          <p>{info.selection_note}</p>
        </>
      )}
    </details>
  );
}