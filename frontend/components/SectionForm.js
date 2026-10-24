"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import Alert from "@/components/Alert";
import Field from "@/components/Field";
import { ApiError, errorMessage, fieldErrors, userApi } from "@/lib/api";
import { labelOf } from "@/lib/options";

const NULLABLE_TYPES = ["date", "number"];

function isBlank(value) {
  return value === "" || value === null || value === undefined;
}

function initialValues(fields, data) {
  return Object.fromEntries(fields.map((field) => [field.name, data?.[field.name] ?? ""]));
}

function toPayload(fields, values) {
  return Object.fromEntries(
    fields.map((field) => [
      field.name,
      NULLABLE_TYPES.includes(field.type) && values[field.name] === "" ? null : values[field.name],
    ])
  );
}

function display(field, value) {
  if (isBlank(value)) return "—";
  return field.as === "select" ? labelOf(field.options, value) : String(value);
}

export default function SectionForm({
  id,
  title,
  intro,
  endpoint,
  requiredFields,
  optionalFields,
  optionalTitle = "Optional information",
  data,
  disabled,
  onSaved,
}) {
  const router = useRouter();
  const fields = [...requiredFields, ...optionalFields];
  const [editing, setEditing] = useState(false);
  const [values, setValues] = useState(() => initialValues(fields, data));
  const [errors, setErrors] = useState({});
  const [formError, setFormError] = useState("");
  const [busy, setBusy] = useState(false);

  const hasData = fields.some((field) => !isBlank(data?.[field.name]));

  function handleChange(event) {
    setValues({ ...values, [event.target.name]: event.target.value });
  }

  function startEdit() {
    setValues(initialValues(fields, data));
    setErrors({});
    setFormError("");
    setEditing(true);
  }

  function cancelEdit() {
    setEditing(false);
    setErrors({});
    setFormError("");
  }

  async function run(method, body, message) {
    setBusy(true);
    setErrors({});
    setFormError("");
    try {
      await userApi(endpoint, { method, body });
      await onSaved(message);
      setEditing(false);
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) {
        router.replace("/login");
        return;
      }
      setErrors(fieldErrors(error));
      setFormError(errorMessage(error));
    } finally {
      setBusy(false);
    }
  }

  function handleSubmit(event) {
    event.preventDefault();
    run("PATCH", toPayload(fields, values), `${title} saved.`);
  }

  function handleDelete() {
    if (window.confirm(`Delete everything saved in “${title}”? This clears every field in this section.`)) {
      run("DELETE", undefined, `${title} deleted.`);
    }
  }

  function renderFields(list) {
    return (
      <div className="form-grid">
        {list.map(({ name, label, as, options, wide, hint, ...control }) => (
          <div key={name} className={wide ? "span-all" : undefined}>
            <Field
              id={`${id}-${name}`}
              name={name}
              as={as}
              label={label}
              hint={hint}
              error={errors[name]}
              value={values[name]}
              onChange={handleChange}
              {...control}
            >
              {as === "select" ? (
                <>
                  <option value="">Not set</option>
                  {options.map(([value, text]) => (
                    <option key={value} value={value}>
                      {text}
                    </option>
                  ))}
                </>
              ) : undefined}
            </Field>
          </div>
        ))}
      </div>
    );
  }

  function renderSummary(list) {
    return (
      <dl className="details" style={{ marginBottom: 0 }}>
        {list.map((field) => (
          <div className="detail-row" key={field.name}>
            <dt>{field.label}</dt>
            <dd>{display(field, data?.[field.name])}</dd>
          </div>
        ))}
      </dl>
    );
  }

  return (
    <section className="card" aria-labelledby={`${id}-title`}>
      <h2 id={`${id}-title`}>{title}</h2>
      <p className="muted">{intro}</p>
      <Alert kind="error">{formError}</Alert>

      {editing ? (
        <form className="form" onSubmit={handleSubmit}>
          <fieldset disabled={busy} className="form">
            <legend className="sr-only">{title}</legend>
            <h3>Needed for 100% completion</h3>
            {renderFields(requiredFields)}
            <h3>{optionalTitle}</h3>
            <p className="muted" style={{ margin: 0 }}>
              Not needed for completion. Add what you like, or leave it blank.
            </p>
            {renderFields(optionalFields)}
            <div className="row">
              <button className="btn btn-primary" type="submit">
                {busy ? "Saving…" : "Save"}
              </button>
              <button className="btn btn-secondary" type="button" onClick={cancelEdit}>
                Cancel
              </button>
            </div>
          </fieldset>
        </form>
      ) : (
        <>
          <h3>Needed for 100% completion</h3>
          {renderSummary(requiredFields)}
          <h3>{optionalTitle}</h3>
          {renderSummary(optionalFields)}
          {disabled ? null : (
            <div className="row" style={{ marginTop: "1.25rem" }}>
              <button className="btn btn-secondary btn-small" type="button" onClick={startEdit} disabled={busy}>
                {hasData ? "Edit" : "Add details"}
                <span className="sr-only"> {title}</span>
              </button>
              {hasData ? (
                <button className="btn btn-danger btn-small" type="button" onClick={handleDelete} disabled={busy}>
                  Delete<span className="sr-only"> {title}</span>
                </button>
              ) : null}
            </div>
          )}
        </>
      )}
    </section>
  );
}