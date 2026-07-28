import { useAuth } from "../auth/AuthContext.jsx";

// Holding page for logged-in users whose account is not yet approved.
export default function Pending() {
  const { user, logout } = useAuth();
  const rejected = user?.status === "rejected";

  return (
    <div className="card auth-card">
      <h1>{rejected ? "Account not approved" : "Awaiting approval"}</h1>
      {rejected ? (
        <p>
          Your account request was not approved. If you believe this is a mistake,
          please contact the administrator.
        </p>
      ) : (
        <p>
          Your account (<strong>{user?.email}</strong>) is awaiting administrator
          approval. Once approved, you'll have access to all five subjects. Check back
          shortly.
        </p>
      )}
      <button className="btn btn-secondary" onClick={logout}>
        Log out
      </button>
    </div>
  );
}
