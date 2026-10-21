"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import AdminBar from "@/components/AdminBar";
import Alert from "@/components/Alert";
import Field from "@/components/Field";
import StatusBadge from "@/components/StatusBadge";
import { api, ApiError, errorMessage } from "@/lib/api";
import { formatDate } from "@/lib/format";
import { COMPLETION_STATUSES, ORDERINGS, PROFILE_STATUSES, labelOf } from "@/lib/options";
import usePageTitle from "@/lib/usePageTitle";

const PAGE_SIZE = 10;
const BLANK = { search: "", status: "", completion_status: "", ordering: "-created_at" };

export default function AdminDashboardPage() {
  usePageTitle("Admin dashboard");
  const router = useRouter();
  const [inputs, setInputs] = useState(BLANK);
  const [applied, setApplied] = useState({ ...BLANK, page: 1 });
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const params = new URLSearchParams({ page: String(applied.page), page_size: String(PAGE_SIZE) });
      for (const key of ["search", "status", "completion_status", "ordering"]) {
        if (applied[key]) params.set(key, applied[key]);
      }
      try {
        const data = await api(`/api/admin/profiles?${params}`);
        if (!cancelled) {
          setResult(data);
          setError("");
        }
      } catch (err) {
        if (cancelled) return;
        if (err instanceof ApiError && (err.status === 401 || err.status === 403)) {
          router.replace("/admin/login");
          return;
        }
        setError(errorMessage(err));
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [applied, router]);

  function handleInput(event) {
    setInputs({ ...inputs, [event.target.name]: event.target.value });
  }

  function applyFilters(event) {
    event.preventDefault();
    setLoading(true);
    setApplied({ ...inputs, search: inputs.search.trim(), page: 1 });
  }

  function clearFilters() {
    setInputs(BLANK);
    setLoading(true);
    setApplied({ ...BLANK, page: 1 });
  }

  function goToPage(page) {
    setLoading(true);
    setApplied({ ...applied, page });
  }

  const totalPages = result ? Math.max(1, Math.ceil(result.count / PAGE_SIZE)) : 1;
  const summary = loading
    ? "Loading profiles…"
    : result
      ? `${result.count} profile${result.count === 1 ? "" : "s"} found`
      : "";

  return (
    <>
      <AdminBar />
      <h1>Member profiles</h1>

      <form className="card toolbar" onSubmit={applyFilters} role="search" aria-label="Search and filter profiles">
        <Field id="search" type="search" label="Search by name or email" value={inputs.search} onChange={handleInput} maxLength={100} autoComplete="off" />
        <Field id="status" as="select" label="Profile status" value={inputs.status} onChange={handleInput}>
          <option value="">All</option>
          {PROFILE_STATUSES.map(([value, text]) => (
            <option key={value} value={value}>
              {text}
            </option>
          ))}
        </Field>
        <Field id="completion_status" as="select" label="Completion" value={inputs.completion_status} onChange={handleInput}>
          <option value="">All</option>
          {COMPLETION_STATUSES.map(([value, text]) => (
            <option key={value} value={value}>
              {text}
            </option>
          ))}
        </Field>
        <Field id="ordering" as="select" label="Sort by" value={inputs.ordering} onChange={handleInput}>
          {ORDERINGS.map(([value, text]) => (
            <option key={value} value={value}>
              {text}
            </option>
          ))}
        </Field>
        <div className="row">
          <button className="btn btn-primary" type="submit">
            Apply
          </button>
          <button className="btn btn-secondary" type="button" onClick={clearFilters}>
            Clear
          </button>
        </div>
      </form>

      <section aria-labelledby="results-heading" aria-busy={loading}>
        <h2 id="results-heading" className="sr-only">
          Results
        </h2>
        <Alert kind="error">{error}</Alert>
        <p role="status" className="muted">
          {summary}
        </p>

        {result && result.results.length > 0 ? (
          <>
            <div className="table-wrap">
              <table>
                <caption className="sr-only">Member profiles</caption>
                <thead>
                  <tr>
                    <th scope="col">Member</th>
                    <th scope="col">Completion</th>
                    <th scope="col">Status</th>
                    <th scope="col" className="hide-sm">
                      Created
                    </th>
                    <th scope="col">
                      <span className="sr-only">Actions</span>
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {result.results.map((row) => (
                    <tr key={row.id}>
                      <td>
                        <strong>{row.full_name}</strong>
                        <br />
                        <span className="muted">{row.email}</span>
                      </td>
                      <td>
                        <div className="mini-progress">
                          <progress value={row.completion_percent} max="100" aria-label={`Completion for ${row.full_name}`}>
                            {row.completion_percent}%
                          </progress>
                          <span>
                            {row.completion_percent}% <span className="sr-only">{labelOf(COMPLETION_STATUSES, row.completion_status)}</span>
                          </span>
                        </div>
                      </td>
                      <td>
                        <StatusBadge status={row.status} />
                      </td>
                      <td className="hide-sm">{formatDate(row.created_at)}</td>
                      <td>
                        <Link className="btn btn-secondary btn-small" href={`/admin/profiles/${row.id}`}>
                          View<span className="sr-only"> {row.full_name}</span>
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <nav className="pager" aria-label="Pagination">
              <button className="btn btn-secondary" type="button" onClick={() => goToPage(applied.page - 1)} disabled={!result.previous || loading}>
                Previous
              </button>
              <span>
                Page {applied.page} of {totalPages}
              </span>
              <button className="btn btn-secondary" type="button" onClick={() => goToPage(applied.page + 1)} disabled={!result.next || loading}>
                Next
              </button>
            </nav>
          </>
        ) : null}

        {result && !loading && result.results.length === 0 ? (
          <div className="card">
            <p style={{ margin: 0 }}>No profiles match your filters.</p>
          </div>
        ) : null}
      </section>
    </>
  );
}