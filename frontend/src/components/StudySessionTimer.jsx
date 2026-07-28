import { useEffect, useRef, useState } from "react";

// A minimalist study-session stopwatch for the open book's left page.
// Digital clock face + Start/Pause and Reset. Purely local; nothing persisted.
function fmt(totalSeconds) {
  const h = Math.floor(totalSeconds / 3600);
  const m = Math.floor((totalSeconds % 3600) / 60);
  const s = totalSeconds % 60;
  const pad = (n) => String(n).padStart(2, "0");
  return `${pad(h)}:${pad(m)}:${pad(s)}`;
}

export default function StudySessionTimer() {
  const [seconds, setSeconds] = useState(0);
  const [running, setRunning] = useState(false);
  const tick = useRef(null);

  useEffect(() => {
    if (running) {
      tick.current = setInterval(() => setSeconds((s) => s + 1), 1000);
      return () => clearInterval(tick.current);
    }
  }, [running]);

  return (
    <div className="study-timer">
      <span className="study-timer-label">Study session</span>
      <div className="study-timer-face" aria-live="off">
        {fmt(seconds)}
      </div>
      <div className="study-timer-controls">
        <button
          className="study-timer-btn"
          onClick={() => setRunning((r) => !r)}
          aria-pressed={running}
        >
          {running ? "Pause" : seconds ? "Resume" : "Start"}
        </button>
        <button
          className="study-timer-btn ghost"
          onClick={() => {
            setRunning(false);
            setSeconds(0);
          }}
          disabled={!seconds && !running}
        >
          Reset
        </button>
      </div>
    </div>
  );
}
