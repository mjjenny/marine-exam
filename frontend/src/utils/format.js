// Question-number label. Imported banks store it as "Q3"; older/dev data as "3".
// Normalise so we never double the "Q" (avoids "QQ3") or drop it.
export function qLabel(n) {
  if (n == null || n === "") return "";
  const s = String(n).trim();
  return /^q/i.test(s) ? s : `Q${s}`;
}
