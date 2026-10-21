"use client";

import { useState } from "react";

import Alert from "@/components/Alert";
import Field from "@/components/Field";
import { errorMessage, fieldErrors, userApi } from "@/lib/api";
import { RELATIONSHIPS, labelOf } from "@/lib/options";

const BASE = "/api/profiles/me/emergency-contacts";
const EMPTY = { name: "", relationship: "OTHER", phone: "", email: "", is_primary: false };

export default function ContactsSection({ contacts, disabled, onChanged }) {
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState(EMPTY);
  const [errors, setErrors] = useState({});
  const [formError, setFormError] = useState("");
  const [listError, setListError] = useState("");
  const [busy, setBusy] = useState(false);

  const full = contacts.length >= 3 && !editing;

  function handleChange(event) {
    const { name, type, checked, value } = event.target;
    setForm({ ...form, [name]: type === "checkbox" ? checked : value });
  }

  function startEdit(contact) {
    setEditing(contact);
    setForm({
      name: contact.name,
      relationship: contact.relationship,
      phone: contact.phone,
      email: contact.email,
      is_primary: contact.is_primary,
    });
    setErrors({});
    setFormError("");
  }

  function resetForm() {
    setEditing(null);
    setForm(EMPTY);
    setErrors({});
    setFormError("");
  }

  async function save(event) {
    event.preventDefault();
    setBusy(true);
    setErrors({});
    setFormError("");
    try {
      if (editing) {
        const body = { name: form.name, relationship: form.relationship, phone: form.phone, email: form.email };
        if (form.is_primary && !editing.is_primary) body.is_primary = true;
        await userApi(`${BASE}/${editing.id}`, { method: "PATCH", body });
        resetForm();
        await onChanged("Contact updated.");
      } else {
        await userApi(BASE, { method: "POST", body: form });
        resetForm();
        await onChanged("Contact added.");
      }
    } catch (error) {
      const found = fieldErrors(error);
      setErrors(found);
      setFormError(found.non_field_errors || errorMessage(error));
    } finally {
      setBusy(false);
    }
  }

  async function act(action, message) {
    setListError("");
    try {
      await action();
      await onChanged(message);
    } catch (error) {
      setListError(fieldErrors(error).is_primary || errorMessage(error));
    }
  }

  function makePrimary(contact) {
    return act(
      () => userApi(`${BASE}/${contact.id}`, { method: "PATCH", body: { is_primary: true } }),
      `${contact.name} is now the primary contact.`
    );
  }

  function remove(contact) {
    if (!window.confirm(`Delete the contact “${contact.name}”?`)) return undefined;
    return act(() => userApi(`${BASE}/${contact.id}`, { method: "DELETE" }), "Contact deleted.");
  }

  return (
    <section className="card" aria-labelledby="contacts-title">
      <h2 id="contacts-title">Emergency contacts</h2>
      <p className="muted">Up to three people. One of them is your primary contact.</p>
      <Alert kind="error">{listError}</Alert>

      {contacts.length === 0 ? (
        <p>You haven’t added a contact yet.</p>
      ) : (
        <ul className="plain stack">
          {contacts.map((contact) => (
            <li key={contact.id} className="contact">
              <div>
                <strong>{contact.name}</strong>{" "}
                {contact.is_primary ? <span className="badge badge-active">Primary</span> : null}
                <br />
                <span className="muted">
                  {labelOf(RELATIONSHIPS, contact.relationship)} · {contact.phone || "No phone yet"}
                  {contact.email ? ` · ${contact.email}` : ""}
                </span>
              </div>
              {disabled ? null : (
                <div className="row">
                  <button className="btn btn-secondary btn-small" type="button" onClick={() => startEdit(contact)}>
                    Edit<span className="sr-only"> {contact.name}</span>
                  </button>
                  {contact.is_primary ? null : (
                    <button className="btn btn-secondary btn-small" type="button" onClick={() => makePrimary(contact)}>
                      Make primary<span className="sr-only"> {contact.name}</span>
                    </button>
                  )}
                  <button className="btn btn-danger btn-small" type="button" onClick={() => remove(contact)}>
                    Delete<span className="sr-only"> {contact.name}</span>
                  </button>
                </div>
              )}
            </li>
          ))}
        </ul>
      )}

      {disabled ? null : full ? (
        <p className="alert alert-info" style={{ marginTop: "1rem", marginBottom: 0 }}>
          You have reached the limit of three contacts. Delete one to add another.
        </p>
      ) : (
        <form className="form" onSubmit={save} style={{ marginTop: "1.25rem" }}>
          <h3>{editing ? `Edit ${editing.name}` : "Add a contact"}</h3>
          <Alert kind="error">{formError}</Alert>
          <div className="form-grid">
            <Field id="contact-name" name="name" label="Name" value={form.name} onChange={handleChange} error={errors.name} maxLength={100} required />
            <Field id="contact-relationship" name="relationship" as="select" label="Relationship" value={form.relationship} onChange={handleChange} error={errors.relationship}>
              {RELATIONSHIPS.map(([value, text]) => (
                <option key={value} value={value}>
                  {text}
                </option>
              ))}
            </Field>
            <Field id="contact-phone" name="phone" type="tel" label="Phone" hint="7 to 15 digits. Digits, spaces, dashes and brackets are fine." value={form.phone} onChange={handleChange} error={errors.phone} autoComplete="off" required />
            <Field id="contact-email" name="email" type="email" label="Email (optional)" value={form.email} onChange={handleChange} error={errors.email} autoComplete="off" />
          </div>
          <label className="checkbox">
            <input type="checkbox" name="is_primary" checked={form.is_primary} disabled={editing?.is_primary} onChange={handleChange} />
            Make this my primary contact
          </label>
          <div className="row">
            <button className="btn btn-primary" type="submit" disabled={busy}>
              {busy ? "Saving…" : editing ? "Save contact" : "Add contact"}
            </button>
            {editing ? (
              <button className="btn btn-secondary" type="button" onClick={resetForm}>
                Cancel
              </button>
            ) : null}
          </div>
        </form>
      )}
    </section>
  );
}