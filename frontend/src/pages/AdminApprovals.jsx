import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client.js";

// Admin member-approval queue: list pending signups, approve or reject each.
export default function AdminApprovals() {
  const [users, setUsers] = useState(null);
  const [error, setError] = useState(null);
  const [busyId, setBusyId] = useState(null);

  const load = useCallback(() => {
    setError(null);
    api
      .adminUsers("pending")
      .then(setUsers)
      .catch((e) => setError(e.message));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function act(id, action) {
    setBusyId(id);
    setError(null);
    try {
      await (action === "approve" ? api.approveUser(id) : api.rejectUser(id));
      // Remove the actioned user from the pending list.
      setUsers((prev) => prev.filter((u) => u.id !== id));
    } catch (e) {
      setError(e.message);
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div className="card">
      <p className="crumbs">
        <Link to="/">Home</Link> / Admin / Approvals
      </p>
      <h1>Member approvals</h1>
      <p className="muted">Pending signups awaiting your approval.</p>

      {error && <p className="form-error">{error}</p>}
      {!users && !error && <p>Loading…</p>}
      {users && users.length === 0 && (
        <p className="muted">No pending signups. All caught up.</p>
      )}

      {users && users.length > 0 && (
        <table className="admin-table">
          <thead>
            <tr>
              <th>Email</th>
              <th>Requested</th>
              <th className="col-actions">Actions</th>
            </tr>
          </thead>
          <tbody>
            {users.map((u) => (
              <tr key={u.id}>
                <td>{u.email}</td>
                <td className="muted">
                  {u.created_at ? new Date(u.created_at).toLocaleString() : "—"}
                </td>
                <td className="col-actions">
                  <button
                    className="btn btn-small"
                    disabled={busyId === u.id}
                    onClick={() => act(u.id, "approve")}
                  >
                    Approve
                  </button>
                  <button
                    className="btn btn-small btn-reject"
                    disabled={busyId === u.id}
                    onClick={() => act(u.id, "reject")}
                  >
                    Reject
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
