"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import Alert from "@/components/Alert";
import { api, ApiError, cursorOf, errorMessage } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import { ACTOR_ROLES, AUDIT_ACTIONS, AUDIT_OUTCOMES, labelOf } from "@/lib/options";

function detailsOf(row) {
  const { metadata, changed_fields: fields } = row;
  if (metadata.from_status) return `${metadata.from_status} → ${metadata.to_status}`;
  if (metadata.filters_used) return `Filters: ${metadata.filters_used.join(", ")} · ${metadata.result_count} result(s)`;
  if (fields.length) return fields.join(", ");
  return "—";
}

export default function AuditPanel({ profileId = null, filters = {} }) {
  const router = useRouter();
  const [cursor, setCursor] = useState(null);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const filterKey = JSON.stringify(filters);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const params = new URLSearchParams({ page_size: "10" });
      for (const [key, value] of Object.entries(JSON.parse(filterKey))) {
        if (value) params.set(key, value);
      }
      if (cursor) params.set("cursor", cursor);
      const base = profileId ? `/api/admin/profiles/${profileId}/audit-events` : "/api/admin/audit-events";
      try {
        const result = await api(`${base}?${params}`);
        if (!cancelled) {
          setData(result);
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
  }, [profileId, filterKey, cursor, router]);

  function go(url) {
    setLoading(true);
    setCursor(cursorOf(url));
  }

  return (
    <div aria-busy={loading}>
      <Alert kind="error">{error}</Alert>
      <p role="status" className="muted">
        {loading ? "Loading events…" : data && data.results.length === 0 ? "No events found." : ""}
      </p>

      {data && data.results.length > 0 ? (
        <>
          <div className="table-wrap">
            <table>
              <caption className="sr-only">Audit events, newest first</caption>
              <thead>
                <tr>
                  <th scope="col">When</th>
                  <th scope="col">Event</th>
                  <th scope="col" className="hide-sm">
                    Who
                  </th>
                  <th scope="col" className="hide-sm">
                    Profile
                  </th>
                  <th scope="col">Details</th>
                  <th scope="col">Outcome</th>
                </tr>
              </thead>
              <tbody>
                {data.results.map((row) => (
                  <tr key={row.id}>
                    <td>{formatDateTime(row.created_at)}</td>
                    <td>{labelOf(AUDIT_ACTIONS, row.action)}</td>
                    <td className="hide-sm">
                      {labelOf(ACTOR_ROLES, row.actor_role)}
                      {row.actor_id ? ` #${row.actor_id}` : ""}
                    </td>
                    <td className="hide-sm">{row.profile_id ?? "—"}</td>
                    <td>{detailsOf(row)}</td>
                    <td>{labelOf(AUDIT_OUTCOMES, row.outcome)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <nav className="pager" aria-label="Audit log pages">
            <button className="btn btn-secondary" type="button" onClick={() => go(data.previous)} disabled={!data.previous || loading}>
              Newer events
            </button>
            <button className="btn btn-secondary" type="button" onClick={() => go(data.next)} disabled={!data.next || loading}>
              Older events
            </button>
          </nav>
        </>
      ) : null}
    </div>
  );
}