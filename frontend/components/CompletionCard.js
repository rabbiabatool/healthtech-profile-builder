import { COMPLETION_STATUSES, labelOf } from "@/lib/options";

export default function CompletionCard({ completion }) {
  const { percent, status, missing } = completion;

  return (
    <section className="card" aria-labelledby="completion-title">
      <h2 id="completion-title">Profile completion</h2>
      <p className="completion-figure">
        <strong>{percent}%</strong> <span className="muted">· {labelOf(COMPLETION_STATUSES, status)}</span>
      </p>
      <progress value={percent} max="100" aria-labelledby="completion-title">
        {percent}%
      </progress>
      {missing.length > 0 ? (
        <>
          <h3>What’s left</h3>
          <ul className="checklist">
            {missing.map((item) => (
              <li key={item.key}>{item.label}</li>
            ))}
          </ul>
        </>
      ) : (
        <p className="alert alert-success" style={{ marginTop: "1rem", marginBottom: 0 }}>
          Everything is filled in.
        </p>
      )}
    </section>
  );
}