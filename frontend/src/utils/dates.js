// Shared day-count math for anything counting down to an ISO date — membership
// expiry (My Account) and the member's own exam date (My Account + Home).

// Whole days remaining until `isoDate` (may be a date-only "YYYY-MM-DD" or a full
// timestamp). Returns null if unset, 0 or negative once the date has passed.
export function daysRemaining(isoDate) {
  if (!isoDate) return null;
  const end = new Date(isoDate);
  const now = new Date();
  const ms = end.getTime() - now.getTime();
  return Math.max(0, Math.ceil(ms / (1000 * 60 * 60 * 24)));
}

// Same as daysRemaining, but returns null (rather than 0) once the date is today
// or in the past — for UI that should hide itself entirely rather than show a
// "0 days" / stale countdown (e.g. the Home page exam countdown chip).
export function daysUntilFuture(isoDate) {
  if (!isoDate) return null;
  const end = new Date(isoDate);
  const now = new Date();
  if (end.getTime() <= now.getTime()) return null;
  return Math.max(1, Math.ceil((end.getTime() - now.getTime()) / (1000 * 60 * 60 * 24)));
}
