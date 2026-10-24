"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import Alert from "@/components/Alert";
import CompletionCard from "@/components/CompletionCard";
import ContactsSection from "@/components/ContactsSection";
import SectionForm from "@/components/SectionForm";
import StatusBadge from "@/components/StatusBadge";
import { api, ApiError, errorMessage, userApi } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import {
  DEMOGRAPHICS_OPTIONAL,
  DEMOGRAPHICS_REQUIRED,
  WELLNESS_OPTIONAL,
  WELLNESS_REQUIRED,
} from "@/lib/sections";
import usePageTitle from "@/lib/usePageTitle";

export default function ProfilePage() {
  usePageTitle("Your profile");
  const router = useRouter();
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [notice, setNotice] = useState("");

  const load = useCallback(async () => {
    try {
      const data = await userApi("/api/profiles/me");
      setProfile(data);
      setLoadError("");
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) {
        router.replace("/login");
      } else {
        setLoadError(errorMessage(error));
      }
    } finally {
      setLoading(false);
    }
  }, [router]);

  useEffect(() => {
    load();
  }, [load]);

  async function handleChanged(message) {
    setNotice(message);
    await load();
  }

  async function handleLogout() {
    try {
      await api("/api/auth/user/logout", { method: "POST" });
    } catch {
      // We leave the page either way.
    }
    router.replace("/login");
  }

  if (loading) return <p role="status">Loading your profile…</p>;
  if (loadError) return <Alert kind="error">{loadError}</Alert>;
  if (!profile) return null;

  const inactive = profile.status !== "ACTIVE";

  return (
    <div className="stack">
      <div className="bar">
        <div>
          <h1>Your health profile</h1>
          <p className="muted" style={{ margin: 0 }}>
            {profile.full_name} · {profile.email}
          </p>
        </div>
        <div className="row">
          <StatusBadge status={profile.status} />
          <button className="btn btn-secondary" type="button" onClick={handleLogout}>
            Log out
          </button>
        </div>
      </div>

      <p className="alert alert-info" style={{ margin: 0 }}>
        Demo only: enter fictional information, never real health data.
      </p>
      {inactive ? (
        <Alert kind="info">This profile has been deactivated by an administrator. You can view it but not edit it.</Alert>
      ) : null}
      <Alert kind="success">{notice}</Alert>

      <CompletionCard completion={profile.completion} />

      <SectionForm
        key={`demographics-${profile.demographics?.updated_at}`}
        id="demographics"
        title="Demographics"
        intro="Basic details about you. All fictional."
        endpoint="/api/profiles/me/demographics"
        requiredFields={DEMOGRAPHICS_REQUIRED}
        optionalFields={DEMOGRAPHICS_OPTIONAL}
        optionalTitle="Optional information (biometrics and more)"
        data={profile.demographics}
        disabled={inactive}
        onSaved={handleChanged}
      />

      <ContactsSection contacts={profile.emergency_contacts} disabled={inactive} onChanged={handleChanged} />

      <SectionForm
        key={`wellness-${profile.wellness?.updated_at}`}
        id="wellness"
        title="Wellness preferences"
        intro="How we may contact you and what you are working towards."
        endpoint="/api/profiles/me/wellness"
        requiredFields={WELLNESS_REQUIRED}
        optionalFields={WELLNESS_OPTIONAL}
        optionalTitle="Optional lifestyle information"
        data={profile.wellness}
        disabled={inactive}
        onSaved={handleChanged}
      />

      <p className="muted">Last updated {formatDateTime(profile.updated_at)}</p>
    </div>
  );
}