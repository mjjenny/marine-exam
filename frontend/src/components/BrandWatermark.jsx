// Fixed, faded brand watermark behind all content (replaces the old CAD ship wireframe).
export default function BrandWatermark() {
  return (
    <div className="app-bg" aria-hidden="true">
      <picture>
        <source srcSet="/branding/logo.webp" type="image/webp" />
        <img
          className="app-bg-logo"
          src="/branding/logo.png"
          alt=""
          width={512}
          height={512}
          decoding="async"
          fetchPriority="low"
        />
      </picture>
    </div>
  );
}
