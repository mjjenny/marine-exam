// A fixed CAD-style skeletal wireframe of a tanker, drawn as a single lightweight
// inline SVG (vector — no images, no repaint on scroll). Sits behind all content
// globally as a bold ice-white "blueprint". Decorative only.
export default function WireframeBackground() {
  return (
    <div className="app-bg" aria-hidden="true">
      <svg
        viewBox="0 0 1400 520"
        preserveAspectRatio="xMidYMid meet"
        xmlns="http://www.w3.org/2000/svg"
      >
        <g
          fill="none"
          stroke="currentColor"
          strokeWidth="2.8"
          strokeLinejoin="round"
          strokeLinecap="round"
        >
          {/* waterline */}
          <line x1="60" y1="300" x2="1360" y2="300" strokeDasharray="16 11" strokeWidth="2" />

          {/* hull outline (bow to the right) */}
          <path d="M 250 232 L 1120 232 Q 1198 234 1242 300 L 1248 330 Q 1244 362 1176 362 L 300 362 Q 250 362 248 332 Z" />
          {/* bulbous bow */}
          <path d="M 1246 300 q 30 6 16 30 q -6 10 -18 6" strokeWidth="2.2" />
          {/* transom stern detail */}
          <line x1="250" y1="232" x2="248" y2="332" />

          {/* longitudinal stringers */}
          <line x1="252" y1="270" x2="1236" y2="270" strokeWidth="1.8" />
          <line x1="256" y1="316" x2="1210" y2="316" strokeWidth="1.8" />

          {/* transverse frame / station lines */}
          {[350, 450, 550, 650, 750, 850, 950, 1050, 1130].map((x) => (
            <line key={x} x1={x} y1="232" x2={x} y2="362" strokeWidth="1.8" />
          ))}

          {/* deck cargo hatches + manifold piping */}
          <line x1="440" y1="224" x2="1070" y2="224" strokeWidth="1.8" />
          {[470, 570, 670, 770, 870, 970].map((x) => (
            <g key={x}>
              <rect x={x} y="218" width="44" height="14" rx="2" strokeWidth="1.8" />
              <line x1={x + 22} y1="224" x2={x + 22} y2="232" strokeWidth="1.6" />
            </g>
          ))}

          {/* aft superstructure / bridge, funnel and mast */}
          <rect x="280" y="150" width="132" height="82" strokeWidth="2.2" />
          <rect x="300" y="120" width="92" height="30" strokeWidth="2" />
          <line x1="300" y1="176" x2="412" y2="176" strokeWidth="1.6" />
          <line x1="300" y1="204" x2="412" y2="204" strokeWidth="1.6" />
          <rect x="328" y="92" width="36" height="30" strokeWidth="2" />
          <line x1="262" y1="150" x2="262" y2="86" strokeWidth="2" />
          <line x1="248" y1="104" x2="290" y2="104" strokeWidth="1.6" />

          {/* LOA dimension line (CAD annotation) */}
          <g strokeWidth="1.6" stroke="currentColor">
            <line x1="248" y1="410" x2="1262" y2="410" />
            <line x1="248" y1="402" x2="248" y2="418" />
            <line x1="1262" y1="402" x2="1262" y2="418" />
          </g>
        </g>
      </svg>
    </div>
  );
}
