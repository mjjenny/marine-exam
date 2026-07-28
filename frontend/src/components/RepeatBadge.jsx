// "↺N" badge marking a question that recurs across N diets — for spotting
// high-repeat "banker" questions at a glance. Hovering lists the diets.
export default function RepeatBadge({ diets }) {
  if (!diets || diets.length < 2) return null;
  return (
    <span
      className="repeat-badge"
      title={`Recurs in ${diets.length} diets: ${diets.join(", ")}`}
    >
      ↺{diets.length}
    </span>
  );
}
