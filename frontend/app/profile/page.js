"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import Alert from "@/components/Alert";
import Field from "@/components/Field";
import StatusBadge from "@/components/StatusBadge";
import { api, ApiError, errorMessage, fieldErrors, userApi } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import usePageTitle from "@/lib/usePageTitle";

const BLOOD_GROUPS = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"];

function toForm(profile) {
  return {
    date_of_birth: profile.date_of_birth ?? "",
    blood_group: profile.blood_group ?? "",
    height_cm: profile.height_cm ?? "",
    weight_kg: profile.weight_kg ?? "",
    allergies: profile.allergies ?? "",
    conditions: profile.conditions ?? "",
    emergency_contact: profile.emergency_contact ?? "",
  };
}

function toPayload(form) {
  return {
    ...form,
    date_of_birth: form.date_of_birth || null,
    height_cm: form.height_cm === "" ? null : form.height_cm,
    weight_kg: form.weight_kg === "" ? null : form.weight_kg,
  };
}

export default function ProfilePage() {
  usePageTitle("Your profile");
  const router = useRouter();
  const [profile, setProfile] = useState(null);
  const [form, setForm] = useState(null);
  const [errors, setErrors] = useState({});
  const [formError, setFormError] = useState("");
  const [saved, setSaved] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [loadError, setLoadError] = useState("");

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const data = await userApi("/api/profiles/me");
        if (!cancelled) {
          setProfile(data);
          setForm(toForm(data));
        }
      } catch (error) {
        if (cancelled) return;
        if (error instanceof ApiError && error.status === 401) {
          router.replace("/login");
        } else {
          setLoadError(errorMessage(error));
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [router]);

  function handleChange(event) {
    setSaved(false);
    setForm({ ...form, [event.target.name]: event.target.value });
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setSaving(true);
    setErrors({});
    setFormError("");
    setSaved(false);
    try {
      const data = await userApi("/api/profiles/me", { method: "PATCH", body: toPayload(form) });
      setProfile(data);
      setForm(toForm(data));
      setSaved(true);
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) {
        router.replace("/login");
        return;
      }
      setErrors(fieldErrors(error));
      setFormError(errorMessage(error));
    } finally {
      setSaving(false);
    }
  }

  async function handleLogout() {
    try {
      await api("/api/auth/user/logout", { method: "POST" });
    } catch {
      // Even if the call fails, we leave the page.
    }
    router.replace("/login");
  }

  if (loading) {
    return <p role="status">Loading your profile…</p>;
  }
  if (loadError) {
    return <Alert kind="error">{loadError}</Alert>;
  }
  if (!profile || !form) {
    return null;
  }

  const inactive = profile.status !== "ACTIVE";

  return (
    <>
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

      <div className="card">
        <p className="alert alert-info">Demo only: enter fictional information, never real health data.</p>
        {inactive ? (
          <Alert kind="info">This profile has been deactivated by an administrator. You can view it but not edit it.</Alert>
        ) : null}
        <Alert kind="error">{formError}</Alert>
        <Alert kind="success">{saved ? "Profile saved." : ""}</Alert>

        <form className="form" onSubmit={handleSubmit}>
          <fieldset disabled={inactive || saving} className="form">
            <legend className="sr-only">Health profile details</legend>
            <div className="form-grid">
              <Field
                id="date_of_birth"
                label="Date of birth"
                type="date"
                value={form.date_of_birth}
                onChange={handleChange}
                error={errors.date_of_birth}
              />
              <Field
                id="blood_group"
                as="select"
                label="Blood group"
                value={form.blood_group}
                onChange={handleChange}
                error={errors.blood_group}
              >
                <option value="">Not set</option>
                {BLOOD_GROUPS.map((group) => (
                  <option key={group} value={group}>
                    {group}
                  </option>
                ))}
              </Field>
              <Field
                id="height_cm"
                label="Height (cm)"
                type="number"
                inputMode="decimal"
                step="0.1"
                min="30"
                max="272"
                value={form.height_cm}
                onChange={handleChange}
                error={errors.height_cm}
              />
              <Field
                id="weight_kg"
                label="Weight (kg)"
                type="number"
                inputMode="decimal"
                step="0.1"
                min="2"
                max="650"
                value={form.weight_kg}
                onChange={handleChange}
                error={errors.weight_kg}
              />
            </div>
            <Field
              id="allergies"
              as="textarea"
              label="Allergies"
              hint="Fictional notes only."
              value={form.allergies}
              onChange={handleChange}
              error={errors.allergies}
            />
            <Field
              id="conditions"
              as="textarea"
              label="Conditions"
              hint="Fictional notes only."
              value={form.conditions}
              onChange={handleChange}
              error={errors.conditions}
            />
            <Field
              id="emergency_contact"
              label="Emergency contact"
              value={form.emergency_contact}
              onChange={handleChange}
              error={errors.emergency_contact}
              maxLength={100}
            />
            {inactive ? null : (
              <button className="btn btn-primary" type="submit">
                {saving ? "Saving…" : "Save changes"}
              </button>
            )}
          </fieldset>
        </form>
        <p className="muted" style={{ margin: "1.25rem 0 0" }}>
          Last updated {formatDateTime(profile.updated_at)}
        </p>
      </div>
    </>
  );
}