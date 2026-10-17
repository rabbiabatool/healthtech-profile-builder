"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import Alert from "@/components/Alert";
import Field from "@/components/Field";
import PasswordField from "@/components/PasswordField";
import { api, errorMessage, fieldErrors } from "@/lib/api";
import usePageTitle from "@/lib/usePageTitle";

export default function SignupPage() {
  usePageTitle("Create your account");
  const router = useRouter();
  const [form, setForm] = useState({ full_name: "", email: "", password: "" });
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
      await api("/api/auth/signup", { method: "POST", body: form });
      await api("/api/auth/user/login", {
        method: "POST",
        body: { email: form.email, password: form.password },
      });
      router.push("/profile");
    } catch (error) {
      setErrors(fieldErrors(error));
      setFormError(errorMessage(error));
      setBusy(false);
    }
  }

  return (
    <div className="card narrow">
      <h1>Create your account</h1>
      <p className="muted">Use a fictional name and email for this demo.</p>
      <Alert kind="error">{formError}</Alert>

      <form className="form" onSubmit={handleSubmit}>
        <Field
          id="full_name"
          label="Full name"
          value={form.full_name}
          onChange={handleChange}
          error={errors.full_name}
          autoComplete="name"
          maxLength={150}
          required
        />
        <Field
          id="email"
          label="Email"
          type="email"
          value={form.email}
          onChange={handleChange}
          error={errors.email}
          autoComplete="email"
          required
        />
        <PasswordField
          value={form.password}
          onChange={handleChange}
          error={errors.password}
          hint="At least 8 characters. Avoid common passwords and ones similar to your name or email."
          autoComplete="new-password"
          minLength={8}
          maxLength={128}
          required
        />
        <button className="btn btn-primary" type="submit" disabled={busy}>
          {busy ? "Creating account…" : "Create account"}
        </button>
      </form>

      <p style={{ marginTop: "1.25rem", marginBottom: 0 }}>
        Already registered? <Link href="/login">Log in</Link>
      </p>
    </div>
  );
}