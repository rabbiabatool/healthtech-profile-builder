"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import AdminBar from "@/components/AdminBar";
import Alert from "@/components/Alert";
import AuditPanel from "@/components/AuditPanel";
import CompletionCard from "@/components/CompletionCard";
import StatusBadge from "@/components/StatusBadge";
import { api, ApiError, errorMessage } from "@/lib/api";
import { formatDateTime, formatDay } from "@/lib/format";
import {
  ACTIVITY_LEVELS,
  DIET_PREFERENCES,
  GENDERS,
  RELATIONSHIPS,
  REMINDER_CHANNELS,
  labelOf,
} from "@/lib/options";
import usePageTitle from "@/lib/usePageTitle";

function Details({ title, rows }) {
  const id = `details-${title.replace(/\s+/g, "-").toLowerCase()}`;
  return (
    <section className="card" aria-labelledby={id}>
      <h2 id={id}>{title}</h2>
      <dl className="details" style={{ marginBottom: 0 }}>
        {rows.map(([term, value]) => (
          <div className="detail-row" key={term}>
            <dt>{term}</dt>
            <dd>{value}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}

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

  const demographics = profile?.demographics;
  const wellness = profile?.wellness;

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
        <div className="stack">
          <div className="bar" style={{ marginBottom: 0 }}>
            <div>
              <h1 style={{ margin: 0 }}>{profile.full_name}</h1>
              <p className="muted" style={{ margin: 0 }}>
                {profile.email} · account {profile.user_id}
              </p>
            </div>
            <StatusBadge status={profile.status} />
          </div>

          <Alert kind="success">{message}</Alert>
          <p className="alert alert-info" style={{ margin: 0 }}>
            Read-only. Viewing this profile has been recorded in the audit log.
          </p>

          <CompletionCard completion={profile.completion} />

          {demographics ? (
            <Details
              title="Demographics"
              rows={[
                ["Date of birth", formatDay(demographics.date_of_birth)],
                ["Gender", labelOf(GENDERS, demographics.gender)],
                ["Blood group", demographics.blood_group || "—"],
                ["Height", demographics.height_cm ? `${demographics.height_cm} cm` : "—"],
                ["Weight", demographics.weight_kg ? `${demographics.weight_kg} kg` : "—"],
                ["Country", demographics.country || "—"],
                ["Preferred language", demographics.preferred_language || "—"],
              ]}
            />
          ) : null}

          <section className="card" aria-labelledby="admin-contacts-title">
            <h2 id="admin-contacts-title">Emergency contacts</h2>
            {profile.emergency_contacts.length === 0 ? (
              <p style={{ marginBottom: 0 }}>None saved.</p>
            ) : (
              <ul className="plain stack">
                {profile.emergency_contacts.map((contact) => (
                  <li key={contact.id}>
                    <strong>{contact.name}</strong>{" "}
                    {contact.is_primary ? <span className="badge badge-active">Primary</span> : null}
                    <br />
                    <span className="muted">
                      {labelOf(RELATIONSHIPS, contact.relationship)} · {contact.phone || "No phone"}
                      {contact.email ? ` · ${contact.email}` : ""}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </section>

          {wellness ? (
            <Details
              title="Wellness preferences"
              rows={[
                ["Activity level", labelOf(ACTIVITY_LEVELS, wellness.activity_level)],
                ["Diet preference", labelOf(DIET_PREFERENCES, wellness.diet_preference)],
                ["Sleep goal", wellness.sleep_goal_hours ? `${wellness.sleep_goal_hours} hours` : "—"],
                ["Reminder channel", labelOf(REMINDER_CHANNELS, wellness.reminder_channel)],
                ["Wellness goals", wellness.wellness_goals || "—"],
                ["Allergy notes", wellness.allergy_notes || "—"],
                ["Condition notes", wellness.condition_notes || "—"],
              ]}
            />
          ) : null}

          <section className="card" aria-labelledby="timeline-title">
            <h2 id="timeline-title">Audit timeline</h2>
            <AuditPanel profileId={id} />
          </section>

          <p className="muted">
            Created {formatDateTime(profile.created_at)} · Last updated {formatDateTime(profile.updated_at)}
          </p>

          <div className="card">
            <h2>Profile status</h2>
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
        </div>
      ) : null}
    </>
  );
}