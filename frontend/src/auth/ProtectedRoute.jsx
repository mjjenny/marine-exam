import { Navigate } from "react-router-dom";
import { useAuth } from "./AuthContext.jsx";

const ACTIVE = new Set(["approved"]);

// Guards routes that require an approved (optionally admin) account.
// Expired and revoked users are redirected to /pending which shows a clear message.
export default function ProtectedRoute({ children, requireAdmin = false }) {
  const { user, loading } = useAuth();

  if (loading) return <div className="card">Loading…</div>;
  if (!user) return <Navigate to="/login" replace />;
  if (!ACTIVE.has(user.status)) return <Navigate to="/pending" replace />;
  if (requireAdmin && !user.is_admin) return <Navigate to="/" replace />;

  return children;
}
