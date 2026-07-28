import { createContext, useCallback, useContext, useState } from "react";

// Lightweight toast notifications. Wrap the app in <ToastProvider>, then call
// useToast().success(msg) / .error(msg) from anywhere.
const ToastCtx = createContext(null);

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);

  const remove = useCallback((id) => {
    setToasts((t) => t.filter((x) => x.id !== id));
  }, []);

  const push = useCallback(
    (message, kind) => {
      const id = Date.now() + Math.random();
      setToasts((t) => [...t, { id, message, kind }]);
      setTimeout(() => remove(id), 4500);
    },
    [remove]
  );

  const api = {
    success: (m) => push(m, "success"),
    error: (m) => push(m, "error"),
    info: (m) => push(m, "info"),
  };

  return (
    <ToastCtx.Provider value={api}>
      {children}
      <div className="toast-stack" aria-live="polite">
        {toasts.map((t) => (
          <div key={t.id} className={`toast toast-${t.kind}`} role="status">
            <span className="toast-icon" aria-hidden="true">
              {t.kind === "success" ? "✓" : t.kind === "error" ? "!" : "i"}
            </span>
            <span className="toast-msg">{t.message}</span>
            <button className="toast-close" onClick={() => remove(t.id)} aria-label="Dismiss">
              ✕
            </button>
          </div>
        ))}
      </div>
    </ToastCtx.Provider>
  );
}

export function useToast() {
  const ctx = useContext(ToastCtx);
  if (!ctx) throw new Error("useToast must be used within a ToastProvider");
  return ctx;
}
