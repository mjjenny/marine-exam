import { useEffect, useState } from "react";
import { isMastered, toggleMastered, onMasteryChange } from "../utils/mastery.js";

// A vintage rubber-stamp toggle (not a checkbox) that marks a canonical answer as
// "mastered". Drives the book's progress ribbon via the shared mastery store.
export default function MasteryToggle({ slug, answerId }) {
  const [mastered, setMastered] = useState(false);

  useEffect(() => {
    const sync = () => setMastered(isMastered(slug, answerId));
    sync();
    return onMasteryChange(sync);
  }, [slug, answerId]);

  return (
    <button
      type="button"
      className={`mastery-stamp ${mastered ? "is-mastered" : ""}`}
      aria-pressed={mastered}
      onClick={() => setMastered(toggleMastered(slug, answerId))}
      title={mastered ? "Mastered — click to unmark" : "Mark this answer as mastered"}
    >
      <span className="mastery-stamp-inner">
        {mastered ? "✦ Mastered" : "Mark mastered"}
      </span>
    </button>
  );
}
