"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { api, ApiError } from "@/lib/api";

const LINKS = [
  { href: "/admin", label: "Profiles" },
  { href: "/admin/audit", label: "Audit log" },
];

export default function AdminBar() {
  const router = useRouter();
  const pathname = usePathname();
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

  function isCurrent(href) {
    return pathname === href || (href === "/admin" && pathname.startsWith("/admin/profiles"));
  }

  return (
    <div className="bar">
      <div>
        <p className="muted" style={{ margin: 0 }}>
          {admin ? (
            <>
              Signed in as <strong>{admin.full_name}</strong>
            </>
          ) : (
            "Checking your session…"
          )}
        </p>
        <nav aria-label="Admin sections" className="nav-links">
          {LINKS.map(({ href, label }) => (
            <Link key={href} href={href} aria-current={isCurrent(href) ? "page" : undefined}>
              {label}
            </Link>
          ))}
        </nav>
      </div>
      <button className="btn btn-secondary" type="button" onClick={handleLogout}>
        Log out
      </button>
    </div>
  );
}