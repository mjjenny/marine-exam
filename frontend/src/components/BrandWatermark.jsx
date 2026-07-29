// Fixed brand watermark behind all content (pre-animated WebP logo).
export default function BrandWatermark() {
  return (
    <div className="app-bg" aria-hidden="true">
      <img
        className="w-[350px] md:w-[500px] lg:w-[700px] max-w-[95vw] h-auto pointer-events-auto transition-transform duration-300 ease-in-out hover:scale-105"
        src="/branding/engine_room_academy_slow_spin.webp"
        alt=""
        width={512}
        height={512}
        decoding="async"
        fetchPriority="low"
        style={{ filter: "drop-shadow(0 0 18px rgba(180, 120, 60, 0.25))" }}
      />
    </div>
  );
}
