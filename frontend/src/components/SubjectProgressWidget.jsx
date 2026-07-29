import { useEffect, useState } from "react";
import { api } from "../api/client.js";

function Ring({ percent, label }) {
  const size = 72;
  const stroke = 7;
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const offset = c - (Math.max(0, Math.min(100, percent)) / 100) * c;

  return (
    <div className="flex flex-col items-center gap-2 min-w-[5.5rem]">
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} aria-hidden="true">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke="var(--border)"
          strokeWidth={stroke}
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke="var(--amber-500)"
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={c}
          strokeDashoffset={offset}
          transform={`rotate(-90 ${size / 2} ${size / 2})`}
          className="transition-all duration-500"
        />
        <text
          x="50%"
          y="50%"
          dominantBaseline="central"
          textAnchor="middle"
          className="fill-[var(--ink)] text-[0.7rem] font-semibold"
          style={{ fontSize: "0.75rem", fontWeight: 700, fill: "var(--ink)" }}
        >
          {percent}%
        </text>
      </svg>
      <p className="text-xs text-center text-[var(--muted)] leading-tight max-w-[6rem]">
        {label}
      </p>
    </div>
  );
}

/** Subject completion rings for the home dashboard. */
export default function SubjectProgressWidget() {
  const [rows, setRows] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    api
      .progressSummary()
      .then(setRows)
      .catch((e) => setError(e.message));
  }, []);

  if (error) return null;
  if (!rows) {
    return <p className="muted text-sm mt-4">Loading progress…</p>;
  }
  if (!rows.length) return null;

  return (
    <section className="mt-6 mb-2" aria-labelledby="progress-heading">
      <h2 id="progress-heading" className="text-base font-semibold mb-3">
        Your progress
      </h2>
      <div className="flex flex-wrap gap-5 items-start">
        {rows.map((r) => (
          <Ring key={r.subject_id} percent={r.percent} label={r.name} />
        ))}
      </div>
    </section>
  );
}
