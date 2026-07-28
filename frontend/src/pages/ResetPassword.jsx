import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api } from "../api/client.js";
import PasswordChecklist from "../components/PasswordChecklist.jsx";
import { isPasswordValid } from "../utils/password.js";

export default function ResetPassword() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token") || "";

  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [done, setDone] = useState(false);

  const pwValid = isPasswordValid(password);
  const matches = password === confirm;

  async function onSubmit(e) {
    e.preventDefault();
    if (!pwValid) {
      setError("Please choose a password that meets all the requirements below.");
      return;
    }
    if (!matches) {
      setError("The two passwords don't match.");
      return;
    }
    setError(null);
    setBusy(true);
    try {
      await api.resetPassword(token, password);
      setDone(true);
    } catch (err) {
      setError(err.message || "Could not reset your password.");
    } finally {
      setBusy(false);
    }
  }

  if (!token) {
    return (
      <div className="card auth-card">
        <h1>Invalid reset link</h1>
        <p className="form-error">This reset link is missing its token.</p>
        <p className="auth-alt">
          <Link to="/forgot-password">Request a new link</Link>
        </p>
      </div>
    );
  }

  if (done) {
    return (
      <div className="card auth-card">
        <h1>Password reset</h1>
        <p>Your password has been updated. You can now log in with your new password.</p>
        <p className="auth-alt">
          <Link to="/login">Go to log in</Link>
        </p>
      </div>
    );
  }

  return (
    <div className="card auth-card">
      <h1>Choose a new password</h1>
      <form onSubmit={onSubmit}>
        <label>
          New password
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            autoComplete="new-password"
            autoFocus
            aria-describedby="pw-reqs"
          />
        </label>
        <div id="pw-reqs">
          <PasswordChecklist password={password} />
        </div>
        <label>
          Confirm new password
          <input
            type="password"
            value={confirm}
            onChange={(e) => setConfirm(e.target.value)}
            required
            autoComplete="new-password"
          />
        </label>
        {confirm && !matches && <p className="form-error">The two passwords don't match.</p>}
        {error && <p className="form-error">{error}</p>}
        <button type="submit" className="btn" disabled={busy || !pwValid || !matches}>
          {busy ? "Saving…" : "Reset password"}
        </button>
      </form>
      <p className="auth-alt">
        <Link to="/login">Back to log in</Link>
      </p>
    </div>
  );
}
