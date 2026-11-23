import styles from "./predictions.module.css";
import { BAND_TEXT, asPercent } from "./predictorConfig";

export default function ResultCard({ result, headingRef }) {
  const band = BAND_TEXT[result.risk_band];
  const inHundred = Math.round(result.probability * 100);

  return (
    <section className={styles.card} aria-labelledby="ml-result-heading">
      <h2 id="ml-result-heading" ref={headingRef} tabIndex={-1}>
        Estimate
      </h2>
      <p className={styles.bigNumber}>About {inHundred} in 100</p>
      <p>
        That is the model&apos;s estimate of how many appointments like this one would be no-shows. It is
        a rough signal, not a prediction about any person.
      </p>
      <p className={styles.bandLine}>
        <strong>Risk band: {band.title}</strong> ({result.risk_band}). {band.text}
      </p>

      {result.input_warnings.length > 0 && (
        <div role="note" className={styles.warning}>
          <strong>Unusual values</strong>
          <ul>
            {result.input_warnings.map((note) => (
              <li key={note}>{note}</li>
            ))}
          </ul>
        </div>
      )}

      <dl className={styles.facts}>
        <div><dt>Model version</dt><dd>{result.model_version}</dd></div>
        <div><dt>Contract version</dt><dd>{result.schema_version}</dd></div>
        <div><dt>Operating threshold</dt><dd>{asPercent(result.threshold)}</dd></div>
      </dl>
      <p className={styles.disclaimer}>{result.disclaimer}</p>
    </section>
  );
}