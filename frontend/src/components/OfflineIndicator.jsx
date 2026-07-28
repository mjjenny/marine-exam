import { useEffect, useState } from "react";

/** Compact banner shown whenever the browser reports offline. */
export default function OfflineIndicator() {
  const [offline, setOffline] = useState(
    typeof navigator !== "undefined" ? !navigator.onLine : false
  );

  useEffect(() => {
    const flushQueue = () => {
      if (navigator.serviceWorker?.controller) {
        navigator.serviceWorker.controller.postMessage({ type: "FLUSH_OFFLINE_QUEUE" });
      }
    };

    const goOffline = () => setOffline(true);
    const goOnline = () => {
      setOffline(false);
      flushQueue();
    };

    window.addEventListener("offline", goOffline);
    window.addEventListener("online", goOnline);

    // Ask the SW to drain any leftover queue on mount if we're online.
    if (navigator.onLine) flushQueue();

    return () => {
      window.removeEventListener("offline", goOffline);
      window.removeEventListener("online", goOnline);
    };
  }, []);

  if (!offline) return null;

  return (
    <div className="offline-indicator" role="status" aria-live="polite">
      <span className="offline-indicator-dot" aria-hidden="true" />
      Offline Mode — showing cached exam data
    </div>
  );
}
