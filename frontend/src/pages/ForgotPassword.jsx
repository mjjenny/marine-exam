import { useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client.js";

export default function ForgotPassword() {
  const [email, setEmail] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [sent, setSent] = useState(false);

  async function onSubmit(e) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await api.forgotPassword(email);
      setSent(true); // response is intentionally the same whether or not the email exists
    } catch (err) {
      setError(err.message || "Something went wrong. Please try again.");
    } finally {
      setBusy(false);
    }
  }

  if (sent) {
    return (
      <div className="card auth-card">
        <h1>Check your email</h1>
        <p>
          If an account exists for <strong>{email}</strong>, we've sent a link to reset
          your password. The link is valid for 1 hour.
        </p>
        <p className="auth-alt">
          <Link to="/login">Back to log in</Link>
        </p>
      </div>
    );
  }

  return (
    <div className="card auth-card">
      <h1>Forgot password</h1>
      <p className="muted">
        Enter your account email and we'll send you a link to reset your password.
      </p>
      <form onSubmit={onSubmit}>
        <label>
          Email
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            autoComplete="email"
            autoFocus
          />
        </label>
        {error && <p className="form-error">{error}</p>}
        <button type="submit" className="btn" disabled={busy}>
          {busy ? "Sending…" : "Send reset link"}
        </button>
      </form>
      <p className="auth-alt">
        Remembered it? <Link to="/login">Log in</Link>
      </p>
    </div>
  );
}
