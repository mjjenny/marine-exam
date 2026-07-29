import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client.js";

const STATUS_BADGE = {
  approved: "bg-emerald-100 text-emerald-800",
  pending:  "bg-amber-100 text-amber-800",
  rejected: "bg-red-100 text-red-800",
  expired:  "bg-orange-100 text-orange-800",
  revoked:  "bg-red-200 text-red-900",
};

const REVOCABLE = new Set(["approved", "pending", "expired"]);

function fmt(iso) {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString(undefined, {
    year: "numeric", month: "short", day: "numeric",
  });
}

function RevokeModal({ user, onConfirm, onCancel, busy }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="card max-w-sm w-full">
        <h2 className="text-lg font-semibold mb-2">Revoke access?</h2>
        <p className="text-sm text-[var(--muted)] mb-4">
          This will immediately block <strong>{user.email}</strong> from logging
          in. This action cannot be undone from this screen.
        </p>
        <div className="flex gap-2 justify-end">
          <button className="btn btn-secondary btn-small" onClick={onCancel} disabled={busy}>
            Cancel
          </button>
          <button className="btn btn-small btn-reject" onClick={onConfirm} disabled={busy}>
            {busy ? "Revoking…" : "Revoke access"}
          </button>
        </div>
      </div>
    </div>
  );
}

export default function AdminUsers() {
  const [users, setUsers]         = useState(null);
  const [error, setError]         = useState(null);
  const [query, setQuery]         = useState("");
  const [filter, setFilter]       = useState("all");
  const [revokeTarget, setRevokeTarget] = useState(null);
  const [revoking, setRevoking]   = useState(false);

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

  async function confirmRevoke() {
    if (!revokeTarget) return;
    setRevoking(true);
    setError(null);
    try {
      const updated = await api.revokeUser(revokeTarget.id);
      setUsers((prev) => prev.map((u) => (u.id === updated.id ? updated : u)));
      setRevokeTarget(null);
    } catch (e) {
      setError(e.message);
    } finally {
      setRevoking(false);
    }
  }

  return (
    <>
      {revokeTarget && (
        <RevokeModal
          user={revokeTarget}
          onConfirm={confirmRevoke}
          onCancel={() => setRevokeTarget(null)}
          busy={revoking}
        />
      )}

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
            <option value="expired">Expired</option>
            <option value="revoked">Revoked</option>
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
                  <th>Expires</th>
                  <th>Role</th>
                  <th>Status</th>
                  <th className="col-actions">Actions</th>
                </tr>
              </thead>
              <tbody>
                {visible.map((u) => (
                  <tr key={u.id}>
                    <td>{u.email}</td>
                    <td className="muted">{fmt(u.created_at)}</td>
                    <td className="muted">{u.is_admin ? "Never" : fmt(u.expires_at)}</td>
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
                    <td className="col-actions">
                      {!u.is_admin && REVOCABLE.has(u.status) && (
                        <button
                          className="btn btn-small btn-reject"
                          onClick={() => setRevokeTarget(u)}
                        >
                          Revoke
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </>
  );
}
