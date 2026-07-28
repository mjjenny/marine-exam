import { useEffect, useState } from "react";
import { masteryPercent, onMasteryChange } from "../utils/mastery.js";

// A styled book cover — a spine on the left, page edges on the right, foil title.
// Used both as the clickable "book on the shelf" (pass onClick) and as the flipping
// cover inside the opened book (no onClick). When showRibbon is set and the subject
// carries an answer_count, a bookmark ribbon hangs from the top showing mastery
// progress (grey → silver → gold), kept live via the mastery store.
function ribbonTier(pct) {
  if (pct >= 100) return "gold";
  if (pct >= 26) return "silver";
  return "grey";
}

export default function BookCover({ subject, onClick, showRibbon = true }) {
  const interactive = typeof onClick === "function";
  const [pct, setPct] = useState(0);
  const hasProgress = showRibbon && subject.answer_count > 0;

  useEffect(() => {
    if (!hasProgress) return;
    const recompute = () => setPct(masteryPercent(subject.slug, subject.answer_count));
    recompute();
    return onMasteryChange(recompute);
  }, [hasProgress, subject.slug, subject.answer_count]);

  return (
    <div
      className={`book-cover cover-${subject.slug}`}
      onClick={onClick}
      role={interactive ? "button" : undefined}
      tabIndex={interactive ? 0 : undefined}
      onKeyDown={
        interactive
          ? (e) => (e.key === "Enter" || e.key === " ") && (e.preventDefault(), onClick())
          : undefined
      }
      aria-label={interactive ? `Open ${subject.name}` : undefined}
    >
      <span className="book-spine" aria-hidden="true" />
      <span className="book-edges" aria-hidden="true" />
      <div className="book-cover-face">
        <span className="book-cover-kicker">MCA · SQA</span>
        <h3 className="book-cover-title">{subject.name}</h3>
        <span className="book-cover-rule" aria-hidden="true" />
        <span className="book-cover-sub">
          {subject.is_oral ? "Oral · topic index" : "Question index"}
        </span>
      </div>
      {hasProgress && pct > 0 && (
        <span
          className={`cover-ribbon ribbon-${ribbonTier(pct)}`}
          title={`${pct}% mastered`}
          aria-hidden="true"
        >
          {pct}%
        </span>
      )}
    </div>
  );
}
