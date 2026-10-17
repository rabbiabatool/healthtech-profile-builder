export default function Field({ id, label, hint, error, as = "input", children, ...controlProps }) {
  const Control = as;
  const describedBy =
    [hint ? `${id}-hint` : null, error ? `${id}-error` : null].filter(Boolean).join(" ") || undefined;

  return (
    <div className="field">
      <label htmlFor={id}>
        {label}
        {controlProps.required ? (
          <span className="req" aria-hidden="true">
            {" "}
            *
          </span>
        ) : null}
      </label>
      <Control
        id={id}
        name={id}
        aria-describedby={describedBy}
        aria-invalid={error ? "true" : undefined}
        {...controlProps}
      >
        {children}
      </Control>
      {hint ? (
        <p id={`${id}-hint`} className="hint">
          {hint}
        </p>
      ) : null}
      {error ? (
        <p id={`${id}-error`} className="error-text">
          {error}
        </p>
      ) : null}
    </div>
  );
}