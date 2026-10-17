export default function StatusBadge({ status }) {
  const active = status === "ACTIVE";
  return <span className={`badge ${active ? "badge-active" : "badge-inactive"}`}>{active ? "Active" : "Inactive"}</span>;
}