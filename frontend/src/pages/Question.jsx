import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { api } from "../api/client.js";
import SuggestModal from "../components/SuggestModal.jsx";
import SketchZoom from "../components/SketchZoom.jsx";
import Markdown from "../components/Markdown.jsx";
import MasteryToggle from "../components/MasteryToggle.jsx";
import BookmarkButton from "../components/BookmarkButton.jsx";
import { qLabel } from "../utils/format.js";

// Single question page: verbatim question, canonical answer, highlighted examiner
// feedback, cross-diet "also asked in", and (later) Suggest Improvement.
export default function Question() {
  const { questionId } = useParams();
  const [q, setQ] = useState(null);
  const [error, setError] = useState(null);
  const [showSuggest, setShowSuggest] = useState(false);

  useEffect(() => {
    setQ(null);
    setError(null);
    api.question(questionId).then(setQ).catch((e) => setError(e.message));
  }, [questionId]);

  if (error) return <div className="card"><p className="form-error">{error}</p></div>;
  if (!q) return <div className="card">Loading…</div>;

  const parent = q.diet
    ? { to: `/diets/${q.diet.id}`, label: q.diet.label }
    : { to: `/subjects/${q.subject.slug}`, label: q.subject.name };
  const pending = q.canonical_answer.answer_pending;
  const heading = q.canonical_answer?.title || q.question_text_as_asked;
  const asSetText = q.canonical_answer?.question_as_set || q.question_text_as_asked;

  return (
    <div className="card question-page reading-page">
      <div className="reading-bar">
        <Link to={`/?book=${q.subject.slug}`} className="back-to-index">‹ Back to Index</Link>
        <div className="reading-bar-actions">
          <BookmarkButton contentType="question" contentId={q.id} />
          <MasteryToggle slug={q.subject.slug} answerId={q.canonical_answer.id} />
        </div>
      </div>

      <p className="crumbs">
        <Link to="/">Home</Link> /{" "}
        <Link to={`/subjects/${q.subject.slug}`}>{q.subject.name}</Link> /{" "}
        <Link to={parent.to}>{parent.label}</Link>
      </p>

      <div className="q-head">
        {q.topic &&
          (q.subject.is_oral ? (
            // EK Oral browses by topic via its flat list, not the diet-oriented view.
            <span className="chip">{q.topic.name}</span>
          ) : (
            <Link
              to={`/topics/${q.topic.id}`}
              className="chip chip-link topic-tab"
              title={`Browse all “${q.topic.name}” questions across diets`}
            >
              {q.topic.name}
            </Link>
          ))}
        {q.question_number && <span className="muted">{qLabel(q.question_number)}</span>}
      </div>
      <h1 className="q-text">{heading}</h1>

      {asSetText && (
        <section className="question-as-set">
          <h2>Question as set</h2>
          <Markdown>{asSetText}</Markdown>
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
            <Markdown>{q.canonical_answer.answer_text}</Markdown>
            <SketchZoom refs={q.canonical_answer.sketch_refs} />
          </>
        )}
      </section>

      {q.examiner_feedback_text && (
        <section className="examiner-feedback">
          <h2>{q.feedback_label}</h2>
          <Markdown>{q.examiner_feedback_text}</Markdown>
        </section>
      )}

      {q.also_asked_in.length > 0 && (
        <section className="also-asked">
          <h2>Also asked in</h2>
          <div className="chip-row">
            {q.also_asked_in.map((a) => (
              <Link
                key={a.question_instance_id}
                to={`/questions/${a.question_instance_id}`}
                className="chip chip-link"
              >
                {a.diet_label}
              </Link>
            ))}
          </div>
        </section>
      )}

      {!pending && (
        <div className="q-actions">
          <button className="btn" onClick={() => setShowSuggest(true)}>
            Suggest Improvement
          </button>
        </div>
      )}

      {showSuggest && (
        <SuggestModal
          answerId={q.canonical_answer.id}
          currentAnswer={q.canonical_answer.answer_text}
          pending={pending}
          onClose={() => setShowSuggest(false)}
        />
      )}
    </div>
  );
}
