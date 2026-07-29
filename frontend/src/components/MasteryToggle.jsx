import { useCallback, useEffect, useState } from "react";
import { api } from "../api/client.js";
import { isMastered, toggleMastered, onMasteryChange } from "../utils/mastery.js";

/**
 * Mark-as-complete control for a canonical answer.
 * Dual-writes to the server progress API and the local mastery store (book ribbon).
 */
export default function MasteryToggle({ slug, answerId }) {
  const [mastered, setMastered] = useState(false);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    const sync = () => setMastered(isMastered(slug, answerId));
    sync();
    return onMasteryChange(sync);
  }, [slug, answerId]);

  // Hydrate from server progress list (answer content_type).
  useEffect(() => {
    let cancelled = false;
    api
      .listProgress("answer")
      .then((items) => {
        if (cancelled) return;
        const on = items.some(
          (i) => i.content_type === "answer" && Number(i.content_id) === Number(answerId)
        );
        if (on !== isMastered(slug, answerId)) {
          // Align local store without flipping twice.
          if (on && !isMastered(slug, answerId)) toggleMastered(slug, answerId);
          if (!on && isMastered(slug, answerId)) toggleMastered(slug, answerId);
        }
        setMastered(on || isMastered(slug, answerId));
      })
      .catch(() => {
        /* offline / unauthenticated — keep local mastery */
      });
    return () => {
      cancelled = true;
    };
  }, [slug, answerId]);

  const onToggle = useCallback(async () => {
    if (busy) return;
    setBusy(true);
    const next = toggleMastered(slug, answerId);
    setMastered(next);
    try {
      const res = await api.toggleProgress("answer", Number(answerId));
      // Server is source of truth if it disagrees (rare race).
      if (Boolean(res.completed) !== next) {
        toggleMastered(slug, answerId);
        setMastered(Boolean(res.completed));
      }
    } catch {
      /* keep optimistic local state */
    } finally {
      setBusy(false);
    }
  }, [busy, slug, answerId]);

  return (
    <button
      type="button"
      className={`mastery-stamp ${mastered ? "is-mastered" : ""}`}
      aria-pressed={mastered}
      disabled={busy}
      onClick={onToggle}
      title={mastered ? "Completed — click to unmark" : "Mark as complete"}
    >
      <span className="mastery-stamp-inner">
        {mastered ? "Complete" : "Mark as Complete"}
      </span>
    </button>
  );
}
