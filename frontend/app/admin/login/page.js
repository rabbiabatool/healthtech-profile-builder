"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import Alert from "@/components/Alert";
import Field from "@/components/Field";
import PasswordField from "@/components/PasswordField";
import { api, errorMessage, fieldErrors, setCsrfToken } from "@/lib/api";
import usePageTitle from "@/lib/usePageTitle";

export default function AdminLoginPage() {
  usePageTitle("Administrator sign in");
  const router = useRouter();
  const [form, setForm] = useState({ email: "", password: "" });
  const [errors, setErrors] = useState({});
  const [formError, setFormError] = useState("");
  const [busy, setBusy] = useState(false);

  function handleChange(event) {
    setForm({ ...form, [event.target.name]: event.target.value });
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setBusy(true);
    setErrors({});
    setFormError("");
    try {
      const data = await api("/api/admin/login", { method: "POST", body: form });
      setCsrfToken(data.csrfToken);
      router.push("/admin");
    } catch (error) {
      setErrors(fieldErrors(error));
      setFormError(errorMessage(error));
      setBusy(false);
    }
  }

  return (
    <div className="card narrow">
      <h1>Administrator sign in</h1>
      <p className="muted">Admin accounts are created by the system owner and cannot be registered here.</p>
      <Alert kind="error">{formError}</Alert>

      <form className="form" onSubmit={handleSubmit}>
        <Field
          id="email"
          label="Email"
          type="email"
          value={form.email}
          onChange={handleChange}
          error={errors.email}
          autoComplete="username"
          required
        />
        <PasswordField
          value={form.password}
          onChange={handleChange}
          error={errors.password}
          autoComplete="current-password"
          required
        />
        <button className="btn btn-primary" type="submit" disabled={busy}>
          {busy ? "Signing in…" : "Sign in"}
        </button>
      </form>

      <p style={{ marginTop: "1.25rem", marginBottom: 0 }}>
        Not an administrator? <Link href="/login">Member log in</Link>
      </p>
    </div>
  );
}