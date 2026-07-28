import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { api } from "../api/client.js";

// Subject page. Written subjects show a diet list; EK Oral shows a flat,
// searchable, topic-filterable question list.
export default function Subject() {
  const { slug } = useParams();
  const [subject, setSubject] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    setSubject(null);
    setError(null);
    api.subject(slug).then(setSubject).catch((e) => setError(e.message));
  }, [slug]);

  if (error) return <div className="card"><p className="form-error">{error}</p></div>;
  if (!subject) return <div className="card">Loading…</div>;

  return (
    <div className="card">
      <p className="crumbs">
        <Link to="/">Home</Link> / {subject.name}
      </p>
      <h1>{subject.name}</h1>
      {subject.is_oral ? (
        <FlatQuestionList slug={slug} topics={subject.topics} />
      ) : (
        <DietList slug={slug} />
      )}
    </div>
  );
}

function DietList({ slug }) {
  const [diets, setDiets] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    api.diets(slug).then(setDiets).catch((e) => setError(e.message));
  }, [slug]);

  if (error) return <p className="form-error">{error}</p>;
  if (!diets) return <p>Loading diets…</p>;
  if (diets.length === 0) return <p className="muted">No diets yet.</p>;

  return (
    <ul className="list">
      {diets.map((d) => (
        <li key={d.id}>
          <Link to={`/diets/${d.id}`} className="list-row">
            <span>{d.label}</span>
            <span className="muted">{d.question_count} questions</span>
          </Link>
        </li>
      ))}
    </ul>
  );
}

function FlatQuestionList({ slug, topics }) {
  const [questions, setQuestions] = useState(null);
  const [error, setError] = useState(null);
  const [activeTopic, setActiveTopic] = useState(null);
  const [search, setSearch] = useState("");

  useEffect(() => {
    setQuestions(null);
    const handle = setTimeout(() => {
      api
        .subjectQuestions(slug, { topicId: activeTopic, q: search })
        .then((r) => setQuestions(r.questions))
        .catch((e) => setError(e.message));
    }, 200); // debounce search typing
    return () => clearTimeout(handle);
  }, [slug, activeTopic, search]);

  return (
    <>
      <input
        className="search"
        type="search"
        placeholder="Search questions…"
        value={search}
        onChange={(e) => setSearch(e.target.value)}
      />
      <div className="chip-row">
        <button
          className={`chip chip-btn${activeTopic === null ? " chip-active" : ""}`}
          onClick={() => setActiveTopic(null)}
        >
          All
        </button>
        {topics?.map((t) => (
          <button
            key={t.id}
            className={`chip chip-btn${activeTopic === t.id ? " chip-active" : ""}`}
            onClick={() => setActiveTopic(t.id)}
          >
            {t.name}
          </button>
        ))}
      </div>
      {error && <p className="form-error">{error}</p>}
      {!questions && !error && <p>Loading…</p>}
      {questions && questions.length === 0 && (
        <p className="muted">No questions match.</p>
      )}
      <ul className="list">
        {questions?.map((q) => (
          <li key={q.id}>
            <Link to={`/questions/${q.id}`} className="list-row">
              <span>{q.question_text_as_asked}</span>
              {q.topic_name && <span className="chip">{q.topic_name}</span>}
            </Link>
          </li>
        ))}
      </ul>
    </>
  );
}
