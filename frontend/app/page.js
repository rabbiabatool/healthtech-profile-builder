import Link from "next/link";

export const metadata = { title: "Welcome" };

export default function HomePage() {
  return (
    <>
      <section className="hero">
        <h1>Build and manage your health profile</h1>
        <p>
          A demo HealthTech app with two separate sign-in flows: members use secure token cookies, and administrators
          use server-side sessions.
        </p>
      </section>

      <div className="grid">
        <section className="card" aria-labelledby="member-title">
          <h2 id="member-title">For members</h2>
          <p>Create an account to build and edit your own health profile.</p>
          <div className="row">
            <Link className="btn btn-primary" href="/signup">
              Create account
            </Link>
            <Link className="btn btn-secondary" href="/login">
              Log in
            </Link>
          </div>
        </section>

        <section className="card" aria-labelledby="admin-title">
          <h2 id="admin-title">For administrators</h2>
          <p>Admin accounts are created by the system owner. They cannot be self-registered.</p>
          <Link className="btn btn-secondary" href="/admin/login">
            Admin sign in
          </Link>
        </section>
      </div>

      <p className="alert alert-info" style={{ marginTop: "1.5rem" }}>
        Demo only: please enter fictional information, never real health data.
      </p>
    </>
  );
}