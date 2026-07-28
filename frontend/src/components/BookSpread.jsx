import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client.js";
import BookCover from "./BookCover.jsx";
import StudySessionTimer from "./StudySessionTimer.jsx";
import { masteredIds, masteryPercent, onMasteryChange } from "../utils/mastery.js";

// The opened book. On desktop it is a two-page spread: the left page is the
// subject dashboard (overview + study timer), the right page is the searchable
// question index. A cover flips away (3D) on open; quick-switch tabs on the right
// edge swap subjects without closing the book. Below 768px it collapses to a single
// full-screen index page (the mobile fallback). See theme.css `.open-book.spread`.
const DISPLAY_TITLE = { "ek-naval": "EK Naval Architecture" };

function ribbonTier(pct) {
  if (pct >= 100) return "gold";
  if (pct >= 26) return "silver";
  return "grey";
}

export default function BookSpread({ subject: initial, subjects, onClose }) {
  const navigate = useNavigate();
  const [subject, setSubject] = useState(initial);
  const [entries, setEntries] = useState(null);
  const [error, setError] = useState(null);
  const [query, setQuery] = useState("");
  const [flipDone, setFlipDone] = useState(false); // reveal even if the flip stalls
  const [pct, setPct] = useState(0);

  // (re)load the index whenever the active subject changes
  useEffect(() => {
    let alive = true;
    setEntries(null);
    setError(null);
    setQuery("");
    api
      .subjectIndex(subject.slug)
      .then((d) => alive && setEntries(d.entries))
      .catch((e) => alive && setError(e.message));
    return () => {
      alive = false;
    };
  }, [subject.slug]);

  // flip-safety net + Escape-to-close (once)
  useEffect(() => {
    const done = setTimeout(() => setFlipDone(true), 820);
    const onKey = (e) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => {
      clearTimeout(done);
      window.removeEventListener("keydown", onKey);
    };
  }, [onClose]);

  // keep the progress ribbon in sync with mastery for the active subject
  const recompute = useCallback(
    () => setPct(masteryPercent(subject.slug, subject.answer_count || 0)),
    [subject.slug, subject.answer_count]
  );
  useEffect(() => {
    recompute();
    return onMasteryChange(recompute);
  }, [recompute]);

  const summary = useMemo(() => {
    if (!entries) return null;
    const sittings = new Set(entries.map((e) => e.sitting).filter(Boolean)).size;
    const occurrences = entries.filter((e) => e.sitting).length;
    const answers = new Set(entries.map((e) => e.canonical_answer_id)).size;
    const mastered = masteredIds(subject.slug).size;
    return { sittings, occurrences, answers, mastered };
  }, [entries, subject.slug, pct]); // pct dep keeps `mastered` fresh on toggle

  const filtered = useMemo(() => {
    if (!entries) return [];
    const q = query.trim().toLowerCase();
    if (!q) return entries;
    return entries.filter((e) =>
      [e.question, e.sitting, e.status, e.q].some(
        (f) => (f || "").toLowerCase().includes(q)
      )
    );
  }, [entries, query]);

  function openEntry(e) {
    onClose();
    navigate(
      e.question_instance_id
        ? `/questions/${e.question_instance_id}`
        : `/answers/${e.canonical_answer_id}`
    );
  }

  const title = DISPLAY_TITLE[subject.slug] || subject.name;

  return (
    <div className="book-overlay" onClick={onClose}>
      <div
        className={`open-book spread ${flipDone ? "flip-done" : ""}`}
        onClick={(e) => e.stopPropagation()}
      >
        {/* LEFT PAGE — subject dashboard */}
        <div className="book-page book-page-left">
          <div className="dash">
            <span className="dash-kicker">{subject.is_oral ? "Oral index" : "Question bank"}</span>
            <h2 className="dash-title">{title}</h2>
            {summary ? (
              <p className="dash-summary">
                <strong>{summary.occurrences}</strong> questions across{" "}
                <strong>{summary.sittings}</strong> sittings, distilled into{" "}
                <strong>{summary.answers}</strong> distinct answers.
              </p>
            ) : (
              <p className="dash-summary muted">Gathering the record…</p>
            )}

            <div className="dash-progress">
              <div className="dash-progress-bar">
                <span className={`dash-progress-fill tier-${ribbonTier(pct)}`} style={{ width: `${pct}%` }} />
              </div>
              <span className="dash-progress-label">
                {pct}% mastered
                {summary ? ` · ${summary.mastered}/${summary.answers}` : ""}
              </span>
            </div>

            <StudySessionTimer />
          </div>
        </div>

        {/* RIGHT PAGE — question index */}
        <div className="book-page book-page-right" key={subject.slug}>
          <div className="book-page-head">
            <div>
              <h2>{subject.name}</h2>
              <p className="muted">
                Question index{entries ? ` · ${entries.length} entries` : ""}
              </p>
            </div>
            <button className="book-close" onClick={onClose} aria-label="Close book">
              ✕
            </button>
          </div>

          <input
            className="book-search"
            type="search"
            placeholder="Search question, sitting, or code…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            autoFocus
          />

          {error && <p className="form-error">{error}</p>}
          {!entries && !error && <p className="muted">Opening the index…</p>}

          {entries && (
            <div className={`book-index ${subject.is_oral ? "oral" : ""}`}>
              <div className="book-index-head">
                <span className="col-sitting">Sitting</span>
                <span className="col-q">{subject.is_oral ? "#" : "Q"}</span>
                <span className="col-question">Question</span>
                <span className="col-status">{subject.is_oral ? "Status" : "Entry"}</span>
              </div>
              <ul className="book-index-list">
                {filtered.map((e, i) => (
                  <li
                    key={
                      e.question_instance_id
                        ? `q${e.question_instance_id}`
                        : `a${e.canonical_answer_id}-${i}`
                    }
                    className="book-index-row"
                    role="button"
                    tabIndex={0}
                    onClick={() => openEntry(e)}
                    onKeyDown={(k) =>
                      (k.key === "Enter" || k.key === " ") &&
                      (k.preventDefault(), openEntry(e))
                    }
                  >
                    <span className="col-sitting">{e.sitting || "—"}</span>
                    <span className="col-q">{e.q || "—"}</span>
                    <span className="col-question">
                      {e.question}
                      {e.subtitle && <span className="col-question-sub">{e.subtitle}</span>}
                    </span>
                    <span
                      className={`col-status ${
                        /^E\d+$/.test(e.status)
                          ? "col-code"
                          : `status-${(e.status || "").toLowerCase()}`
                      }`}
                    >
                      {e.status}
                    </span>
                  </li>
                ))}
                {filtered.length === 0 && (
                  <li className="book-index-empty muted">No questions match “{query}”.</li>
                )}
              </ul>
            </div>
          )}
        </div>

        {/* progress ribbon — hangs from the top, colour tracks mastery */}
        <div className={`book-ribbon ribbon-${ribbonTier(pct)}`} aria-hidden="true">
          <span>{pct}%</span>
        </div>

        {/* quick-switch tabs — swap subjects without closing the book */}
        {subjects && subjects.length > 1 && (
          <div className="book-tabs" role="tablist" aria-label="Switch book">
            {subjects.map((s) => (
              <button
                key={s.slug}
                role="tab"
                aria-selected={s.slug === subject.slug}
                className={`book-tab cover-${s.slug} ${s.slug === subject.slug ? "active" : ""}`}
                onClick={() => s.slug !== subject.slug && setSubject(s)}
                title={s.name}
              >
                {s.name.replace(/^EK\s+/, "")}
              </button>
            ))}
          </div>
        )}

        {/* the flipping cover, revealing the spread underneath */}
        <div className="open-book-cover">
          <BookCover subject={subject} showRibbon={false} />
        </div>
      </div>
    </div>
  );
}
