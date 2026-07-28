import { useMemo, useState } from "react";

// Searchable entry (canonical-answer) picker with a "create new entry" toggle.
// Controlled: `value` is { canonical_answer_id, new_entry_title }. Exactly one is set
// (new_entry_title === null → mapping to an existing entry; otherwise creating one).
export default function EntrySelect({ entries, value, onChange, nextCode, usesEntryCodes }) {
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const creating = value.new_entry_title !== null && value.new_entry_title !== undefined;

  const selected = entries.find((e) => e.canonical_answer_id === value.canonical_answer_id);
  const label = (e) => (e.code ? `${e.code} · ${e.title}` : e.title);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    const list = q
      ? entries.filter((e) => `${e.code || ""} ${e.title}`.toLowerCase().includes(q))
      : entries;
    return list.slice(0, 60);
  }, [entries, query]);

  if (creating) {
    return (
      <div className="entry-select">
        <div className="entry-select-mode">
          <span className="entry-badge new">
            New entry{usesEntryCodes && nextCode ? ` · ${nextCode}` : ""}
          </span>
          <button
            type="button"
            className="link-btn"
            onClick={() => onChange({ canonical_answer_id: null, new_entry_title: null })}
          >
            ← map to existing
          </button>
        </div>
        <input
          className="admin-input"
          placeholder="New entry title (the topic this question covers)…"
          value={value.new_entry_title || ""}
          onChange={(e) =>
            onChange({ canonical_answer_id: null, new_entry_title: e.target.value })
          }
        />
      </div>
    );
  }

  return (
    <div className="entry-select">
      <div className="entry-select-mode">
        {selected ? (
          <span className="entry-badge">{label(selected)}</span>
        ) : (
          <span className="muted">No entry selected</span>
        )}
        <button
          type="button"
          className="link-btn"
          onClick={() => onChange({ canonical_answer_id: null, new_entry_title: "" })}
        >
          + create new entry
        </button>
      </div>
      <div className="combo">
        <input
          className="admin-input"
          placeholder="Search entry — code (E39) or keyword…"
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setOpen(true);
          }}
          onFocus={() => setOpen(true)}
          onBlur={() => setTimeout(() => setOpen(false), 150)}
        />
        {open && (
          <ul className="combo-list">
            {filtered.map((e) => (
              <li
                key={e.canonical_answer_id}
                onMouseDown={() => {
                  onChange({ canonical_answer_id: e.canonical_answer_id, new_entry_title: null });
                  setQuery("");
                  setOpen(false);
                }}
              >
                {e.code && <span className="entry-code">{e.code}</span>}
                <span className="combo-title">{e.title}</span>
              </li>
            ))}
            {filtered.length === 0 && <li className="muted combo-empty">No matching entries</li>}
          </ul>
        )}
      </div>
    </div>
  );
}
