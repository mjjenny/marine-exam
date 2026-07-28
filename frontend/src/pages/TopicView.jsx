import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { api } from "../api/client.js";
import RepeatBadge from "../components/RepeatBadge.jsx";

// Every question sharing a topic, across all diets. Each entry keeps its diet
// label so sitting context isn't lost when browsing by topic instead of by diet.
export default function TopicView() {
  const { topicId } = useParams();
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    setData(null);
    setError(null);
    api.topicQuestions(topicId).then(setData).catch((e) => setError(e.message));
  }, [topicId]);

  if (error) return <div className="card"><p className="form-error">{error}</p></div>;
  if (!data) return <div className="card">Loading…</div>;

  const { topic, questions } = data;

  return (
    <div className="card">
      <p className="crumbs">
        <Link to="/">Home</Link> /{" "}
        <Link to={`/subjects/${topic.subject.slug}`}>{topic.subject.name}</Link> /{" "}
        Topic
      </p>
      <h1>{topic.name}</h1>
      <p className="muted">
        Every question on this topic. ↺ marks how many diets a question recurs across.
      </p>

      {questions.length === 0 ? (
        <p className="muted">No questions on this topic yet.</p>
      ) : (
        <ul className="list">
          {questions.map((qq) => {
            // One row per question. Multi-diet questions open their latest occurrence;
            // occurrence-less reference answers link to the answer page.
            const to = qq.question_instance_id
              ? `/questions/${qq.question_instance_id}`
              : `/answers/${qq.canonical_answer_id}`;
            return (
              <li key={qq.canonical_answer_id}>
                <Link to={to} className="list-row">
                  <span>{qq.question_text_as_asked}</span>
                  <span className="row-tags">
                    {qq.repeat_diets.length > 1 ? (
                      <RepeatBadge diets={qq.repeat_diets} />
                    ) : qq.repeat_diets.length === 1 ? (
                      <span className="chip">{qq.repeat_diets[0]}</span>
                    ) : qq.question_instance_id ? null : (
                      <span className="chip">no recorded sittings</span>
                    )}
                  </span>
                </Link>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
