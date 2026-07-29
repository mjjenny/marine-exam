import { Link } from "react-router-dom";
import { useAuth } from "../auth/AuthContext.jsx";

function displayName(email) {
  if (!email) return "";
  const local = email.split("@")[0];
  return local
    .split(/[._-]+/)
    .filter(Boolean)
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}

export default function Profile() {
  const { user, logout } = useAuth();
  const name = displayName(user?.email);

  return (
    <div className="profile-page">
      <p className="home-kicker">Account</p>
      <h1 className="home-greeting">{name || "Profile"}</h1>
      <p className="muted">{user?.email}</p>

      <div className="profile-card">
        <dl className="profile-meta">
          <div>
            <dt>Status</dt>
            <dd>{user?.status || "—"}</dd>
          </div>
          <div>
            <dt>Role</dt>
            <dd>{user?.is_admin ? "Admin" : "Member"}</dd>
          </div>
        </dl>

        {user?.is_admin && (
          <div className="profile-admin-links">
            <Link className="btn btn-secondary" to="/admin/approvals">
              Approvals
            </Link>
            <Link className="btn btn-secondary" to="/admin/moderation">
              Moderation
            </Link>
            <Link className="btn btn-secondary" to="/admin/add-diet">
              Add Diet
            </Link>
          </div>
        )}

        <Link className="btn" to="/account">
          My Account
        </Link>

        <button type="button" className="btn btn-ghost profile-logout" onClick={logout}>
          Log out
        </button>
      </div>
    </div>
  );
}
