import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api } from "../api/client.js";
import { useAuth } from "../auth/AuthContext.jsx";
import BookSpread from "../components/BookSpread.jsx";
import Bookshelf from "../components/Bookshelf.jsx";
import SubjectProgressWidget from "../components/SubjectProgressWidget.jsx";

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

// Approved-only landing page: a static library shelf of subject books that open
// to a searchable question index (BookSpread).
export default function Home() {
  const { user } = useAuth();
  const [subjects, setSubjects] = useState(null);
  const [error, setError] = useState(null);
  const [active, setActive] = useState(null);
  const [searchParams, setSearchParams] = useSearchParams();

  useEffect(() => {
    api.subjects().then(setSubjects).catch((e) => setError(e.message));
  }, []);

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

  return (
    <div>
      <div className="home-head">
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
        <p className="muted">Choose a book from the shelf to browse its question index.</p>
      </div>

      <SubjectProgressWidget />

      {error && <p className="form-error">{error}</p>}
      {!subjects && !error && <p className="muted">Loading…</p>}

      {subjects && <Bookshelf subjects={subjects} onOpen={openBook} />}

      {active && (
        <BookSpread subject={active} subjects={subjects} onClose={closeBook} />
      )}
    </div>
  );
}
