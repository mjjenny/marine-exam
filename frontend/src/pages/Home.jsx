import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api } from "../api/client.js";
import { useAuth } from "../auth/AuthContext.jsx";
import BookSpread from "../components/BookSpread.jsx";
import Bookshelf from "../components/Bookshelf.jsx";
import { masteredCount, onMasteryChange } from "../utils/mastery.js";

const COMPASS_SRC = "/branding/engine_room_academy_slow_spin.webp";

// A member's display name, derived from the local part of their email
// (e.g. "jane.doe@…" -> "Jane Doe"), since the account has no separate name field.
function displayName(email) {
  if (!email) return "";
  const local = email.split("@")[0];
  return local
    .split(/[._-]+/)
    .filter(Boolean)
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}

// Greeting keyed to the member's local browser time.
function timeGreeting() {
  const h = new Date().getHours();
  if (h < 12) return "Good morning";
  if (h < 17) return "Good afternoon";
  return "Good evening";
}

// Approved-only landing page: layered hero with compass + subject shelf.
export default function Home() {
  const { user } = useAuth();
  const [subjects, setSubjects] = useState(null);
  const [error, setError] = useState(null);
  const [active, setActive] = useState(null);
  const [searchParams, setSearchParams] = useSearchParams();
  const [masteryTick, setMasteryTick] = useState(0);

  useEffect(() => {
    api.subjects().then(setSubjects).catch((e) => setError(e.message));
  }, []);

  useEffect(() => onMasteryChange(() => setMasteryTick((n) => n + 1)), []);

  // Deep-link: /?book=<slug> auto-opens that subject's book (e.g. "Back to Index"
  // from an answer page returns the reader straight to the open book, not the shelf).
  const bookSlug = searchParams.get("book");
  useEffect(() => {
    if (subjects && bookSlug) {
      const s = subjects.find((x) => x.slug === bookSlug);
      if (s) setActive(s);
    }
  }, [subjects, bookSlug]);

  function openBook(subject) {
    setActive(subject);
    setSearchParams({ book: subject.slug }, { replace: true });
  }

  function closeBook() {
    setActive(null);
    if (bookSlug) setSearchParams({}, { replace: true }); // drop ?book so it won't re-open
  }

  const name = displayName(user?.email);

  const overall = useMemo(() => {
    if (!subjects?.length) return null;
    const total = subjects.reduce((sum, s) => sum + (s.answer_count || 0), 0);
    if (!total) return null;
    const mastered = subjects.reduce((sum, s) => sum + masteredCount(s.slug), 0);
    const pct = Math.round((mastered / total) * 100);
    return { total, mastered, pct };
    // masteryTick forces recompute when local mastery changes
  }, [subjects, masteryTick]);

  return (
    <div className="home-page">
      <div className="home-hero">
        {/* Atmosphere only — does not hold the compass image */}
        <div className="home-hero-scrim" aria-hidden="true" />

        <div className="home-hero-content">
          <header className="home-head">
            <p className="home-kicker">MCA · SQA Chief Engineer Exam Prep</p>
            <h1 className="home-greeting">
              {timeGreeting()}
              {name ? (
                <>
                  , <span className="home-name">{name}</span>
                </>
              ) : (
                ""
              )}
            </h1>
            {overall && (
              <p className="home-overall">
                Overall {overall.pct}% · {overall.mastered} of {overall.total} mastered
              </p>
            )}
          </header>

          {/* Compass in normal flow — not absolutely positioned over content */}
          <div className="home-compass">
            <img
              src={COMPASS_SRC}
              alt=""
              width={512}
              height={512}
              decoding="async"
              fetchPriority="low"
            />
          </div>

          {/* Sibling AFTER compass, BEFORE shelf — never overlaps the logo */}
          <p className="home-shelf-hint">
            Choose a book from the shelf to browse its question index.
          </p>

          <div className="home-shelf">
            {error && <p className="form-error">{error}</p>}
            {!subjects && !error && <p className="muted">Loading…</p>}
            {subjects && <Bookshelf subjects={subjects} onOpen={openBook} />}
          </div>
        </div>
      </div>

      {active && (
        <BookSpread subject={active} subjects={subjects} onClose={closeBook} />
      )}
    </div>
  );
}
