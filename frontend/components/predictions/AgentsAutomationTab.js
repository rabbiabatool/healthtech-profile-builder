"use client";

import { useEffect, useState } from "react";
import {
  executeAgentWorkflow,
  fetchAgentTools,
  fetchBackgroundJobs,
  fetchModelMonitoring,
  submitBackgroundTask,
} from "../../lib/mlClient";
import styles from "./predictions.module.css";

const PRESET_WORKFLOWS = [
  {
    label: "📅 Book Cardiology Appointment",
    query: "I want to book an appointment with cardiology next week",
  },
  {
    label: "📊 Predict Risk & Match Persona",
    query: "Evaluate attendance risk and persona for this patient",
  },
  {
    label: "📖 Search Specialist Cancellation Rules",
    query: "What is the cancellation policy for specialist appointments?",
  },
];

export default function AgentsAutomationTab() {
  const [query, setQuery] = useState("");
  const [workflowState, setWorkflowState] = useState(null);
  const [isRunning, setIsRunning] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");
  const [isUnauthorized, setIsUnauthorized] = useState(false);

  const [tools, setTools] = useState([]);
  const [jobs, setJobs] = useState([]);
  const [monitoring, setMonitoring] = useState(null);
  const [isSubmittingJob, setIsSubmittingJob] = useState(false);

  useEffect(() => {
    loadToolsAndTelemetry();
  }, []);

  async function loadToolsAndTelemetry() {
    try {
      const results = await Promise.allSettled([
        fetchAgentTools(),
        fetchBackgroundJobs(),
        fetchModelMonitoring(),
      ]);

      const toolsRes = results[0].status === "fulfilled" ? results[0].value : null;
      const jobsRes = results[1].status === "fulfilled" ? results[1].value : null;
      const monRes = results[2].status === "fulfilled" ? results[2].value : null;

      if (toolsRes?.status === 401 || jobsRes?.status === 401 || monRes?.status === 401) {
        setIsUnauthorized(true);
      } else {
        setIsUnauthorized(false);
      }

      if (toolsRes?.data?.tools) setTools(toolsRes.data.tools);
      if (jobsRes?.data?.jobs) setJobs(jobsRes.data.jobs);
      if (monRes?.data) setMonitoring(monRes.data);
    } catch {
      // Gracefully handle any unexpected errors
    }
  }

  async function handleRunWorkflow(promptQuery, confirmed = false, idemKey = null) {
    const q = promptQuery || query;
    if (!q.trim()) return;

    setIsRunning(true);
    setErrorMsg("");
    try {
      const res = await executeAgentWorkflow(q, confirmed, idemKey);
      if (res.status === 200 && res.data) {
        setWorkflowState(res.data);
      } else if (res.status === 401) {
        setIsUnauthorized(true);
        setErrorMsg("Authentication required. Please sign in as a Member or Admin.");
      } else {
        setErrorMsg(res.data?.detail || res.error || "Agent workflow execution failed.");
      }
    } catch (err) {
      setErrorMsg("Network error executing agent workflow.");
    } finally {
      setIsRunning(false);
      loadToolsAndTelemetry();
    }
  }

  async function handleTriggerJob(jobType) {
    setIsSubmittingJob(true);
    try {
      const res = await submitBackgroundTask(jobType, { cohort_size: 50 });
      if (res.status === 401) {
        setIsUnauthorized(true);
      }
      await loadToolsAndTelemetry();
    } catch {
      // Graceful fallback
    } finally {
      setIsSubmittingJob(false);
    }
  }

  return (
    <div className={styles.tabContent}>
      <header className={styles.sectionHeader}>
        <h3>🤖 Controlled AI Agents, Multi-Step Planner & Task Automation</h3>
        <p>
          Stateful multi-tool agents combining verified document retrieval, supervised ML risk estimation,
          asynchronous background task queues, and statistical model drift monitoring.
        </p>
      </header>

      {isUnauthorized && (
        <div
          role="alert"
          style={{
            background: "#eff6ff",
            color: "#1e40af",
            border: "1px solid #bfdbfe",
            padding: "12px 16px",
            borderRadius: "6px",
            marginBottom: "16px",
            fontSize: "0.9rem",
          }}
        >
          ℹ️ <strong>Authentication Notice:</strong> You are currently not signed in. Log in as a{" "}
          <strong>Member</strong> or <strong>Admin</strong> to execute live workflows and submit background jobs.
        </div>
      )}

      {/* ─── 1. Multi-Step Workflow Runner ─── */}
      <section className={styles.comparisonCard}>
        <h4>1. Multi-Step Stateful Agent Workflow</h4>
        <p className={styles.neutralMeta}>
          Executes the complete <code>Plan → Tool Selection → Validation → Execution → Response</code> loop
          with server-side authorization and human-in-the-loop write gates.
        </p>

        <div className={styles.presetRow}>
          <span>Example Workflows:</span>
          {PRESET_WORKFLOWS.map((pw) => (
            <button
              key={pw.label}
              type="button"
              className={styles.button}
              onClick={() => {
                setQuery(pw.query);
                handleRunWorkflow(pw.query, false);
              }}
              disabled={isRunning}
            >
              {pw.label}
            </button>
          ))}
        </div>

        <div style={{ marginTop: "12px", display: "flex", gap: "8px" }}>
          <input
            type="text"
            className={styles.input}
            style={{ flex: 1 }}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Enter workflow query (e.g. 'Book cardiology appointment next week')..."
            disabled={isRunning}
          />
          <button
            type="button"
            className={styles.primaryButton}
            onClick={() => handleRunWorkflow(query, false)}
            disabled={isRunning || !query.trim()}
          >
            {isRunning ? "Executing Steps..." : "Run Workflow"}
          </button>
        </div>

        {errorMsg && (
          <div role="alert" className={styles.errorSummary} style={{ marginTop: "12px" }}>
            {errorMsg}
          </div>
        )}

        {/* Workflow Execution Result */}
        {workflowState && (
          <div style={{ marginTop: "16px", background: "#f8fafc", padding: "16px", borderRadius: "8px", border: "1px solid #e2e8f0" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <strong>Workflow ID: <code>{workflowState.workflow_id}</code></strong>
              <span className={styles.metricBadge}>
                Status: {workflowState.is_completed ? "COMPLETED" : "NEEDS_CONFIRMATION"}
              </span>
            </div>

            {/* Answer Display */}
            {workflowState.final_response?.answer && (
              <div style={{ margin: "12px 0", padding: "10px", background: "#ffffff", borderRadius: "6px", borderLeft: "4px solid #3b82f6" }}>
                <strong>Agent Response:</strong>
                <p style={{ margin: "4px 0 0 0" }}>{workflowState.final_response.answer}</p>
              </div>
            )}

            {/* Human Confirmation Gate for Write Tool */}
            {workflowState.requires_human_confirmation && (
              <div style={{ margin: "12px 0", padding: "12px", background: "#fffbeb", borderRadius: "6px", border: "1px solid #fde68a" }}>
                <strong style={{ color: "#92400e" }}>⚠️ Explicit Human Confirmation Required:</strong>
                <p style={{ margin: "6px 0", color: "#78350f" }}>{workflowState.confirmation_prompt}</p>
                <div style={{ display: "flex", gap: "8px", marginTop: "8px" }}>
                  <button
                    type="button"
                    className={styles.primaryButton}
                    style={{ background: "#059669" }}
                    onClick={() =>
                      handleRunWorkflow(
                        workflowState.user_query,
                        true,
                        workflowState.pending_draft?.idempotency_key
                      )
                    }
                    disabled={isRunning}
                  >
                    ✅ Confirm & Schedule Appointment
                  </button>
                  <button
                    type="button"
                    className={styles.button}
                    onClick={() => setWorkflowState(null)}
                  >
                    Reject Write
                  </button>
                </div>
              </div>
            )}

            {/* Step-by-Step Execution Traces */}
            <h5 style={{ margin: "14px 0 8px 0" }}>Step-by-Step Execution Trace:</h5>
            <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
              {workflowState.traces?.map((trace, idx) => (
                <div
                  key={idx}
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    padding: "6px 10px",
                    background: "#ffffff",
                    borderRadius: "4px",
                    fontSize: "0.85rem",
                    border: "1px solid #cbd5e1",
                  }}
                >
                  <div>
                    <span style={{ fontWeight: 600, color: "#1e293b", marginRight: "8px" }}>
                      Step {trace.step_number} [{trace.phase.toUpperCase()}]
                    </span>
                    {trace.tool_name && <code>{trace.tool_name}</code>}
                    <span style={{ color: "#475569", marginLeft: "8px" }}>{trace.details}</span>
                  </div>
                  <div style={{ color: "#64748b" }}>
                    <span>{trace.status.toUpperCase()}</span>
                    {trace.latency_ms > 0 && <span style={{ marginLeft: "8px" }}>({trace.latency_ms} ms)</span>}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </section>

      {/* ─── 2. Background Task Queue & Safe Retries ─── */}
      <section className={styles.comparisonCard} style={{ marginTop: "20px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <h4>2. Asynchronous Background Task Queue</h4>
          <div style={{ display: "flex", gap: "8px" }}>
            <button
              type="button"
              className={styles.button}
              onClick={() => handleTriggerJob("document_indexing")}
              disabled={isSubmittingJob}
            >
              🔄 Trigger Document Re-Indexing
            </button>
            <button
              type="button"
              className={styles.button}
              onClick={() => handleTriggerJob("batch_predictions")}
              disabled={isSubmittingJob}
            >
              ⚡ Run Batch ML Predictions (N=50)
            </button>
          </div>
        </div>
        <p className={styles.neutralMeta}>
          Executes long-running tasks asynchronously with transient retry backoff and state tracking.
        </p>

        <div style={{ overflowX: "auto", marginTop: "10px" }}>
          <table className={styles.comparisonTable}>
            <thead>
              <tr>
                <th>Job ID</th>
                <th>Job Type</th>
                <th>Status</th>
                <th>Retries</th>
                <th>Duration</th>
                <th>Result Summary</th>
              </tr>
            </thead>
            <tbody>
              {jobs.length === 0 ? (
                <tr>
                  <td colSpan={6} style={{ textAlign: "center", color: "#64748b" }}>
                    No background tasks logged. Click a button above to submit an async job.
                  </td>
                </tr>
              ) : (
                jobs.slice(0, 5).map((job) => (
                  <tr key={job.job_id}>
                    <td><code>{job.job_id}</code></td>
                    <td>{job.job_type}</td>
                    <td>
                      <span
                        className={styles.metricBadge}
                        style={{
                          background: job.status === "succeeded" ? "#d1fae5" : "#fee2e2",
                          color: job.status === "succeeded" ? "#065f46" : "#991b1b",
                        }}
                      >
                        {job.status.toUpperCase()}
                      </span>
                    </td>
                    <td>{job.retry_count} / {job.max_retries}</td>
                    <td>{job.duration_ms} ms</td>
                    <td>
                      {job.result
                        ? job.job_type === "document_indexing"
                          ? `Indexed ${job.result.total_chunks_indexed} chunks`
                          : `Mean risk: ${job.result.mean_no_show_risk} (${job.result.high_risk_count} high-risk)`
                        : job.error || "Processing..."}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </section>

      {/* ─── 3. Synthetic Model Drift Telemetry ─── */}
      {monitoring && (
        <section className={styles.comparisonCard} style={{ marginTop: "20px" }}>
          <h4>3. Statistical Model Drift Monitoring & Latency Telemetry</h4>
          <p className={styles.neutralMeta}>
            Compares live prediction distributions against baseline validation data using the{" "}
            <strong>Two-Sample Kolmogorov-Smirnov (KS) test</strong>.
          </p>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "12px", margin: "14px 0" }}>
            <div style={{ padding: "12px", background: "#f8fafc", borderRadius: "6px", border: "1px solid #e2e8f0" }}>
              <div style={{ fontSize: "0.8rem", color: "#64748b" }}>KS Test Statistic (D)</div>
              <div style={{ fontSize: "1.3rem", fontWeight: "bold" }}>{monitoring.drift_analysis.ks_statistic}</div>
              <div style={{ fontSize: "0.75rem", color: "#64748b" }}>p-value: {monitoring.drift_analysis.p_value}</div>
            </div>

            <div style={{ padding: "12px", background: "#f8fafc", borderRadius: "6px", border: "1px solid #e2e8f0" }}>
              <div style={{ fontSize: "0.8rem", color: "#64748b" }}>Drift Status</div>
              <div
                style={{
                  fontSize: "1.1rem",
                  fontWeight: "bold",
                  color: monitoring.drift_analysis.drift_detected ? "#b91c1c" : "#047857",
                }}
              >
                {monitoring.drift_analysis.drift_severity}
              </div>
              <div style={{ fontSize: "0.75rem", color: "#64748b" }}>
                Baseline Mean: {monitoring.drift_analysis.baseline_sample_mean} | Current: {monitoring.drift_analysis.current_sample_mean}
              </div>
            </div>

            <div style={{ padding: "12px", background: "#f8fafc", borderRadius: "6px", border: "1px solid #e2e8f0" }}>
              <div style={{ fontSize: "0.8rem", color: "#64748b" }}>Inference Latency</div>
              <div style={{ fontSize: "1.3rem", fontWeight: "bold" }}>p50: {monitoring.latency_percentiles.p50_ms} ms</div>
              <div style={{ fontSize: "0.75rem", color: "#64748b" }}>p95: {monitoring.latency_percentiles.p95_ms} ms</div>
            </div>
          </div>

          <p style={{ fontSize: "0.78rem", color: "#64748b", fontStyle: "italic", margin: "8px 0 0 0" }}>
            {monitoring.operational_disclaimer}
          </p>
        </section>
      )}
    </div>
  );
}

