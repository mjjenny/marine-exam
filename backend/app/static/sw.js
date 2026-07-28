/* Engine Room Academy — static cache-first + API network-first + offline POST queue */
const STATIC_CACHE = "era-static-v3";
const API_CACHE = "era-api-v1";
const OFFLINE_URL = "/offline.html";
const PRECACHE_URLS = ["/offline.html", "/manifest.json"];
const SYNC_TAG = "exam-sync";
const DB_NAME = "era-offline";
const DB_VERSION = 1;
const QUEUE_STORE = "exam-queue";

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(STATIC_CACHE).then((cache) => cache.addAll(PRECACHE_URLS))
  );
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    (async () => {
      const keep = new Set([STATIC_CACHE, API_CACHE]);
      const keys = await caches.keys();
      await Promise.all(keys.filter((k) => !keep.has(k)).map((k) => caches.delete(k)));
      await self.clients.claim();
      await flushExamQueue();
    })()
  );
});

self.addEventListener("sync", (event) => {
  if (event.tag === SYNC_TAG) {
    event.waitUntil(flushExamQueue());
  }
});

self.addEventListener("message", (event) => {
  if (event.data?.type === "FLUSH_OFFLINE_QUEUE") {
    event.waitUntil(flushExamQueue());
  }
});

function isStaticAsset(url) {
  return (
    url.pathname.startsWith("/assets/") ||
    /\.(?:js|css|png|jpg|jpeg|gif|svg|webp|woff2?|ttf|ico)$/i.test(url.pathname)
  );
}

function isApiRequest(url) {
  return url.pathname.startsWith("/api/");
}

function isAuthApi(url) {
  return url.pathname.startsWith("/api/auth/");
}

/** Student writebacks we treat as offline "exam" submissions. */
function isQueueableExamPost(url) {
  if (!isApiRequest(url) || isAuthApi(url)) return false;
  return (
    /\/api\/answers\/\d+\/suggestions\/?$/.test(url.pathname) ||
    url.pathname === "/api/admin/questions" ||
    /\/api\/admin\/questions\/?$/.test(url.pathname)
  );
}

/* ── IndexedDB queue ─────────────────────────────────────── */

