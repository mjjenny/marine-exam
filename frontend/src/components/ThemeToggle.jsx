import { useEffect, useState } from "react";

const KEY = "era-theme";
const EVENT = "era-theme-change";

export function getTheme() {
  if (typeof window === "undefined") return "dark";
  return localStorage.getItem(KEY) === "light" ? "light" : "dark";
}

export function applyTheme(theme) {
  const next = theme === "light" ? "light" : "dark";
  const root = document.documentElement;
  if (next === "dark") {
    root.classList.add("dark");
    root.classList.remove("light");
  } else {
    root.classList.add("light");
    root.classList.remove("dark");
  }
  localStorage.setItem(KEY, next);
  window.dispatchEvent(new Event(EVENT));
  return next;
}

export function initTheme() {
  applyTheme(getTheme());
}

/** Persisted light/dark toggle for header and mobile nav. */
export default function ThemeToggle({ className = "" }) {
  const [theme, setTheme] = useState(() => getTheme());

  useEffect(() => {
    const sync = () => setTheme(getTheme());
    window.addEventListener(EVENT, sync);
    window.addEventListener("storage", sync);
    return () => {
      window.removeEventListener(EVENT, sync);
      window.removeEventListener("storage", sync);
    };
  }, []);

  function toggle() {
    setTheme(applyTheme(theme === "dark" ? "light" : "dark"));
  }

  const isDark = theme === "dark";

  return (
    <button
      type="button"
      className={`theme-toggle ${className}`}
      onClick={toggle}
      aria-pressed={isDark}
      aria-label={isDark ? "Switch to light mode" : "Switch to dark mode"}
      title={isDark ? "Light mode" : "Dark mode"}
    >
      {isDark ? "Light" : "Dark"}
    </button>
  );
}
