import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client.js";
import SketchZoom from "../components/SketchZoom.jsx";
import Markdown from "../components/Markdown.jsx";

// Admin suggested-edit moderation queue. Each pending suggestion is shown beside the
// live answer; approving publishes the (optionally edited) text, rejecting leaves the
// live answer untouched.
export default function AdminModeration() {
  const [items, setItems] = useState(null);
  const [error, setError] = useState(null);

  const load = useCallback(() => {
    setError(null);
    api.adminSuggestions("pending").then(setItems).catch((e) => setError(e.message));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  function removeItem(id) {
    setItems((prev) => prev.filter((s) => s.id !== id));
  }

  return (
    <div className="card">
      <p className="crumbs">
        <Link to="/">Home</Link> / Admin / Moderation
      </p>
      <h1>Suggested edits</h1>
      <p className="muted">
        Pending answer suggestions. Approving publishes the text and archives the
        previous version; rejecting leaves the live answer unchanged.
      </p>

      {error && <p className="form-error">{error}</p>}
      {!items && !error && <p>Loading…</p>}
      {items && items.length === 0 && (
        <p className="muted">No pending suggestions. All caught up.</p>
      )}

      {items?.map((s) => (
        <SuggestionCard key={s.id} suggestion={s} onDone={() => removeItem(s.id)} onError={setError} />
      ))}
    </div>
  );
}

function SuggestionCard({ suggestion: s, onDone, onError }) {
  const [finalText, setFinalText] = useState(s.suggested_text);
  const [busy, setBusy] = useState(false);

  async function approve() {
    if (!finalText.trim()) return;
    setBusy(true);
    onError(null);
    try {
      await api.approveSuggestion(s.id, finalText.trim());
      onDone();
    } catch (e) {
      onError(e.message);
      setBusy(false);
    }
  }

  async function reject() {
    setBusy(true);
    onError(null);
    try {
      await api.rejectSuggestion(s.id);
      onDone();
    } catch (e) {
      onError(e.message);
      setBusy(false);
    }
  }

  const edited = finalText.trim() !== s.suggested_text.trim();

  return (
    <div className="mod-card">
      <div className="mod-meta">
        <span className="chip">{s.answer.subject}</span>
        {s.answer.topic && <span className="chip">{s.answer.topic}</span>}
        <span className="muted">
          from {s.submitted_by} ·{" "}
          {s.submitted_at ? new Date(s.submitted_at).toLocaleString() : "—"}
        </span>
      </div>
      {s.answer.sample_question && (
        <p className="mod-question">{s.answer.sample_question}</p>
      )}

      <div className="mod-compare">
        <div className="mod-col">
          <h3>Current live answer</h3>
          <div className="mod-current">
            {s.answer.current_text ? (
              <Markdown>{s.answer.current_text}</Markdown>
            ) : (
              <em>(empty)</em>
            )}
          </div>
        </div>
        <div className="mod-col">
          <h3>
            Suggested {edited && <span className="edited-tag">(edited)</span>}
          </h3>
          <textarea
            className="mod-textarea"
            rows={8}
            value={finalText}
            onChange={(e) => setFinalText(e.target.value)}
          />
          {s.sketches?.length > 0 && (
            <div className="mod-sketches">
              <span className="muted">Attached sketches (published on approval):</span>
              <SketchZoom refs={s.sketches} />
            </div>
          )}
        </div>
      </div>

      <div className="mod-actions">
        <button className="btn btn-small btn-reject" disabled={busy} onClick={reject}>
          Reject
        </button>
        <button className="btn btn-small" disabled={busy || !finalText.trim()} onClick={approve}>
          {edited ? "Approve edited" : "Approve"}
        </button>
      </div>
    </div>
  );
}
