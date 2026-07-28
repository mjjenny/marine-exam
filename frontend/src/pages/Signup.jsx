import { useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../auth/AuthContext.jsx";
import PasswordChecklist from "../components/PasswordChecklist.jsx";
import { isPasswordValid } from "../utils/password.js";

export default function Signup() {
  const { signup } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);

  const pwValid = isPasswordValid(password);

  async function onSubmit(e) {
    e.preventDefault();
    if (!pwValid) {
      setError("Please choose a password that meets all the requirements below.");
      return;
    }
    setError(null);
    setBusy(true);
    try {
      await signup(email, password);
      setDone(true);
    } catch (err) {
      setError(err.message || "Signup failed");
    } finally {
      setBusy(false);
    }
  }

  if (done) {
    return (
      <div className="card auth-card">
        <h1>Thanks for signing up</h1>
        <p>
          Your account is <strong>awaiting approval</strong>. You'll be able to log in
          and access the subjects once an administrator approves you.
        </p>
        <p className="auth-alt">
          <Link to="/login">Back to log in</Link>
        </p>
      </div>
    );
  }

  return (
    <div className="card auth-card">
      <h1>Sign up</h1>
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
            autoComplete="new-password"
            aria-describedby="pw-reqs"
          />
        </label>
        <div id="pw-reqs">
          <PasswordChecklist password={password} />
        </div>
        {error && <p className="form-error">{error}</p>}
        <button type="submit" className="btn" disabled={busy || !pwValid}>
          {busy ? "Submitting…" : "Sign up"}
        </button>
      </form>
      <p className="auth-alt">
        Already have an account? <Link to="/login">Log in</Link>
      </p>
    </div>
  );
}
