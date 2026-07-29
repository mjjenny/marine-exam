import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../api/client.js";

/** Star toggle that bookmarks a content item via the study API. */
export default function BookmarkButton({ contentType, contentId, label }) {
  const [on, setOn] = useState(false);
  const [busy, setBusy] = useState(false);
  const [ready, setReady] = useState(false);
  // Bumped when a toggle starts so an in-flight listBookmarks cannot clobber state.
  const gen = useRef(0);

  useEffect(() => {
    let cancelled = false;
    const id = ++gen.current;
    setReady(false);
    setOn(false);
    api
      .listBookmarks(contentType)
      .then((items) => {
        if (cancelled || id !== gen.current) return;
        setOn(
          items.some(
            (i) =>
              i.content_type === contentType &&
              Number(i.content_id) === Number(contentId)
          )
        );
        setReady(true);
      })
      .catch(() => {
        if (cancelled || id !== gen.current) return;
        setReady(true);
      });
    return () => {
      cancelled = true;
    };
  }, [contentType, contentId]);

  const toggle = useCallback(async () => {
    if (busy || !ready) return;
    setBusy(true);
    gen.current += 1; // invalidate any pending listBookmarks apply
    const prev = on;
    setOn(!prev);
    try {
      const res = await api.toggleBookmark(contentType, Number(contentId));
      setOn(Boolean(res.bookmarked));
    } catch {
      setOn(prev);
    } finally {
      setBusy(false);
    }
  }, [busy, ready, on, contentType, contentId]);

  return (
    <button
      type="button"
      className={`bookmark-btn ${on ? "is-on" : ""}`}
      data-testid="bookmark-button"
      aria-pressed={on}
      aria-label={on ? "Remove bookmark" : "Bookmark for later"}
      title={on ? "Saved - click to remove" : "Save for later"}
      disabled={busy || !ready}
      onClick={toggle}
    >
      <span aria-hidden="true">{on ? "★" : "☆"}</span>
      {label ? <span className="bookmark-btn-label">{label}</span> : null}
    </button>
  );
}
