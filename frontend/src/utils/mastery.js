// Per-reader "mastered" tracking, kept in localStorage (no backend model yet).
// Shape: { [subjectSlug]: [canonicalAnswerId, ...] }. Toggling an answer's mastery
// broadcasts a "mastery-change" event so the book ribbon + toggle stay in sync,
// including across tabs (via the native `storage` event).
const KEY = "mca-mastery";
const EVENT = "mastery-change";

function readAll() {
  try {
    return JSON.parse(localStorage.getItem(KEY)) || {};
  } catch {
    return {};
  }
}

function writeAll(data) {
  localStorage.setItem(KEY, JSON.stringify(data));
  window.dispatchEvent(new Event(EVENT));
}

export function masteredIds(slug) {
  return new Set(readAll()[slug] || []);
}

export function isMastered(slug, answerId) {
  return masteredIds(slug).has(answerId);
}

export function masteredCount(slug) {
  return (readAll()[slug] || []).length;
}

// Returns the new mastered state for this answer.
export function toggleMastered(slug, answerId) {
  const all = readAll();
  const ids = new Set(all[slug] || []);
  const nowMastered = !ids.has(answerId);
  if (nowMastered) ids.add(answerId);
  else ids.delete(answerId);
  all[slug] = [...ids];
  writeAll(all);
  return nowMastered;
}

// Subscribe to any mastery change (same tab or cross-tab). Returns an unsubscribe fn.
export function onMasteryChange(fn) {
  const local = () => fn();
  const cross = (e) => e.key === KEY && fn();
  window.addEventListener(EVENT, local);
  window.addEventListener("storage", cross);
  return () => {
    window.removeEventListener(EVENT, local);
    window.removeEventListener("storage", cross);
  };
}

// 0–100 whole-number progress for a subject given its total answer count.
export function masteryPercent(slug, total) {
  if (!total) return 0;
  return Math.round((masteredCount(slug) / total) * 100);
}
