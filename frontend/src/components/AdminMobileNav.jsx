import { NavLink, useLocation } from "react-router-dom";
import { useAuth } from "../auth/AuthContext.jsx";

const ADMIN_LINKS = [
  { to: "/admin/approvals", label: "Approvals" },
  { to: "/admin/moderation", label: "Moderation" },
  { to: "/admin/add-diet", label: "Add Diet" },
  { to: "/admin/users", label: "Members" },
];

// Horizontal scrollable admin tab strip — visible only on mobile for admin users.
export default function AdminMobileNav() {
  const { user } = useAuth();
  const { pathname } = useLocation();

  if (!user?.is_admin) return null;
  // Only show when on an admin page.
  if (!pathname.startsWith("/admin")) return null;

  return (
    <nav className="admin-mobile-nav mobile-only" aria-label="Admin">
      {ADMIN_LINKS.map(({ to, label }) => (
        <NavLink
          key={to}
          to={to}
          className={({ isActive }) =>
            `admin-mobile-nav-link${isActive ? " is-active" : ""}`
          }
        >
          {label}
        </NavLink>
      ))}
    </nav>
  );
}
