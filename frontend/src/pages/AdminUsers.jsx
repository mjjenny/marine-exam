import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client.js";

const STATUS_BADGE = {
  approved: "bg-emerald-100 text-emerald-800",
  pending:  "bg-amber-100 text-amber-800",
  rejected: "bg-red-100 text-red-800",
};

function fmt(iso) {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString(undefined, {
    year: "numeric", month: "short", day: "numeric",
  });
}

export default function AdminUsers() {
  const [users, setUsers]   = useState(null);
  const [error, setError]   = useState(null);
  const [query, setQuery]   = useState("");
  const [filter, setFilter] = useState("all");

  const load = useCallback(() => {
    setError(null);
    api
      .adminUsers()
      .then(setUsers)
      .catch((e) => setError(e.message));
  }, []);

  useEffect(() => { load(); }, [load]);

  const visible = useMemo(() => {
    if (!users) return [];
    return users.filter((u) => {
      const matchStatus = filter === "all" || u.status === filter;
      const matchQuery  = u.email.toLowerCase().includes(query.toLowerCase());
      return matchStatus && matchQuery;
    });
  }, [users, query, filter]);

  return (
    <div className="card">
      <p className="crumbs">
        <Link to="/">Home</Link> / Admin / Members
      </p>
      <h1>Members</h1>
      <p className="muted">All registered accounts.</p>

      {/* toolbar */}
      <div className="flex flex-wrap gap-3 mt-4 mb-2 items-center">
        <input
          type="search"
          className="flex-1 min-w-[180px] border border-[var(--border)] rounded px-3 py-1.5 bg-[var(--surface-2)] text-[var(--ink)] text-sm focus:outline-none focus:border-[var(--amber-500)]"
          placeholder="Search by email…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <select
          className="border border-[var(--border)] rounded px-2 py-1.5 bg-[var(--surface-2)] text-[var(--ink)] text-sm focus:outline-none focus:border-[var(--amber-500)]"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
        >
          <option value="all">All statuses</option>
          <option value="approved">Approved</option>
          <option value="pending">Pending</option>
          <option value="rejected">Rejected</option>
        </select>
        {users && (
          <span className="text-sm text-[var(--muted)]">
            {visible.length} / {users.length}
          </span>
        )}
      </div>

      {error && <p className="form-error">{error}</p>}
      {!users && !error && <p>Loading…</p>}

      {users && visible.length === 0 && (
        <p className="muted mt-4">No members match your search.</p>
      )}

      {users && visible.length > 0 && (
        <div className="overflow-x-auto mt-2">
          <table className="admin-table">
            <thead>
              <tr>
                <th>Email</th>
                <th>Joined</th>
                <th>Role</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {visible.map((u) => (
                <tr key={u.id}>
                  <td>{u.email}</td>
                  <td className="muted">{fmt(u.created_at)}</td>
                  <td>
                    <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${u.is_admin ? "bg-violet-100 text-violet-800" : "bg-[var(--navy-100)] text-[var(--navy-800)]"}`}>
                      {u.is_admin ? "Admin" : "Member"}
                    </span>
                  </td>
                  <td>
                    <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium capitalize ${STATUS_BADGE[u.status] ?? ""}`}>
                      {u.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
