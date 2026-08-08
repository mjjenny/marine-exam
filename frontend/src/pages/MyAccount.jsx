import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client.js";
import { useAuth } from "../auth/AuthContext.jsx";
import { daysRemaining } from "../utils/dates.js";

const MEMBERSHIP_DAYS = 365;

function membershipPct(daysLeft) {
  if (daysLeft == null) return 100;
  return Math.max(0, Math.min(100, Math.round((daysLeft / MEMBERSHIP_DAYS) * 100)));
}

export default function MyAccount() {
  const { user, logout, refreshUser } = useAuth();
  const days = useMemo(() => daysRemaining(user?.expires_at), [user?.expires_at]);
  const pct = membershipPct(days);

  const [examDateInput, setExamDateInput] = useState(user?.exam_date || "");
  const [examMsg, setExamMsg] = useState(null);
  const [examError, setExamError] = useState(null);
  const [examBusy, setExamBusy] = useState(false);
  const examDaysLeft = useMemo(() => daysRemaining(user?.exam_date), [user?.exam_date]);

  async function onSaveExamDate(e) {
    e.preventDefault();
    setExamMsg(null);
    setExamError(null);
    setExamBusy(true);
    try {
      await api.setExamDate(examDateInput || null);
      await refreshUser();
      setExamMsg(examDateInput ? "Exam date saved." : "Exam date cleared.");
    } catch (err) {
      setExamError(err.message || "Could not save exam date.");
    } finally {
      setExamBusy(false);
    }
  }

  async function onClearExamDate() {
    setExamDateInput("");
    setExamMsg(null);
    setExamError(null);
    setExamBusy(true);
    try {
      await api.setExamDate(null);
      await refreshUser();
      setExamMsg("Exam date cleared.");
    } catch (err) {
      setExamError(err.message || "Could not clear exam date.");
    } finally {
      setExamBusy(false);
    }
  }

  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [pwMsg, setPwMsg] = useState(null);
  const [pwError, setPwError] = useState(null);
  const [busy, setBusy] = useState(false);

  async function onChangePassword(e) {
    e.preventDefault();
    setPwMsg(null);
    setPwError(null);
    if (newPassword !== confirmPassword) {
      setPwError("New passwords do not match.");
      return;
    }
    setBusy(true);
    try {
      const res = await api.changePassword(currentPassword, newPassword);
      setPwMsg(res.message || "Password updated.");
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
    } catch (err) {
      setPwError(err.message || "Could not update password.");
    } finally {
      setBusy(false);
    }
  }

  const lifetime = user?.is_admin || !user?.expires_at;

  return (
    <div className="card max-w-xl mx-auto">
      <p className="crumbs">
        <Link to="/">Home</Link> / My Account
      </p>
      <h1>My Account</h1>
      <p className="muted">Membership access and account security.</p>

      <section className="mt-6" aria-labelledby="membership-heading">
        <h2 id="membership-heading" className="text-lg font-semibold mb-3">
          Membership
        </h2>

        {lifetime ? (
          <div className="rounded-lg border border-[var(--border)] bg-[var(--surface-2)] p-4">
            <p className="text-sm font-medium text-[var(--amber-400)]">
              Unlimited access
            </p>
            <p className="muted text-sm mt-1">
              {user?.is_admin
                ? "Admin accounts do not expire."
                : "No expiry date is set on this account."}
            </p>
          </div>
        ) : (
          <div className="rounded-lg border border-[var(--border)] bg-[var(--surface-2)] p-4">
            <div className="flex flex-wrap items-baseline justify-between gap-2 mb-3">
              <p className="text-base font-semibold">
                <span className="text-[var(--amber-400)]">{days}</span>
                {" "}
                {days === 1 ? "Day" : "Days"} of Access Remaining
              </p>
              <p className="muted text-sm">
                Expires{" "}
                {new Date(user.expires_at).toLocaleDateString(undefined, {
                  year: "numeric",
                  month: "short",
                  day: "numeric",
                })}
              </p>
            </div>
            <div
              className="h-3 w-full rounded-full bg-[var(--navy-800)] overflow-hidden"
              role="progressbar"
              aria-valuenow={pct}
              aria-valuemin={0}
              aria-valuemax={100}
              aria-label={`${days} days of access remaining`}
            >
              <div
                className="h-full rounded-full bg-[var(--amber-500)] transition-all duration-500"
                style={{ width: `${pct}%` }}
              />
            </div>
            <p className="muted text-xs mt-2">{pct}% of the {MEMBERSHIP_DAYS}-day membership window left</p>
          </div>
        )}
      </section>

      <section className="mt-8" aria-labelledby="exam-date-heading">
        <h2 id="exam-date-heading" className="text-lg font-semibold mb-3">
          Exam date
        </h2>
        <p className="muted text-sm mb-3">
          Set the date of your own oral exam and the homepage will show a countdown.
        </p>
        <div className="rounded-lg border border-[var(--border)] bg-[var(--surface-2)] p-4">
          {user?.exam_date && examDaysLeft != null && (
            <p className="text-base font-semibold mb-3">
              <span className="text-[var(--amber-400)]">{examDaysLeft}</span>{" "}
              {examDaysLeft === 1 ? "Day" : "Days"} Until Your Exam
            </p>
          )}
          <form
            onSubmit={onSaveExamDate}
            className="flex flex-wrap items-end gap-3"
          >
            <label className="flex flex-col gap-1 text-sm">
              Exam date
              <input
                type="date"
                className="border border-[var(--border)] rounded px-3 py-2 bg-[var(--surface)] text-[var(--ink)]"
                value={examDateInput}
                onChange={(e) => setExamDateInput(e.target.value)}
              />
            </label>
            <button type="submit" className="btn" disabled={examBusy}>
              {examBusy ? "Saving…" : "Save"}
            </button>
            {user?.exam_date && (
              <button
                type="button"
                className="btn btn-ghost"
                onClick={onClearExamDate}
                disabled={examBusy}
              >
                Clear
              </button>
            )}
          </form>
          {examError && <p className="form-error mt-2">{examError}</p>}
          {examMsg && <p className="text-sm text-emerald-400 mt-2">{examMsg}</p>}
        </div>
      </section>

      <section className="mt-8" aria-labelledby="details-heading">
        <h2 id="details-heading" className="text-lg font-semibold mb-3">
          Account details
        </h2>
        <dl className="grid gap-3 text-sm">
          <div className="flex flex-col gap-0.5">
            <dt className="muted">Email</dt>
            <dd className="font-medium" aria-label="Account email">
              {user?.email || "—"}
            </dd>
          </div>
          <div className="flex flex-col gap-0.5">
            <dt className="muted">Status</dt>
            <dd className="font-medium capitalize">{user?.status || "—"}</dd>
          </div>
          <div className="flex flex-col gap-0.5">
            <dt className="muted">Role</dt>
            <dd className="font-medium">{user?.is_admin ? "Admin" : "Member"}</dd>
          </div>
        </dl>
      </section>

      <section className="mt-8" aria-labelledby="password-heading">
        <h2 id="password-heading" className="text-lg font-semibold mb-3">
          Change password
        </h2>
        <form onSubmit={onChangePassword} className="flex flex-col gap-3 max-w-md">
          <label className="flex flex-col gap-1 text-sm">
            Current password
            <input
              type="password"
              className="border border-[var(--border)] rounded px-3 py-2 bg-[var(--surface-2)] text-[var(--ink)]"
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
              required
              autoComplete="current-password"
            />
          </label>
          <label className="flex flex-col gap-1 text-sm">
            New password
            <input
              type="password"
              className="border border-[var(--border)] rounded px-3 py-2 bg-[var(--surface-2)] text-[var(--ink)]"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              required
              autoComplete="new-password"
            />
          </label>
          <label className="flex flex-col gap-1 text-sm">
            Confirm new password
            <input
              type="password"
              className="border border-[var(--border)] rounded px-3 py-2 bg-[var(--surface-2)] text-[var(--ink)]"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              required
              autoComplete="new-password"
            />
          </label>
          {pwError && <p className="form-error">{pwError}</p>}
          {pwMsg && <p className="text-sm text-emerald-400">{pwMsg}</p>}
          <button type="submit" className="btn self-start" disabled={busy}>
            {busy ? "Updating…" : "Update password"}
          </button>
        </form>
        <p className="muted text-sm mt-3">
          Prefer an email link?{" "}
          <Link to="/forgot-password">Request a password reset</Link>
        </p>
      </section>

      <div className="mt-8 flex flex-wrap gap-3">
        <Link className="btn btn-secondary" to="/profile">
          Profile
        </Link>
        <button type="button" className="btn btn-ghost" onClick={logout}>
          Log out
        </button>
      </div>
    </div>
  );
}
