"use client";

import { useState } from "react";

import Field from "./Field";

export default function PasswordField({ id = "password", label = "Password", ...props }) {
  const [visible, setVisible] = useState(false);

  return (
    <div>
      <Field id={id} label={label} type={visible ? "text" : "password"} {...props} />
      <label className="checkbox">
        <input type="checkbox" checked={visible} onChange={(event) => setVisible(event.target.checked)} />
        Show password
      </label>
    </div>
  );
}