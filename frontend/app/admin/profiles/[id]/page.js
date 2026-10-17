"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import AdminBar from "@/components/AdminBar";
import Alert from "@/components/Alert";
import StatusBadge from "@/components/StatusBadge";
import { api, ApiError, errorMessage } from "@/lib/api";
import { formatDateTime, formatDay } from "@/lib/format";
import usePageTitle from "@/lib/usePageTitle";

export default function AdminProfileDetailPage() {
  usePageTitle("Profile details");
  const router = useRouter();
  const { id } = useParams();
  const validId = /^\d+$/.test(String(id));

  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(validId);
  const [notFound, setNotFound] = useState(!validId);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [confirming, setConfirming] = useState(false);
  const [working, setWorking] = useState(false);

  useEffect(() => {
    if (!validId) return undefined;
    let cancelled = false;
    (async () => {
      try {
        const data = await api(`/api/admin/profiles/${id}`);
        if (!cancelled) setProfile(data);
      } catch (err) {
        if (cancelled) return;
        if (err instanceof ApiError && (err.status === 401 || err.status === 403)) {
          router.replace("/admin/login");
        } else if (err instanceof ApiError && err.status === 404) {
          setNotFound(true);
        } else {
          setError(errorMessage(err));
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [id, validId, router]);

  async function changeStatus(action) {
    setWorking(true);
    setError("");
    setMessage("");
    try {
      const data = await api(`/api/admin/profiles/${id}/${action}`, { method: "PATCH" });
      setProfile(data);
      setConfirming(false);
      setMessage(action === "deactivate" ? "Profile deactivated." : "Profile reactivated.");
    } catch (err) {
      if (err instanceof ApiError && (err.status === 401 || err.status === 403) && !String(err.message).includes("CSRF")) {
        router.replace("/admin/login");
        return;
      }
      setError(errorMessage(err));
    } finally {
      setWorking(false);
    }
  }

  const rows = profile
    ? [
        ["Name", profile.full_name],
        ["Email", profile.email],
        ["Account ID", profile.user_id],
        ["Date of birth", formatDay(profile.date_of_birth)],
        ["Blood group", profile.blood_group || "—"],
        ["Height", profile.height_cm ? `${profile.height_cm} cm` : "—"],
        ["Weight", profile.weight_kg ? `${profile.weight_kg} kg` : "—"],
        ["Allergies", profile.allergies || "—"],
        ["Conditions", profile.conditions || "—"],
        ["Emergency contact", profile.emergency_contact || "—"],
        ["Created", formatDateTime(profile.created_at)],
        ["Last updated", formatDateTime(profile.updated_at)],
      ]
    : [];

  return (
    <>
      <AdminBar />
      <p>
        <Link href="/admin">← Back to all profiles</Link>
      </p>

      {loading ? <p role="status">Loading profile…</p> : null}
      <Alert kind="error">{error}</Alert>
      {notFound ? (
        <div className="card">
          <h1>Profile not found</h1>
          <p style={{ marginBottom: 0 }}>This profile doesn’t exist or has been removed.</p>
        </div>
      ) : null}

      {profile ? (
        <div className="card">
          <div className="bar">
            <h1 style={{ margin: 0 }}>{profile.full_name}</h1>
            <StatusBadge status={profile.status} />
          </div>

          <Alert kind="success">{message}</Alert>

          <dl className="details">
            {rows.map(([term, value]) => (
              <div className="detail-row" key={term}>
                <dt>{term}</dt>
                <dd>{value}</dd>
              </div>
            ))}
          </dl>

          {profile.status === "ACTIVE" ? (
            confirming ? (
              <div role="group" aria-label="Confirm deactivation" className="stack">
                <p style={{ margin: 0 }}>
                  Deactivate this profile? The member will still be able to view it but will no longer be able to edit it.
                </p>
                <div className="row">
                  <button className="btn btn-danger" type="button" disabled={working} onClick={() => changeStatus("deactivate")}>
                    {working ? "Deactivating…" : "Yes, deactivate"}
                  </button>
                  <button className="btn btn-secondary" type="button" autoFocus onClick={() => setConfirming(false)}>
                    Cancel
                  </button>
                </div>
              </div>
            ) : (
              <button className="btn btn-danger" type="button" onClick={() => setConfirming(true)}>
                Deactivate profile
              </button>
            )
          ) : (
            <button className="btn btn-primary" type="button" disabled={working} onClick={() => changeStatus("reactivate")}>
              {working ? "Reactivating…" : "Reactivate profile"}
            </button>
          )}
        </div>
      ) : null}
    </>
  );
}