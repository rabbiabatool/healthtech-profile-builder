"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import Alert from "@/components/Alert";
import Field from "@/components/Field";
import PasswordField from "@/components/PasswordField";
import { api, errorMessage, fieldErrors } from "@/lib/api";
import usePageTitle from "@/lib/usePageTitle";

export default function LoginPage() {
  usePageTitle("Log in");
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
      await api("/api/auth/user/login", { method: "POST", body: form });
      router.push("/profile");
    } catch (error) {
      setErrors(fieldErrors(error));
      setFormError(errorMessage(error));
      setBusy(false);
    }
  }

  return (
    <div className="card narrow">
      <h1>Member log in</h1>
      <Alert kind="error">{formError}</Alert>

      <form className="form" onSubmit={handleSubmit}>
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
          autoComplete="current-password"
          required
        />
        <button className="btn btn-primary" type="submit" disabled={busy}>
          {busy ? "Logging in…" : "Log in"}
        </button>
      </form>

      <p style={{ marginTop: "1.25rem", marginBottom: 0 }}>
        New here? <Link href="/signup">Create an account</Link>
        <br />
        Administrator? <Link href="/admin/login">Admin sign in</Link>
      </p>
    </div>
  );
}