"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import Alert from "@/components/Alert";
import Field from "@/components/Field";
import { ApiError, errorMessage, fieldErrors, userApi } from "@/lib/api";

const NULLABLE_TYPES = ["date", "number"];

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

export default function SectionForm({ id, title, intro, endpoint, fields, data, disabled, onSaved }) {
  const router = useRouter();
  const [values, setValues] = useState(() => initialValues(fields, data));
  const [errors, setErrors] = useState({});
  const [formError, setFormError] = useState("");
  const [busy, setBusy] = useState(false);

  function handleChange(event) {
    setValues({ ...values, [event.target.name]: event.target.value });
  }

  async function run(method, body, message) {
    setBusy(true);
    setErrors({});
    setFormError("");
    try {
      await userApi(endpoint, { method, body });
      await onSaved(message);
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

  function handleClear() {
    if (window.confirm(`Clear everything in “${title}”?`)) {
      run("DELETE", undefined, `${title} cleared.`);
    }
  }

  return (
    <section className="card" aria-labelledby={`${id}-title`}>
      <h2 id={`${id}-title`}>{title}</h2>
      <p className="muted">{intro}</p>
      <Alert kind="error">{formError}</Alert>

      <form className="form" onSubmit={handleSubmit}>
        <fieldset disabled={disabled || busy} className="form">
          <legend className="sr-only">{title}</legend>
          <div className="form-grid">
            {fields.map(({ name, label, as, options, wide, hint, ...control }) => (
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
          {disabled ? null : (
            <div className="row">
              <button className="btn btn-primary" type="submit">
                {busy ? "Saving…" : `Save ${title.toLowerCase()}`}
              </button>
              <button className="btn btn-secondary" type="button" onClick={handleClear}>
                Clear section
              </button>
            </div>
          )}
        </fieldset>
      </form>
    </section>
  );
}