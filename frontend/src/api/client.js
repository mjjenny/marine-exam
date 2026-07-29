// Thin fetch wrapper. Session cookies flow automatically (same-origin via Vite proxy).
const BASE = "/api";

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

async function request(path, options = {}) {
  const isForm = options.body instanceof FormData;
  const res = await fetch(path.startsWith("/") ? path : `${BASE}/${path}`, {
    credentials: "same-origin",
    // Let the browser set the multipart boundary for FormData bodies.
    headers: {
      ...(isForm ? {} : { "Content-Type": "application/json" }),
      ...(options.headers || {}),
    },
    ...options,
  });
  if (!res.ok) {
    let message = `${res.status} ${res.statusText}`;
    try {
      const body = await res.json();
      if (body && body.error) message = body.error;
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(message, res.status);
  }
  return res.status === 204 ? null : res.json();
}

export const api = {
  health: () => request("/health"),

  // Auth
  signup: (email, password) =>
    request("/api/auth/signup", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),
  login: (email, password) =>
    request("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),
  logout: () => request("/api/auth/logout", { method: "POST" }),
  me: () => request("/api/auth/me"),
  forgotPassword: (email) =>
    request("/api/auth/forgot-password", {
      method: "POST",
      body: JSON.stringify({ email }),
    }),
  resetPassword: (token, password) =>
    request("/api/auth/reset-password", {
      method: "POST",
      body: JSON.stringify({ token, password }),
    }),
  changePassword: (currentPassword, newPassword) =>
    request("/api/auth/change-password", {
      method: "POST",
      body: JSON.stringify({
        current_password: currentPassword,
        new_password: newPassword,
      }),
    }),

  // Study QoL — progress & bookmarks
  listProgress: (contentType) =>
    request(
      `/api/progress${contentType ? `?content_type=${encodeURIComponent(contentType)}` : ""}`
    ),
  toggleProgress: (contentType, contentId) =>
    request("/api/progress/toggle", {
      method: "POST",
      body: JSON.stringify({ content_type: contentType, content_id: contentId }),
    }),
  listBookmarks: (contentType) =>
    request(
      `/api/bookmarks${contentType ? `?content_type=${encodeURIComponent(contentType)}` : ""}`
    ),
  toggleBookmark: (contentType, contentId) =>
    request("/api/bookmarks/toggle", {
      method: "POST",
      body: JSON.stringify({ content_type: contentType, content_id: contentId }),
    }),

  // Content
  subjects: () => request("/api/subjects"),
  subject: (slug) => request(`/api/subjects/${encodeURIComponent(slug)}`),
  subjectIndex: (slug) => request(`/api/subjects/${encodeURIComponent(slug)}/index`),
  diets: (slug) => request(`/api/subjects/${encodeURIComponent(slug)}/diets`),
  diet: (id) => request(`/api/diets/${id}`),
  question: (id) => request(`/api/questions/${id}`),
  answer: (id) => request(`/api/answers/${id}`),
  topicQuestions: (topicId) => request(`/api/topics/${topicId}/questions`),
  subjectQuestions: (slug, { topicId, q } = {}) => {
    const params = new URLSearchParams();
    if (topicId != null) params.set("topic_id", topicId);
    if (q) params.set("q", q);
    const qs = params.toString();
    return request(
      `/api/subjects/${encodeURIComponent(slug)}/questions${qs ? `?${qs}` : ""}`
    );
  },

  // Admin
  adminUsers: (status) =>
    request(`/api/admin/users${status ? `?status=${encodeURIComponent(status)}` : ""}`),
  adminPendingCount: () => request("/api/admin/pending-count"),
  approveUser: (id) => request(`/api/admin/users/${id}/approve`, { method: "POST" }),
  rejectUser: (id) => request(`/api/admin/users/${id}/reject`, { method: "POST" }),
  revokeUser: (id) => request(`/api/admin/users/${id}/revoke`, { method: "POST" }),

  // Suggestions
  submitSuggestion: (answerId, suggestedText, files = []) => {
    if (files && files.length) {
      const fd = new FormData();
      fd.append("suggested_text", suggestedText);
      for (const f of files) fd.append("sketches", f);
      return request(`/api/answers/${answerId}/suggestions`, { method: "POST", body: fd });
    }
    return request(`/api/answers/${answerId}/suggestions`, {
      method: "POST",
      body: JSON.stringify({ suggested_text: suggestedText }),
    });
  },

  // Admin moderation
  adminSuggestions: (status) =>
    request(`/api/admin/suggestions${status ? `?status=${encodeURIComponent(status)}` : ""}`),
  approveSuggestion: (id, finalText) =>
    request(`/api/admin/suggestions/${id}/approve`, {
      method: "POST",
      body: JSON.stringify({ final_text: finalText }),
    }),
  rejectSuggestion: (id) =>
    request(`/api/admin/suggestions/${id}/reject`, { method: "POST" }),

  // Admin — Add Diet (manual + PDF)
  adminEntries: (subjectSlug) =>
    request(`/api/admin/entries?subject=${encodeURIComponent(subjectSlug)}`),
  adminAddQuestions: (payload) =>
    request("/api/admin/questions", { method: "POST", body: JSON.stringify(payload) }),
  adminParsePdf: (file) => {
    const fd = new FormData();
    fd.append("file", file);
    return request("/api/admin/parse-pdf", { method: "POST", body: fd });
  },
};
