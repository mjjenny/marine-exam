import { useEffect, useRef, useState } from "react";

// Renders sketch thumbnails (with captions) that open a frosted full-screen lightbox.
// In the lightbox, click the image to toggle 2.5× zoom; while zoomed, move the mouse
// to pan. `refs` is an array of { path (storage key), caption }.
export default function SketchZoom({ refs }) {
  const [active, setActive] = useState(null); // the ref object being viewed
  const [zoomed, setZoomed] = useState(false);
  const [origin, setOrigin] = useState("center center");
  const imgRef = useRef(null);

  useEffect(() => {
    const onKey = (e) => e.key === "Escape" && setActive(null);
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  useEffect(() => {
    // reset zoom each time a new sketch opens
    setZoomed(false);
    setOrigin("center center");
  }, [active]);

  if (!refs || refs.length === 0) return null;

  function onMove(e) {
    if (!zoomed || !imgRef.current) return;
    const r = imgRef.current.getBoundingClientRect();
    const x = ((e.clientX - r.left) / r.width) * 100;
    const y = ((e.clientY - r.top) / r.height) * 100;
    setOrigin(`${x}% ${y}%`);
  }

  return (
    <>
      <div className="sketch-row">
        {refs.map((r, i) => (
          <figure className="sketch-fig" key={r.path || i}>
            <button
              className="sketch-thumb-btn"
              onClick={() => setActive(r)}
              title="Click to zoom"
            >
              <img
                src={`/api/sketches/${r.path}`}
                alt={r.caption || "sketch"}
                className="sketch-thumb"
              />
            </button>
            {r.caption && <figcaption className="sketch-caption">{r.caption}</figcaption>}
          </figure>
        ))}
      </div>

      {active && (
        <div className="sketch-overlay" onClick={() => setActive(null)}>
          <figure className="sketch-stage" onClick={(e) => e.stopPropagation()}>
            <img
              ref={imgRef}
              src={`/api/sketches/${active.path}`}
              alt={active.caption || "sketch"}
              className={`sketch-full ${zoomed ? "is-zoomed" : ""}`}
              style={zoomed ? { transformOrigin: origin } : undefined}
              onClick={() => setZoomed((z) => !z)}
              onMouseMove={onMove}
            />
            {active.caption && <figcaption className="sketch-full-caption">{active.caption}</figcaption>}
            <button
              className="sketch-close"
              onClick={() => setActive(null)}
              aria-label="Close sketch"
            >
              ✕
            </button>
          </figure>
        </div>
      )}
    </>
  );
}
