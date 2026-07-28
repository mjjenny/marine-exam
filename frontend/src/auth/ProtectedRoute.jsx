import { Navigate } from "react-router-dom";
import { useAuth } from "./AuthContext.jsx";

// Guards routes that require an approved (optionally admin) account.
export default function ProtectedRoute({ children, requireAdmin = false }) {
  const { user, loading } = useAuth();

  if (loading) return <div className="card">Loading…</div>;
  if (!user) return <Navigate to="/login" replace />;
  if (user.status !== "approved") return <Navigate to="/pending" replace />;
  if (requireAdmin && !user.is_admin) return <Navigate to="/" replace />;

  return children;
}
