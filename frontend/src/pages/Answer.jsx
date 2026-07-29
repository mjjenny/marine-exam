import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { api } from "../api/client.js";
import SketchZoom from "../components/SketchZoom.jsx";
import SuggestModal from "../components/SuggestModal.jsx";
import Markdown from "../components/Markdown.jsx";
import MasteryToggle from "../components/MasteryToggle.jsx";
import BookmarkButton from "../components/BookmarkButton.jsx";
import { qLabel } from "../utils/format.js";

// Canonical answer page. Reachable for answers with no occurrences (empty
// question_instances) — e.g. reference/companion entries — so their title and
// answer still render and they're browsable from the topic listing.
export default function Answer() {
  const { answerId } = useParams();
  const [a, setA] = useState(null);
  const [error, setError] = useState(null);
  const [showSuggest, setShowSuggest] = useState(false);

  useEffect(() => {
    setA(null);
    setError(null);
    api.answer(answerId).then(setA).catch((e) => setError(e.message));
  }, [answerId]);

  if (error) return <div className="card"><p className="form-error">{error}</p></div>;
  if (!a) return <div className="card">Loading…</div>;

  const pending = a.answer_pending;

  return (
    <div className="card question-page reading-page">
      <div className="reading-bar">
        <Link to={`/?book=${a.subject.slug}`} className="back-to-index">‹ Back to Index</Link>
        <div className="reading-bar-actions">
          <BookmarkButton contentType="answer" contentId={a.id} />
          <MasteryToggle slug={a.subject.slug} answerId={a.id} />
        </div>
      </div>

      <p className="crumbs">
        <Link to="/">Home</Link> /{" "}
        <Link to={`/subjects/${a.subject.slug}`}>{a.subject.name}</Link>
        {a.topic && (
          <>
            {" "}/ <Link to={`/topics/${a.topic.id}`}>{a.topic.name}</Link>
          </>
        )}
      </p>

      <div className="q-head">
        {a.topic &&
          (a.subject.is_oral ? (
            <span className="chip">{a.topic.name}</span>
          ) : (
            <Link to={`/topics/${a.topic.id}`} className="chip chip-link topic-tab">
              {a.topic.name}
            </Link>
          ))}
      </div>
      <h1 className="q-text">{a.title || "(untitled)"}</h1>

      {a.question_as_set && (
        <section className="question-as-set">
          <h2>Question as set</h2>
          <Markdown>{a.question_as_set}</Markdown>
        </section>
      )}

      <section>
        <h2>Answer</h2>
        {pending ? (
          <div className="answer-pending">
            <p className="answer-pending-title">Answer pending for this diet.</p>
            <p className="muted">
              This question has been logged, but a model answer hasn’t been published
              yet. If you have a strong answer, submit it below — an administrator will
              review and publish it here.
            </p>
            <button className="btn" onClick={() => setShowSuggest(true)}>
              Submit an Answer
            </button>
          </div>
        ) : (
          <>
            <Markdown>{a.answer_text}</Markdown>
            <SketchZoom refs={a.sketch_refs} />
          </>
        )}
      </section>

      <section className="also-asked">
        <h2>Recorded sittings</h2>
        {a.occurrences.length === 0 ? (
          <p className="muted">
            No recorded sittings yet — this is a reference entry with no logged diet
            occurrence.
          </p>
        ) : (
          <div className="chip-row">
            {a.occurrences.map((o) => (
              <Link
                key={o.question_instance_id}
                to={`/questions/${o.question_instance_id}`}
                className="chip chip-link"
              >
                {o.diet_label || "—"}
                {o.question_number ? ` · ${qLabel(o.question_number)}` : ""}
              </Link>
            ))}
          </div>
        )}
      </section>

      {!pending && (
        <div className="q-actions">
          <button className="btn" onClick={() => setShowSuggest(true)}>
            Suggest Improvement
          </button>
        </div>
      )}

      {showSuggest && (
        <SuggestModal
          answerId={a.id}
          currentAnswer={a.answer_text}
          pending={pending}
          onClose={() => setShowSuggest(false)}
        />
      )}
    </div>
  );
}
