import { NavLink, useLocation } from "react-router-dom";
import { useAuth } from "../auth/AuthContext.jsx";

function IconHome() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" className="bottom-nav-icon">
      <path
        fill="currentColor"
        d="M12 3.2 4 10v10h5.5v-6h5V20H20V10l-8-6.8Z"
      />
    </svg>
  );
}

function IconDashboard() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" className="bottom-nav-icon">
      <path
        fill="currentColor"
        d="M4 4h7v7H4V4Zm9 0h7v5h-7V4ZM4 13h7v7H4v-7Zm9 3h7v4h-7v-4Zm0-3h7v2h-7v-2Z"
      />
    </svg>
  );
}

function IconProfile() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" className="bottom-nav-icon">
      <path
        fill="currentColor"
        d="M12 12a4.5 4.5 0 1 0-4.5-4.5A4.5 4.5 0 0 0 12 12Zm0 2.2c-3.6 0-8 1.8-8 5.4V22h16v-2.4c0-3.6-4.4-5.4-8-5.4Z"
      />
    </svg>
  );
}

function IconLogin() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" className="bottom-nav-icon">
      <path
        fill="currentColor"
        d="M10 4v3h7.2L8 16.2l2.1 2.1L19.3 9.1V16H22V4H10Zm-6 2v14h10v-3H7V9h5V6H4Z"
      />
    </svg>
  );
}

export default function BottomNav() {
  const { user } = useAuth();
  const { pathname } = useLocation();

  const items = user
    ? [
        { to: "/", label: "Home", icon: <IconHome />, end: true },
        ...(user.is_admin
          ? [
              {
                to: "/admin/approvals",
                label: "Dashboard",
                icon: <IconDashboard />,
                end: false,
                activePath: "/admin",
              },
            ]
          : []),
        { to: "/profile", label: "Profile", icon: <IconProfile />, end: true },
      ]
    : [
        { to: "/login", label: "Log in", icon: <IconLogin />, end: true },
        { to: "/signup", label: "Sign up", icon: <IconProfile />, end: true },
      ];

  return (
    <nav className="bottom-nav mobile-only" aria-label="Primary">
      {items.map((item) => (
        <NavLink
          key={item.label}
          to={item.to}
          end={item.end}
          className={({ isActive }) => {
            const active = item.activePath
              ? pathname.startsWith(item.activePath)
              : isActive;
            return `bottom-nav-link${active ? " is-active" : ""}`;
          }}
        >
          {item.icon}
          <span>{item.label}</span>
        </NavLink>
      ))}
    </nav>
  );
}
