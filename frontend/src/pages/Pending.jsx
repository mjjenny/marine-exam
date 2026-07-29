import { useAuth } from "../auth/AuthContext.jsx";

const MESSAGES = {
  rejected: {
    title: "Account not approved",
    body: "Your account request was not approved. If you believe this is a mistake, please contact the administrator.",
  },
  expired: {
    title: "Membership expired",
    body: "Your 365-day membership has expired. Please contact the administrator to arrange a renewal and regain access.",
  },
  revoked: {
    title: "Access revoked",
    body: "Your account access has been revoked. Please contact the administrator if you believe this is an error.",
  },
};

const DEFAULT = {
  title: "Awaiting approval",
  body: null,
};

export default function Pending() {
  const { user, logout } = useAuth();
  const msg = MESSAGES[user?.status] ?? DEFAULT;

  return (
    <div className="card auth-card">
      <h1>{msg.title}</h1>
      {msg.body ? (
        <p>{msg.body}</p>
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