function openQueueDb() {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, DB_VERSION);
    req.onupgradeneeded = () => {
      const db = req.result;
      if (!db.objectStoreNames.contains(QUEUE_STORE)) {
        db.createObjectStore(QUEUE_STORE, { keyPath: "id", autoIncrement: true });
      }
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

function idbReq(request) {
  return new Promise((resolve, reject) => {
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

async function serializeRequest(request) {
  const headers = {};
  request.headers.forEach((value, key) => {
    // Let the browser set multipart boundaries on replay.
    if (key.toLowerCase() === "content-type" && value.includes("multipart/form-data")) {
      return;
    }
    headers[key] = value;
  });

  const contentType = request.headers.get("Content-Type") || "";
  if (contentType.includes("multipart/form-data") || contentType === "") {
    try {
      const formData = await request.clone().formData();
      const parts = [];
      for (const [key, value] of formData.entries()) {
        if (typeof File !== "undefined" && value instanceof File) {
          parts.push({
            kind: "file",
            key,
            fileName: value.name,
            type: value.type,
            lastModified: value.lastModified,
            buffer: await value.arrayBuffer(),
          });
        } else {
          parts.push({ kind: "field", key, value: String(value) });
        }
      }
      if (parts.length) {
        return {
          url: request.url,
          method: request.method,
          headers,
          bodyType: "form",
          parts,
          createdAt: Date.now(),
        };
      }
    } catch {
      /* fall through to text */
    }
  }

  const body = await request.clone().text();
  return {
    url: request.url,
    method: request.method,
    headers,
    bodyType: "text",
    body,
    createdAt: Date.now(),
  };
}

async function enqueueExamPost(request) {
  const record = await serializeRequest(request);
  const db = await openQueueDb();
  try {
    await idbReq(db.transaction(QUEUE_STORE, "readwrite").objectStore(QUEUE_STORE).add(record));
  } finally {
    db.close();
  }

  if (self.registration && "sync" in self.registration) {
    try {
      await self.registration.sync.register(SYNC_TAG);
    } catch {
      /* Background Sync unsupported — client online handler will flush */
    }
  }
}

async function rebuildRequest(record) {
  const init = {
    method: record.method || "POST",
    headers: { ...(record.headers || {}) },
    credentials: "same-origin",
  };

  if (record.bodyType === "form" && Array.isArray(record.parts)) {
    const formData = new FormData();
    for (const part of record.parts) {
      if (part.kind === "file") {
        const blob = new Blob([part.buffer], { type: part.type || "application/octet-stream" });
        formData.append(part.key, blob, part.fileName || "file");
      } else {
        formData.append(part.key, part.value);
      }
    }
    init.body = formData;
    delete init.headers["Content-Type"];
    delete init.headers["content-type"];
  } else if (record.body != null) {
    init.body = record.body;
  }

  return new Request(record.url, init);
}

async function flushExamQueue() {
  const db = await openQueueDb();
  let records;
  try {
    records = await idbReq(db.transaction(QUEUE_STORE, "readonly").objectStore(QUEUE_STORE).getAll());
  } finally {
    db.close();
  }

  if (!records?.length) return;

  for (const record of records) {
    try {
      const request = await rebuildRequest(record);
      const response = await fetch(request);
      if (!response.ok) {
        // Leave in queue for a later retry (auth/server errors may clear later).
        continue;
      }
      const db2 = await openQueueDb();
      try {
        await idbReq(
          db2.transaction(QUEUE_STORE, "readwrite").objectStore(QUEUE_STORE).delete(record.id)
        );
      } finally {
        db2.close();
      }
    } catch {
      // Still offline or transient failure — stop and wait for the next sync.
      break;
    }
  }

  const clients = await self.clients.matchAll({ type: "window", includeUncontrolled: true });
  for (const client of clients) {
    client.postMessage({ type: "OFFLINE_QUEUE_FLUSHED" });
  }
}

function queuedResponse() {
  return new Response(
    JSON.stringify({
      queued: true,
      offline: true,
      message: "Saved offline — will submit when you're back online.",
    }),
    {
      status: 202,
      headers: { "Content-Type": "application/json", "X-Offline-Queued": "1" },
    }
  );
}

function offlineApiResponse() {
  return new Response(JSON.stringify({ error: "Offline and no cached data available." }), {
    status: 503,
    headers: { "Content-Type": "application/json" },
  });
}

async function networkFirstApi(request) {
  try {
    const response = await fetch(request);
    if (response && response.ok && request.method === "GET") {
      const cache = await caches.open(API_CACHE);
      cache.put(request, response.clone());
    }
    return response;
  } catch {
    if (request.method === "GET") {
      const cached = await caches.match(request);
      if (cached) return cached;
    }
    return offlineApiResponse();
  }
}

async function handleExamPost(request) {
  try {
    return await fetch(request.clone());
  } catch {
    await enqueueExamPost(request);
    return queuedResponse();
  }
}

self.addEventListener("fetch", (event) => {
  const { request } = event;
  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;

  if (url.pathname === "/sw.js" || url.pathname === "/health") return;

  // API: POST exam submissions → network, else IndexedDB queue + background sync
  if (request.method === "POST" && isQueueableExamPost(url)) {
    event.respondWith(handleExamPost(request));
    return;
  }

  // Other API writes (auth, admin actions): try network; no silent queue
  if (request.method !== "GET" && isApiRequest(url)) {
    event.respondWith(
      fetch(request).catch(
        () =>
          new Response(JSON.stringify({ error: "You appear to be offline." }), {
            status: 503,
            headers: { "Content-Type": "application/json" },
          })
      )
    );
    return;
  }

  // API GETs (subjects, questions, answers, …): network-first, cache fallback
  if (request.method === "GET" && isApiRequest(url)) {
    event.respondWith(networkFirstApi(request));
    return;
  }

  if (request.method !== "GET") return;

  // Navigations: network-first, never pin HTML in the long-lived cache
  if (request.mode === "navigate") {
    event.respondWith(
      fetch(request).catch(() =>
        caches.match(OFFLINE_URL).then((offline) => offline || caches.match("/"))
      )
    );
    return;
  }

  // Hashed build assets and other static files: cache-first
  if (isStaticAsset(url)) {
    event.respondWith(
      caches.match(request).then((cached) => {
        if (cached) return cached;
        return fetch(request)
          .then((response) => {
            if (response && response.ok) {
              const copy = response.clone();
              caches.open(STATIC_CACHE).then((cache) => cache.put(request, copy));
            }
            return response;
          })
          .catch(() => cached);
      })
    );
  }
});
