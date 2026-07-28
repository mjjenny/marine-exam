import { useEffect, useState } from "react";
import { api } from "../api/client.js";
import Markdown from "./Markdown.jsx";

// Modal for proposing answer text. Writes a pending suggested_edit; the live answer is
// untouched until an admin approves it. When `pending` (the entry has no published
// answer yet), the copy shifts from "suggest an improvement" to "submit an answer".
export default function SuggestModal({ answerId, currentAnswer, onClose, pending = false }) {
  const [text, setText] = useState("");
  const [files, setFiles] = useState([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [done, setDone] = useState(false);

  // Close on Escape.
  useEffect(() => {
    const onKey = (e) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  async function submit(e) {
    e.preventDefault();
    if (!text.trim()) return;
    setBusy(true);
    setError(null);
    try {
      await api.submitSuggestion(answerId, text.trim(), files);
      setDone(true);
    } catch (err) {
      setError(err.message || "Submission failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        {done ? (
          <>
            <h2>{pending ? "Answer submitted" : "Suggestion submitted"}</h2>
            <p className="muted">
              Thanks — your {pending ? "answer" : "suggestion"} is{" "}
              <strong>pending review</strong>. An administrator will review and, once
              approved, publish it to this entry.
            </p>
            <div className="modal-actions">
              <button className="btn" onClick={onClose}>
                Done
              </button>
            </div>
          </>
        ) : (
          <form onSubmit={submit}>
            <h2>{pending ? "Submit an answer" : "Suggest an improvement"}</h2>
            <p className="muted">
              {pending
                ? "No model answer has been published for this question yet. If you have a strong answer, share it below — an administrator will review and publish it to this entry."
                : "Propose improved text for this answer. An administrator will review it before anything changes."}
            </p>
            {!pending && currentAnswer && (
              <details className="current-answer">
                <summary>Show current answer</summary>
                <Markdown>{currentAnswer}</Markdown>
              </details>
            )}
            <label className="modal-label">
              {pending ? "Your answer" : "Your suggested answer"}
              <textarea
                rows={8}
                value={text}
                onChange={(e) => setText(e.target.value)}
                placeholder={
                  pending
                    ? "Type or paste your answer to this question…"
                    : "Type or paste your improved answer…"
                }
                autoFocus
              />
            </label>
            <label className="modal-label">
              Sketches <span className="hint">(optional — PNG/JPG/GIF/WebP, max 5 MB each)</span>
              <input
                type="file"
                accept="image/png,image/jpeg,image/gif,image/webp"
                multiple
                onChange={(e) => setFiles(Array.from(e.target.files))}
              />
            </label>
            {files.length > 0 && (
              <ul className="file-list">
                {files.map((f, i) => (
                  <li key={i}>
                    📎 {f.name}{" "}
                    <span className="muted">({Math.round(f.size / 1024)} KB)</span>
                  </li>
                ))}
              </ul>
            )}
            {error && <p className="form-error">{error}</p>}
            <div className="modal-actions">
              <button
                type="button"
                className="btn btn-ghost-dark"
                onClick={onClose}
                disabled={busy}
              >
                Cancel
              </button>
              <button className="btn" type="submit" disabled={busy || !text.trim()}>
                {busy ? "Submitting…" : pending ? "Submit answer" : "Submit suggestion"}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
