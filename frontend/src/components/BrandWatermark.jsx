// Fixed brand watermark behind all content (replaces the old CAD ship wireframe).
export default function BrandWatermark() {
  return (
    <div className="app-bg" aria-hidden="true">
      <img
        className="app-bg-logo"
        src="/branding/animated-logo.png"
        alt=""
        width={512}
        height={512}
        decoding="async"
        fetchPriority="low"
        style={{
          opacity: 1,
          width: "500px",
          height: "500px",
          maxWidth: "90vw",
          animation: "spin 25s linear infinite",
        }}
      />
    </div>
  );
}
