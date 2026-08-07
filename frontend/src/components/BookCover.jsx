import { useEffect, useState } from "react";
import { masteryPercent, onMasteryChange } from "../utils/mastery.js";

// A styled book cover — spine on the left, page edges on the right, foil title.
// Used both as the clickable "book on the shelf" (pass onClick) and as the flipping
// cover inside the opened book (no onClick). Shelf cards show an inline progress
// bar (or an inviting empty state); the corner ribbon remains for non-shelf uses.
function ribbonTier(pct) {
  if (pct >= 100) return "gold";
  if (pct >= 26) return "silver";
  return "grey";
}

export default function BookCover({ subject, onClick, showRibbon = true }) {
  const interactive = typeof onClick === "function";
  const [pct, setPct] = useState(0);
  const total = subject.answer_count || 0;
  const trackProgress = total > 0;

  useEffect(() => {
    if (!trackProgress) return;
    const recompute = () => setPct(masteryPercent(subject.slug, total));
    recompute();
    return onMasteryChange(recompute);
  }, [trackProgress, subject.slug, total]);

  const Tag = interactive ? "button" : "div";

  return (
    <Tag
      type={interactive ? "button" : undefined}
      className={`book-cover cover-${subject.slug}${interactive ? " book-cover-interactive" : ""}`}
      onClick={onClick}
      aria-label={interactive ? `Open ${subject.name}` : undefined}
      data-testid={interactive ? `subject-book-${subject.slug}` : undefined}
    >
      <span className="book-spine" aria-hidden="true" />
      <span className="book-edges" aria-hidden="true" />
      <div className="book-cover-face">
        <span className="book-cover-kicker">MCA · SQA</span>
        {interactive ? (
          <span className="book-cover-title">{subject.name}</span>
        ) : (
          <h3 className="book-cover-title">{subject.name}</h3>
        )}
        <span className="book-cover-rule" aria-hidden="true" />

        {interactive && trackProgress && pct > 0 && (
          <div className="book-cover-progress" aria-label={`${pct}% mastered`}>
            <div className="book-cover-progress-track">
              <span
                className="book-cover-progress-fill"
                style={{ width: `${pct}%` }}
              />
            </div>
            <span className="book-cover-progress-pct">{pct}%</span>
          </div>
        )}
        {interactive && trackProgress && pct === 0 && (
          <p className="book-cover-progress-empty">
            {total ? `${total} answers · start` : "Start here"}
          </p>
        )}
        {interactive && !trackProgress && (
          <p className="book-cover-progress-empty">Start here</p>
        )}

        <span className="book-cover-sub">
          {subject.is_oral ? "Oral · topic index" : "Question index"}
        </span>
      </div>
      {!interactive && showRibbon && trackProgress && pct > 0 && (
        <span
          className={`cover-ribbon ribbon-${ribbonTier(pct)}`}
          title={`${pct}% mastered`}
          aria-hidden="true"
        >
          {pct}%
        </span>
      )}
    </Tag>
  );
}
