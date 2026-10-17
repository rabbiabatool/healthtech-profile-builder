"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { api, ApiError } from "@/lib/api";

export default function AdminBar() {
  const router = useRouter();
  const [admin, setAdmin] = useState(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const data = await api("/api/admin/me");
        if (!cancelled) setAdmin(data);
      } catch (error) {
        if (cancelled) return;
        if (error instanceof ApiError && (error.status === 401 || error.status === 403)) {
          router.replace("/admin/login");
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [router]);

  async function handleLogout() {
    try {
      await api("/api/admin/logout", { method: "POST" });
    } catch {
      // The session may already be gone; we leave either way.
    }
    router.replace("/admin/login");
  }

  return (
    <div className="bar">
      <p className="muted">
        {admin ? (
          <>
            Signed in as <strong>{admin.full_name}</strong>
          </>
        ) : (
          "Checking your session…"
        )}
      </p>
      <button className="btn btn-secondary" type="button" onClick={handleLogout}>
        Log out
      </button>
    </div>
  );
}