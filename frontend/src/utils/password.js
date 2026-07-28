// Password complexity policy — mirrors the backend (app/auth.py::validate_password):
// >= 8 chars with at least one uppercase, lowercase, digit and special character.
export const PASSWORD_RULES = [
  { label: "At least 8 characters", test: (p) => p.length >= 8 },
  { label: "One uppercase letter", test: (p) => /[A-Z]/.test(p) },
  { label: "One lowercase letter", test: (p) => /[a-z]/.test(p) },
  { label: "One number", test: (p) => /[0-9]/.test(p) },
  // "special" = any non-alphanumeric, non-space character
  { label: "One special character", test: (p) => /[^A-Za-z0-9\s]/.test(p) },
];

export function isPasswordValid(password) {
  return PASSWORD_RULES.every((r) => r.test(password || ""));
}
