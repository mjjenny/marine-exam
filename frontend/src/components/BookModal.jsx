import { useEffect, useMemo, useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { api } from "../api/client.js";
import BookCover from "./BookCover.jsx";

// The opened book: a cover that flips away (3D) to reveal a warm index page with a
// live search filter and a clickable native index. Clicking a row opens that answer.
export default function BookModal({ subject, onClose }) {
  const navigate = useNavigate();
  const [entries, setEntries] = useState(null);
  const [error, setError] = useState(null);
  const [query, setQuery] = useState("");
  const [flipDone, setFlipDone] = useState(false); // safety net: reveal even if the flip animation stalls

  useEffect(() => {
    let alive = true;
    api
      .subjectIndex(subject.slug)
      .then((d) => alive && setEntries(d.entries))
      .catch((e) => alive && setError(e.message));
    const done = setTimeout(() => alive && setFlipDone(true), 820); // ~flip duration
    const onKey = (e) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => {
      alive = false;
      clearTimeout(done);
      window.removeEventListener("keydown", onKey);
    };
  }, [subject.slug, onClose]);

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

  return (
    <div className="book-overlay" onClick={onClose}>
      <div
        className={`open-book ${flipDone ? "flip-done" : ""}`}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="open-book-page">
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
            placeholder="Search question, sitting, or status…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            autoFocus
          />

          {error && <p className="form-error">{error}</p>}
          {!entries && !error && <p className="muted">Opening the index…</p>}

          {entries && (
            <div className="book-index">
              <div className="book-index-head">
                <span className="col-sitting">Sitting</span>
                <span className="col-q">Q</span>
                <span className="col-question">Question</span>
                <span className="col-status">Status</span>
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
                    <span className="col-question">{e.question}</span>
                    <span className={`col-status status-${e.status.toLowerCase()}`}>
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

          <div className="book-page-foot">
            <Link to={`/subjects/${subject.slug}`} onClick={onClose}>
              Browse by {subject.is_oral ? "topic" : "diet"} instead →
            </Link>
          </div>
        </div>

        {/* the flipping cover, revealing the page underneath */}
        <div className="open-book-cover">
          <BookCover subject={subject} />
        </div>
      </div>
    </div>
  );
}
