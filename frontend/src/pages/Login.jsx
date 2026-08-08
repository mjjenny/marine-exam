import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useAuth } from "../auth/AuthContext.jsx";

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(e) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      const u = await login(email, password);
      navigate(u.status === "approved" ? "/" : "/pending", { replace: true });
    } catch (err) {
      setError(err.message || "Login failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="card auth-card">
      <div className="flex flex-col items-center justify-center mb-2 overflow-visible">
        <img
          className="w-20 h-20 md:w-28 md:h-28 object-contain drop-shadow-2xl"
          src="/branding/engine_room_academy_slow_spin.webp"
          alt="Engine Room Academy"
          width={192}
          height={192}
          decoding="async"
          style={{ filter: "drop-shadow(0 0 18px rgba(180, 120, 60, 0.25))" }}
        />
      </div>
      <h1>Log in</h1>
      <form onSubmit={onSubmit}>
        <label>
          Email
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            autoComplete="email"
          />
        </label>
        <label>
          Password
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            autoComplete="current-password"
          />
        </label>
        {error && <p className="form-error">{error}</p>}
        <button type="submit" className="btn" disabled={busy}>
          {busy ? "Logging in…" : "Log in"}
        </button>
      </form>
      <p className="auth-alt">
        <Link to="/forgot-password">Forgot password?</Link>
      </p>
      <p className="auth-alt">
        No account? <Link to="/signup">Sign up</Link>
      </p>
    </div>
  );
}
