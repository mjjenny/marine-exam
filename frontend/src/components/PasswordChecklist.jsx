import { PASSWORD_RULES } from "../utils/password.js";

// Live checklist of the password-complexity rules; each turns green as it's met.
// Only render once the user has started typing (pass the current password value).
export default function PasswordChecklist({ password }) {
  if (!password) return null;
  return (
    <ul className="pw-checklist" aria-label="Password requirements">
      {PASSWORD_RULES.map((r) => {
        const ok = r.test(password);
        return (
          <li key={r.label} className={ok ? "pw-ok" : "pw-todo"}>
            <span aria-hidden="true">{ok ? "✓" : "○"}</span> {r.label}
          </li>
        );
      })}
    </ul>
  );
}
