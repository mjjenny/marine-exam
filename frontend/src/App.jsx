import { Routes, Route, Link, useLocation } from "react-router-dom";
import ErrorBoundary from "./components/ErrorBoundary.jsx";
import WireframeBackground from "./components/WireframeBackground.jsx";
import Home from "./pages/Home.jsx";
import Login from "./pages/Login.jsx";
import Signup from "./pages/Signup.jsx";
import ForgotPassword from "./pages/ForgotPassword.jsx";
import ResetPassword from "./pages/ResetPassword.jsx";
import Pending from "./pages/Pending.jsx";
import Subject from "./pages/Subject.jsx";
import Diet from "./pages/Diet.jsx";
import Question from "./pages/Question.jsx";
import Answer from "./pages/Answer.jsx";
import TopicView from "./pages/TopicView.jsx";
import AdminApprovals from "./pages/AdminApprovals.jsx";
import AdminModeration from "./pages/AdminModeration.jsx";
import AdminAddDiet from "./pages/AdminAddDiet.jsx";
import ProtectedRoute from "./auth/ProtectedRoute.jsx";
import BottomNav from "./components/BottomNav.jsx";
import Profile from "./pages/Profile.jsx";
import { useAuth } from "./auth/AuthContext.jsx";

function HeaderNav() {
  const { user, logout } = useAuth();
  return (
    <nav className="header-nav" aria-label="Desktop">
      <Link to="/" className="header-nav-link">
        Home
      </Link>
      {user ? (
        <>
          {user.is_admin && (
            <>
              <Link to="/admin/approvals" className="header-nav-link accent">
                Approvals
              </Link>
              <Link to="/admin/moderation" className="header-nav-link accent">
                Moderation
              </Link>
              <Link to="/admin/add-diet" className="header-nav-link accent">
                Add Diet
              </Link>
            </>
          )}
          <Link to="/profile" className="header-nav-meta">
            {user.email}
            {user.is_admin ? " (admin)" : ""}
          </Link>
          <button type="button" className="btn btn-ghost" onClick={logout}>
            Log out
          </button>
        </>
      ) : (
        <>
          <Link to="/login" className="header-nav-link">
            Log in
          </Link>
          <Link to="/signup" className="header-nav-link accent">
            Sign up
          </Link>
        </>
      )}
    </nav>
  );
}

export default function App() {
  // Keying the boundary on the path means navigating to a new route remounts it,
  // clearing a prior page error — while the header/nav stay outside it and keep working.
  const location = useLocation();
  return (
    <div className="app-shell">
      <WireframeBackground />
      <header className="app-header desktop-only">
        <span className="brand">
          Marine Engineer <span className="accent">Exam Prep</span>
        </span>
        <HeaderNav />
      </header>
      <main className="container">
        <ErrorBoundary key={location.pathname}>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/signup" element={<Signup />} />
          <Route path="/forgot-password" element={<ForgotPassword />} />
          <Route path="/reset-password" element={<ResetPassword />} />
          <Route path="/pending" element={<Pending />} />
          <Route
            path="/profile"
            element={
              <ProtectedRoute>
                <Profile />
              </ProtectedRoute>
            }
          />
          <Route
            path="/"
            element={
              <ProtectedRoute>
                <Home />
              </ProtectedRoute>
            }
          />
          <Route
            path="/subjects/:slug"
            element={
              <ProtectedRoute>
                <Subject />
              </ProtectedRoute>
            }
          />
          <Route
            path="/diets/:dietId"
            element={
              <ProtectedRoute>
                <Diet />
              </ProtectedRoute>
            }
          />
          <Route
            path="/questions/:questionId"
            element={
              <ProtectedRoute>
                <Question />
              </ProtectedRoute>
            }
          />
          <Route
            path="/answers/:answerId"
            element={
              <ProtectedRoute>
                <Answer />
              </ProtectedRoute>
            }
          />
          <Route
            path="/topics/:topicId"
            element={
              <ProtectedRoute>
                <TopicView />
              </ProtectedRoute>
            }
          />
          <Route
            path="/admin/approvals"
            element={
              <ProtectedRoute requireAdmin>
                <AdminApprovals />
              </ProtectedRoute>
            }
          />
          <Route
            path="/admin/moderation"
            element={
              <ProtectedRoute requireAdmin>
                <AdminModeration />
              </ProtectedRoute>
            }
          />
          <Route
            path="/admin/add-diet"
            element={
              <ProtectedRoute requireAdmin>
                <AdminAddDiet />
              </ProtectedRoute>
            }
          />
        </Routes>
        </ErrorBoundary>
      </main>
      <BottomNav />
    </div>
  );
}
