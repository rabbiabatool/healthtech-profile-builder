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
import usePageTitle from "@/lib/usePageTitle";

const PAGE_SIZE = 10;

export default function AdminDashboardPage() {
  usePageTitle("Admin dashboard");
  const router = useRouter();
  const [searchInput, setSearchInput] = useState("");
  const [statusInput, setStatusInput] = useState("");
  const [filters, setFilters] = useState({ search: "", status: "", page: 1 });
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const params = new URLSearchParams({ page: String(filters.page), page_size: String(PAGE_SIZE) });
      if (filters.search) params.set("search", filters.search);
      if (filters.status) params.set("status", filters.status);
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
  }, [filters, router]);

  function applyFilters(event) {
    event.preventDefault();
    setLoading(true);
    setFilters({ search: searchInput.trim(), status: statusInput, page: 1 });
  }

  function clearFilters() {
    setSearchInput("");
    setStatusInput("");
    setLoading(true);
    setFilters({ search: "", status: "", page: 1 });
  }

  function goToPage(page) {
    setLoading(true);
    setFilters({ ...filters, page });
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

      <form className="card toolbar" onSubmit={applyFilters} role="search" aria-label="Search profiles">
        <Field
          id="search"
          type="search"
          label="Search by name or email"
          value={searchInput}
          onChange={(event) => setSearchInput(event.target.value)}
          maxLength={100}
          autoComplete="off"
        />
        <Field
          id="status"
          as="select"
          label="Status"
          value={statusInput}
          onChange={(event) => setStatusInput(event.target.value)}
        >
          <option value="">All</option>
          <option value="ACTIVE">Active</option>
          <option value="INACTIVE">Inactive</option>
        </Field>
        <div className="row">
          <button className="btn btn-primary" type="submit">
            Search
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
                <caption className="sr-only">Member health profiles, newest first</caption>
                <thead>
                  <tr>
                    <th scope="col">Member</th>
                    <th scope="col" className="hide-sm">
                      Blood group
                    </th>
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
                      <td className="hide-sm">{row.blood_group || "—"}</td>
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
              <button
                className="btn btn-secondary"
                type="button"
                onClick={() => goToPage(filters.page - 1)}
                disabled={!result.previous || loading}
              >
                Previous
              </button>
              <span>
                Page {filters.page} of {totalPages}
              </span>
              <button
                className="btn btn-secondary"
                type="button"
                onClick={() => goToPage(filters.page + 1)}
                disabled={!result.next || loading}
              >
                Next
              </button>
            </nav>
          </>
        ) : null}

        {result && !loading && result.results.length === 0 ? (
          <div className="card">
            <p style={{ margin: 0 }}>No profiles match your search.</p>
          </div>
        ) : null}
      </section>
    </>
  );
}