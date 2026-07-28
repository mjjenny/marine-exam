import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { api } from "../api/client.js";
import { qLabel } from "../utils/format.js";
import RepeatBadge from "../components/RepeatBadge.jsx";

// All questions asked in one diet (sitting).
export default function Diet() {
  const { dietId } = useParams();
  const [diet, setDiet] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    setDiet(null);
    setError(null);
    api.diet(dietId).then(setDiet).catch((e) => setError(e.message));
  }, [dietId]);

  if (error) return <div className="card"><p className="form-error">{error}</p></div>;
  if (!diet) return <div className="card">Loading…</div>;

  return (
    <div className="card">
      <p className="crumbs">
        <Link to="/">Home</Link> /{" "}
        <Link to={`/subjects/${diet.subject.slug}`}>{diet.subject.name}</Link> /{" "}
        {diet.label}
      </p>
      <h1>{diet.label}</h1>
      {diet.questions.length === 0 ? (
        <p className="muted">No questions recorded for this diet.</p>
      ) : (
        <ul className="list">
          {diet.questions.map((q) => (
            <li key={q.id}>
              <Link to={`/questions/${q.id}`} className="list-row">
                <span>
                  {q.question_number ? <strong>{qLabel(q.question_number)}. </strong> : null}
                  {q.question_text_as_asked}
                </span>
                <span className="row-tags">
                  {q.repeat_count > 1 && <RepeatBadge diets={q.repeat_diets} />}
                  {q.topic_name && <span className="chip">{q.topic_name}</span>}
                </span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
