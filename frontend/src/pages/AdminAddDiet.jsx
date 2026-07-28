import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../api/client.js";
import { useToast } from "../components/Toast.jsx";
import EntrySelect from "../components/EntrySelect.jsx";

const MONTHS = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
];
const NOW = new Date();
const YEARS = Array.from({ length: 18 }, (_, i) => 2015 + i); // 2015–2032
const EMPTY_ENTRY = { canonical_answer_id: null, new_entry_title: null };

export default function AdminAddDiet() {
  const toast = useToast();
  const [subjects, setSubjects] = useState([]);
  const [subject, setSubject] = useState("");
  const [entryData, setEntryData] = useState({ entries: [], next_code: null, uses_entry_codes: false });

  const [month, setMonth] = useState(NOW.getMonth() + 1);
  const [year, setYear] = useState(NOW.getFullYear());
  const [mode, setMode] = useState("manual");
  const [busy, setBusy] = useState(false);

  // manual form
  const [qnum, setQnum] = useState("");
  const [wording, setWording] = useState("");
  const [entry, setEntry] = useState(EMPTY_ENTRY);

  // pdf staging
  const [rows, setRows] = useState([]);
  const [parsing, setParsing] = useState(false);
  const [dragging, setDragging] = useState(false);
  const fileInput = useRef(null);

  useEffect(() => {
    api.subjects().then((s) => {
      setSubjects(s);
      if (s.length) setSubject(s[0].slug);
    });
  }, []);

  const loadEntries = useCallback((slug) => {
    if (!slug) return;
    api.adminEntries(slug).then(setEntryData).catch((e) => toast.error(e.message));
  }, [toast]);

  useEffect(() => {
    loadEntries(subject);
    // entries are subject-scoped — clear any stale mapping when the book changes
    setEntry(EMPTY_ENTRY);
    setRows((rs) => rs.map((r) => ({ ...r, entry: EMPTY_ENTRY })));
  }, [subject, loadEntries]);

  const dietLabel = `${MONTHS[month - 1]?.slice(0, 3)} ${year}`;

  async function submitManual() {
    if (!wording.trim()) return toast.error("Enter the question wording.");
    if (!entry.canonical_answer_id && !(entry.new_entry_title || "").trim())
      return toast.error("Map the question to an entry, or create a new one.");
    setBusy(true);
    try {
      const res = await api.adminAddQuestions({
        subject_slug: subject, month, year,
        items: [{
          question_number: qnum, wording,
          canonical_answer_id: entry.canonical_answer_id,
          new_entry_title: entry.new_entry_title,
        }],
      });
      const c = res.created[0];
      toast.success(`Added ${qnum || "question"} to ${res.diet.label}${c.code ? ` · ${c.code}` : ""}.`);
      setWording("");
      setQnum("");
      setEntry(EMPTY_ENTRY);
      loadEntries(subject); // a newly-created entry should appear in the picker
    } catch (e) {
      toast.error(e.message);
    } finally {
      setBusy(false);
    }
  }

  async function handleFile(file) {
    if (!file) return;
    if (!file.name.toLowerCase().endsWith(".pdf")) return toast.error("Please upload a PDF file.");
    setParsing(true);
    try {
      const res = await api.adminParsePdf(file);
      if (res.month) setMonth(res.month);
      if (res.year) setYear(res.year);
      setRows(
        (res.questions || []).map((q, i) => ({
          id: `r${Date.now()}-${i}`, number: q.number || "", wording: q.wording || "",
          entry: EMPTY_ENTRY,
        }))
      );
      if (res.warning) toast.info(res.warning);
      else toast.success(`Parsed ${res.questions.length} question(s)${res.diet_label ? ` from ${res.diet_label}` : ""}.`);
    } catch (e) {
      toast.error(e.message);
    } finally {
      setParsing(false);
    }
  }

  function updateRow(id, patch) {
    setRows((rs) => rs.map((r) => (r.id === id ? { ...r, ...patch } : r)));
  }
  function addRow() {
    setRows((rs) => [...rs, { id: `r${Date.now()}`, number: "", wording: "", entry: EMPTY_ENTRY }]);
  }
  function removeRow(id) {
    setRows((rs) => rs.filter((r) => r.id !== id));
  }

  async function commitStaging() {
    const usable = rows.filter((r) => r.wording.trim());
    if (!usable.length) return toast.error("Nothing to commit — add some question wording.");
    for (const r of usable) {
      if (!r.entry.canonical_answer_id && !(r.entry.new_entry_title || "").trim())
        return toast.error(`Map every question to an entry (check "${r.number || "a row"}").`);
    }
    setBusy(true);
    try {
      const res = await api.adminAddQuestions({
        subject_slug: subject, month, year,
        items: usable.map((r) => ({
          question_number: r.number, wording: r.wording,
          canonical_answer_id: r.entry.canonical_answer_id,
          new_entry_title: r.entry.new_entry_title,
        })),
      });
      toast.success(`Committed ${res.count} question(s) to ${res.diet.label}.`);
      setRows([]);
      loadEntries(subject);
    } catch (e) {
      toast.error(e.message);
    } finally {
      setBusy(false);
    }
  }

  const selectProps = {
    entries: entryData.entries,
    nextCode: entryData.next_code,
    usesEntryCodes: entryData.uses_entry_codes,
  };

  return (
    <div className="card admin-add">
      <h1>Add a Diet / Questions</h1>
      <p className="muted">
        Add exam questions to a sitting — manually, or by uploading an exam paper to
        parse. New questions appear in the book index straight away.
      </p>

      {/* shared: subject + diet date */}
      <div className="admin-grid">
        <label className="admin-field">
          Subject (book)
          <select className="admin-input" value={subject} onChange={(e) => setSubject(e.target.value)}>
            {subjects.map((s) => (
              <option key={s.slug} value={s.slug}>{s.name}</option>
            ))}
          </select>
        </label>
        <label className="admin-field">
          Diet month
          <select className="admin-input" value={month} onChange={(e) => setMonth(Number(e.target.value))}>
            {MONTHS.map((m, i) => (
              <option key={m} value={i + 1}>{m}</option>
            ))}
          </select>
        </label>
        <label className="admin-field">
          Diet year
          <select className="admin-input" value={year} onChange={(e) => setYear(Number(e.target.value))}>
            {YEARS.map((y) => (
              <option key={y} value={y}>{y}</option>
            ))}
          </select>
        </label>
        <div className="admin-field">
          Sitting
          <div className="diet-label-chip">{dietLabel}</div>
        </div>
      </div>

      <div className="admin-tabs">
        <button className={`admin-tab ${mode === "manual" ? "active" : ""}`} onClick={() => setMode("manual")}>
          Manual entry
        </button>
        <button className={`admin-tab ${mode === "pdf" ? "active" : ""}`} onClick={() => setMode("pdf")}>
          PDF upload
        </button>
      </div>

      {mode === "manual" ? (
        <div className="admin-panel">
          <div className="admin-grid">
            <label className="admin-field admin-field-narrow">
              Question no. <span className="hint">(optional)</span>
              <input
                className="admin-input"
                placeholder="e.g. Q12"
                value={qnum}
                onChange={(e) => setQnum(e.target.value)}
              />
            </label>
          </div>
          <label className="admin-field">
            Question as set <span className="hint">(verbatim wording)</span>
            <textarea
              className="admin-input admin-textarea"
              rows={5}
              placeholder="Paste the exact question, including its (a)/(b) parts and marks…"
              value={wording}
              onChange={(e) => setWording(e.target.value)}
            />
          </label>
          <div className="admin-field">
            Entry mapping
            <EntrySelect {...selectProps} value={entry} onChange={setEntry} />
          </div>
          <div className="admin-actions">
            <button className="btn" onClick={submitManual} disabled={busy}>
              {busy ? "Adding…" : "Add question"}
            </button>
          </div>
        </div>
      ) : (
        <div className="admin-panel">
          {rows.length === 0 ? (
            <div
              className={`dropzone ${dragging ? "dragging" : ""}`}
              onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
              onDragLeave={() => setDragging(false)}
              onDrop={(e) => { e.preventDefault(); setDragging(false); handleFile(e.dataTransfer.files[0]); }}
              onClick={() => fileInput.current?.click()}
            >
              <input
                ref={fileInput}
                type="file"
                accept="application/pdf,.pdf"
                hidden
                onChange={(e) => handleFile(e.target.files[0])}
              />
              <div className="dropzone-icon" aria-hidden="true">⬆</div>
              <p className="dropzone-title">{parsing ? "Parsing…" : "Drop an exam-paper PDF here"}</p>
              <p className="muted">or click to choose a file — we’ll extract the date and questions for review.</p>
            </div>
          ) : (
            <div className="staging">
              <div className="staging-head">
                <p className="muted">
                  Review the extracted questions, fix any typos, and map each to an entry.
                  Nothing is saved until you commit.
                </p>
                <button className="btn-ghost-dark btn-small" onClick={() => setRows([])}>
                  Discard &amp; upload another
                </button>
              </div>
              <ul className="staging-list">
                {rows.map((r) => (
                  <li key={r.id} className="staging-row">
                    <div className="staging-row-top">
                      <input
                        className="admin-input staging-qnum"
                        placeholder="Q#"
                        value={r.number}
                        onChange={(e) => updateRow(r.id, { number: e.target.value })}
                      />
                      <button
                        className="staging-remove"
                        onClick={() => removeRow(r.id)}
                        aria-label="Remove question"
                        title="Remove"
                      >
                        ✕
                      </button>
                    </div>
                    <textarea
                      className="admin-input admin-textarea"
                      rows={3}
                      value={r.wording}
                      onChange={(e) => updateRow(r.id, { wording: e.target.value })}
                    />
                    <EntrySelect
                      {...selectProps}
                      value={r.entry}
                      onChange={(entryVal) => updateRow(r.id, { entry: entryVal })}
                    />
                  </li>
                ))}
              </ul>
              <div className="admin-actions">
                <button className="btn-ghost-dark" onClick={addRow}>+ Add a row</button>
                <button className="btn" onClick={commitStaging} disabled={busy}>
                  {busy ? "Committing…" : `Commit ${rows.length} question(s)`}
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
