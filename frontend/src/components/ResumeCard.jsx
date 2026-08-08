import { Link } from "react-router-dom";

/**
 * "Continue where you left off" — shown on Home when the member has at least one
 * completed answer. `answer` is the resolved GET /api/answers/:id payload for their
 * most recently completed item (see Home.jsx), so this component does no fetching
 * of its own.
 */
export default function ResumeCard({ answer }) {
  if (!answer) return null;

  const crumb = [answer.subject?.name, answer.topic?.name].filter(Boolean).join(" › ");

  return (
    <div className="card resume-card" role="group" aria-label="Resume where you left off">
      <p className="chip resume-card-kicker">Continue where you left off</p>
      {crumb && <p className="crumbs resume-card-crumb">{crumb}</p>}
      <p className="resume-card-title">{answer.title || answer.question_as_set || "Untitled question"}</p>
      <Link className="btn" to={`/answers/${answer.id}`}>
        Continue
      </Link>
    </div>
  );
}
