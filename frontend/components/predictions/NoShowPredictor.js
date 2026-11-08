"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";

import { fetchModelInfo, requestPrediction } from "../../lib/mlClient";
import AboutModel from "./AboutModel";
import ResultCard from "./ResultCard";
import styles from "./predictions.module.css";
import {
  DEFAULT_DISCLAIMER,
  FIELD_ORDER,
  HINTS,
  LABELS,
  OPTION_LABELS,
  PRESETS,
  buildPayload,
  splitErrors,
} from "./predictorConfig";

const LOGIN_PATH = "/login";

const COPY = {
  title: "No-show estimate (educational)",
  intro:
    "See how an educational model estimates the chance that a fictional appointment is missed. Nothing you enter is saved, and your own profile is never used.",
};

export default function NoShowPredictor({ mode = "member" }) {
  const [state, setState] = useState("loading");
  const [info, setInfo] = useState(null);
  const [values, setValues] = useState(PRESETS[0].values);
  const [fieldErrors, setFieldErrors] = useState({});
  const [general, setGeneral] = useState([]);
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);
  const resultHeading = useRef(null);

  useEffect(() => {
    let active = true;
    fetchModelInfo()
      .then(async ({ status, data }) => {
        if (!active) return;
        if (status === 200) {
          setInfo(data);
          setState("ready");
        } else if (status === 401) {
          // Check if an admin is currently signed in; if so, show forbidden message
          try {
            const adminRes = await fetch("/api/admin/me", { credentials: "include", cache: "no-store" });
            if (!active) return;
            if (adminRes.status === 200) {
              setState("forbidden");
              return;
            }
          } catch {
            // ignore network check error
          }
          if (active) setState("signin");
        } else if (status === 403) {
          setState("forbidden");
        } else if (status === 503) {
          setState("unavailable");
        } else {
          setState("error");
        }
      })
      .catch(() => active && setState("error"));
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (result && resultHeading.current) resultHeading.current.focus();
  }, [result]);

  function update(name, value) {
    setValues((previous) => ({ ...previous, [name]: value }));
  }

  function clearFeedback() {
    setFieldErrors({});
    setGeneral([]);
    setResult(null);
  }

  function applyPreset(preset) {
    setValues(preset.values);
    clearFeedback();
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setBusy(true);
    setFieldErrors({});
    setGeneral([]);
    try {
      const { status, data } = await requestPrediction(buildPayload(values, info));
      if (status === 200) {
        setResult(data);
      } else {
        setResult(null);
        if (status === 400) {
          const parsed = splitErrors(data, FIELD_ORDER);
          setFieldErrors(parsed.fieldErrors);
          setGeneral(parsed.general.length ? parsed.general : ["Please fix the fields marked below."]);
        } else if (status === 401) {
          setState("signin");
        } else if (status === 403) {
          setGeneral(["Access denied: member session or security token required."]);
        } else if (status === 503) {
          setGeneral([data?.detail ?? "The model is not available right now."]);
        } else {
          setGeneral(["Something went wrong. Please try again."]);
        }
      }
    } catch {
      setGeneral(["Could not reach the server."]);
    } finally {
      setBusy(false);
    }
  }

  function renderField(name) {
    const id = `member-${name}`;
    const hintId = `${id}-hint`;
    const errorId = `${id}-error`;
    const error = fieldErrors[name];
    const schema = info.input_schema;
    const describedBy = error ? `${hintId} ${errorId}` : hintId;
    let hint = HINTS[name] ?? "";
    let control;

    if (name in schema.numeric_ranges) {
      const [low, high] = schema.numeric_ranges[name];
      hint = `${hint} Allowed: ${low} to ${high}.`.trim();
      control = (
        <input
          id={id}
          type="number"
          inputMode={name === "distance_km" ? "decimal" : "numeric"}
          step={name === "distance_km" ? "0.1" : "1"}
          min={low}
          max={high}
          value={values[name]}
          onChange={(event) => update(name, event.target.value)}
          aria-invalid={Boolean(error)}
          aria-describedby={describedBy}
          className={styles.input}
        />
      );
    } else if (name in schema.categorical_values) {
      control = (
        <select
          id={id}
          value={values[name]}
          onChange={(event) => update(name, event.target.value)}
          aria-invalid={Boolean(error)}
          aria-describedby={describedBy}
          className={styles.input}
        >
          {schema.categorical_values[name].map((option) => (
            <option key={option} value={option}>
              {OPTION_LABELS[option] ?? option}
            </option>
          ))}
        </select>
      );
    } else {
      control = (
        <input
          id={id}
          type="checkbox"
          checked={Boolean(values[name])}
          onChange={(event) => update(name, event.target.checked)}
          aria-describedby={describedBy}
          className={styles.checkbox}
        />
      );
    }

    const isCheckbox = !(name in schema.numeric_ranges) && !(name in schema.categorical_values);
    return (
      <div className={styles.field} key={name}>
        {isCheckbox ? (
          <div className={styles.checkRow}>
            {control}
            <label htmlFor={id}>{LABELS[name]}</label>
          </div>
        ) : (
          <>
            <label htmlFor={id} className={styles.label}>{LABELS[name]}</label>
            {control}
          </>
        )}
        <p id={hintId} className={styles.hint}>{hint}</p>
        {error && (
          <p id={errorId} className={styles.error}>
            <strong>Problem:</strong> {error}
          </p>
        )}
      </div>
    );
  }

  const disclaimer = info?.disclaimer ?? DEFAULT_DISCLAIMER;

  return (
    <section className={styles.page} aria-labelledby="ml-page-title">
      <h1 id="ml-page-title">{COPY.title}</h1>
      <p role="note" className={styles.banner}>
        <strong>Educational, synthetic, not clinical.</strong> {disclaimer}
      </p>
      <p>{COPY.intro}</p>

      {state === "loading" && <p>Loading model details…</p>}

      {state === "signin" && (
        <p>
          You need to sign in as a member to use this page. <Link href={LOGIN_PATH}>Go to sign in</Link>.
        </p>
      )}
      {state === "forbidden" && (
        <div role="alert" className={styles.errorSummary}>
          <strong>Access denied.</strong>
          <p>Predictions are available for members only. Administrator accounts cannot access this page.</p>
        </div>
      )}
      {state === "unavailable" && (
        <p role="alert">The model is not available right now. Ask an administrator to rebuild it.</p>
      )}
      {state === "error" && (
        <p role="alert">Could not load the model details. Please reload the page.</p>
      )}

      {state === "ready" && (
        <>
          <div className={styles.presetRow}>
            <span>Try an example:</span>
            {PRESETS.map((preset) => (
              <button key={preset.name} type="button" className={styles.button} onClick={() => applyPreset(preset)}>
                {preset.name}
              </button>
            ))}
          </div>

          <form onSubmit={handleSubmit} noValidate className={styles.form}>
            {general.length > 0 && (
              <div role="alert" className={styles.errorSummary}>
                <strong>The estimate could not be made.</strong>
                <ul>
                  {general.map((message) => (
                    <li key={message}>{message}</li>
                  ))}
                </ul>
              </div>
            )}
            <div className={styles.grid}>{FIELD_ORDER.map(renderField)}</div>
            <div className={styles.actions}>
              <button type="submit" className={styles.primary} disabled={busy}>
                {busy ? "Working…" : "Estimate"}
              </button>
              <button type="button" className={styles.button} onClick={() => { setValues(PRESETS[0].values); clearFeedback(); }}>
                Reset
              </button>
            </div>
          </form>

          <div aria-live="polite">
            {result && <ResultCard result={result} headingRef={resultHeading} />}
          </div>

          <AboutModel info={info} mode={mode} />
        </>
      )}
    </section>
  );
}
