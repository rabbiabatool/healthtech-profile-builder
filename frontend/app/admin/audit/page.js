"use client";

import { useState } from "react";

import AdminBar from "@/components/AdminBar";
import AuditPanel from "@/components/AuditPanel";
import Field from "@/components/Field";
import { AUDIT_ACTIONS, AUDIT_OUTCOMES } from "@/lib/options";
import usePageTitle from "@/lib/usePageTitle";

const BLANK = { action: "", outcome: "", profile_id: "" };

export default function AdminAuditPage() {
  usePageTitle("Audit log");
  const [inputs, setInputs] = useState(BLANK);
  const [applied, setApplied] = useState(BLANK);

  function handleInput(event) {
    setInputs({ ...inputs, [event.target.name]: event.target.value });
  }

  function applyFilters(event) {
    event.preventDefault();
    setApplied({ ...inputs, profile_id: inputs.profile_id.trim() });
  }

  function clearFilters() {
    setInputs(BLANK);
    setApplied(BLANK);
  }

  return (
    <>
      <AdminBar />
      <h1>Audit log</h1>
      <p className="muted">
        A permanent record of profile edits and admin actions. It stores which fields changed, never what they changed to.
      </p>

      <form className="card toolbar" onSubmit={applyFilters} role="search" aria-label="Filter audit events">
        <Field id="action" as="select" label="Event" value={inputs.action} onChange={handleInput}>
          <option value="">All events</option>
          {AUDIT_ACTIONS.map(([value, text]) => (
            <option key={value} value={value}>
              {text}
            </option>
          ))}
        </Field>
        <Field id="outcome" as="select" label="Outcome" value={inputs.outcome} onChange={handleInput}>
          <option value="">Any outcome</option>
          {AUDIT_OUTCOMES.map(([value, text]) => (
            <option key={value} value={value}>
              {text}
            </option>
          ))}
        </Field>
        <Field id="profile_id" type="number" min="1" inputMode="numeric" label="Profile number" value={inputs.profile_id} onChange={handleInput} />
        <div className="row">
          <button className="btn btn-primary" type="submit">
            Apply
          </button>
          <button className="btn btn-secondary" type="button" onClick={clearFilters}>
            Clear
          </button>
        </div>
      </form>

      <AuditPanel key={JSON.stringify(applied)} filters={applied} />
    </>
  );
}