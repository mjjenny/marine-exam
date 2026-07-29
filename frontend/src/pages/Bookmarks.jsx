import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client.js";

function hrefFor(item) {
  switch (item.content_type) {
    case "answer":
      return `/answers/${item.content_id}`;
    case "question":
      return `/questions/${item.content_id}`;
    case "topic":
      return `/topics/${item.content_id}`;
    case "diet":
      return `/diets/${item.content_id}`;
    case "subject":
      return `/subjects/${item.content_id}`;
    default:
      return "/";
  }
}

function titleFor(item) {
  const kind = item.content_type.charAt(0).toUpperCase() + item.content_type.slice(1);
  return `${kind} #${item.content_id}`;
}

export default function Bookmarks() {
  const [items, setItems] = useState(null);
  const [error, setError] = useState(null);
  const [busyId, setBusyId] = useState(null);

  function load() {
    setError(null);
    api
      .listBookmarks()
      .then(setItems)
      .catch((e) => setError(e.message));
  }

  useEffect(() => {
    load();
  }, []);

  async function remove(item) {
    setBusyId(item.id);
    try {
      await api.toggleBookmark(item.content_type, item.content_id);
      setItems((prev) => prev.filter((x) => x.id !== item.id));
    } catch (e) {
      setError(e.message);
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div className="card max-w-2xl mx-auto">
      <p className="crumbs">
        <Link to="/">Home</Link> / Bookmarks
      </p>
      <h1>Bookmarks</h1>
      <p className="muted">Items you saved for later.</p>

      {error && <p className="form-error">{error}</p>}
      {!items && !error && <p>Loading…</p>}
      {items && items.length === 0 && (
        <p className="muted mt-4">No bookmarks yet. Tap the star on a question or answer to save it.</p>
      )}

      {items && items.length > 0 && (
        <ul className="list mt-4">
          {items.map((item) => (
            <li key={item.id} className="flex items-center gap-2 justify-between border-b border-[var(--border)] py-3">
              <Link to={hrefFor(item)} className="list-row flex-1">
                <span>{titleFor(item)}</span>
                <span className="chip capitalize">{item.content_type}</span>
              </Link>
              <button
                type="button"
                className="btn btn-small btn-ghost"
                disabled={busyId === item.id}
                onClick={() => remove(item)}
              >
                Remove
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
