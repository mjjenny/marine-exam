import { useNavigate, useLocation } from "react-router-dom";

/** Routes that should not show the on-screen back control (app roots). */
const ROOT_PATHS = new Set([
  "/",
  "/login",
  "/signup",
  "/forgot-password",
  "/reset-password",
  "/pending",
  "/admin/approvals", // admin dashboard root
]);

/**
 * Mobile-only back control for standalone PWA (no browser chrome).
 * Hidden on home / dashboard roots; uses history when possible.
 */
export default function MobileBackButton() {
  const navigate = useNavigate();
  const { pathname } = useLocation();

  if (ROOT_PATHS.has(pathname)) return null;

  function goBack() {
    if (typeof window !== "undefined" && window.history.length > 1) {
      navigate(-1);
    } else {
      navigate("/", { replace: true });
    }
  }

  return (
    <div className="mobile-back-bar mobile-only">
      <button type="button" className="mobile-back-btn" onClick={goBack} aria-label="Go back">
        <svg viewBox="0 0 24 24" className="mobile-back-icon" aria-hidden="true">
          <path
            fill="currentColor"
            d="M15.4 4.6 13.99 3.2 5.2 12l8.79 8.8 1.41-1.4L8.02 12l7.38-7.4Z"
          />
        </svg>
        <span>Back</span>
      </button>
    </div>
  );
}
