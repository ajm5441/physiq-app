// src/api/client.js
// Central API client — handles auth headers, token refresh, and error normalisation.

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000';

// ── Token storage ─────────────────────────────────────────────────────────────
export const tokenStore = {
  getAccess:  ()    => localStorage.getItem('physiq_access'),
  getRefresh: ()    => localStorage.getItem('physiq_refresh'),
  set: (access, refresh) => {
    localStorage.setItem('physiq_access',  access);
    localStorage.setItem('physiq_refresh', refresh);
  },
  clear: () => {
    localStorage.removeItem('physiq_access');
    localStorage.removeItem('physiq_refresh');
  },
};

// ── Core fetch wrapper ────────────────────────────────────────────────────────
let isRefreshing   = false;
let refreshQueue   = [];   // queued requests waiting for a fresh token

async function request(path, options = {}, retry = true) {
  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers || {}),
  };

  const token = tokenStore.getAccess();
  if (token) headers['Authorization'] = `Bearer ${token}`;

  const res = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers,
    body: options.body ? JSON.stringify(options.body) : undefined,
  });

  // ── Token expired — attempt refresh then retry ────────────────────────────
  if (res.status === 401 && retry) {
    const data = await res.json().catch(() => ({}));
    if (data.code === 'token_expired') {
      const refreshed = await _doRefresh();
      if (refreshed) return request(path, options, false);
      // Refresh failed — caller will receive the 401
    }
  }

  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: 'Unknown error' }));
    throw new APIError(err.error || 'Request failed', res.status, err);
  }

  return res.json();
}

async function _doRefresh() {
  if (isRefreshing) {
    // Queue this caller behind the in-flight refresh
    return new Promise(resolve => refreshQueue.push(resolve));
  }

  isRefreshing = true;
  try {
    const res = await fetch(`${BASE_URL}/auth/refresh`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ refresh_token: tokenStore.getRefresh() }),
    });

    if (!res.ok) {
      tokenStore.clear();
      refreshQueue.forEach(r => r(false));
      refreshQueue = [];
      return false;
    }

    const { access_token, refresh_token } = await res.json();
    tokenStore.set(access_token, refresh_token);
    refreshQueue.forEach(r => r(true));
    refreshQueue = [];
    return true;
  } finally {
    isRefreshing = false;
  }
}

export class APIError extends Error {
  constructor(message, status, body = {}) {
    super(message);
    this.status = status;
    this.body   = body;
  }
}

// ── Convenience methods ───────────────────────────────────────────────────────
export const api = {
  get:    (path)         => request(path, { method: 'GET' }),
  post:   (path, body)   => request(path, { method: 'POST',  body }),
  patch:  (path, body)   => request(path, { method: 'PATCH', body }),
  delete: (path)         => request(path, { method: 'DELETE' }),
};

// ── Auth endpoints ────────────────────────────────────────────────────────────
export const authAPI = {
  register: (username, email, password) =>
    api.post('/auth/register', { username, email, password }),

  login: (email, password) =>
    api.post('/auth/login', { email, password }),

  logout: () =>
    api.post('/auth/logout', {}),
};

// ── Dashboard ─────────────────────────────────────────────────────────────────
export const dashboardAPI = {
  get:    () => api.get('/dashboard'),
  topics: () => api.get('/dashboard/topics'),
};

// ── Topics & subtopics ────────────────────────────────────────────────────────
export const topicsAPI = {
  list:        ()         => api.get('/topics'),
  subtopics:   (topicId)  => api.get(`/topics/${topicId}/subtopics`),
};

// ── Sessions ──────────────────────────────────────────────────────────────────
export const sessionsAPI = {
  start:  (subtopicId)          => api.post('/sessions/start', { subtopic_id: subtopicId }),
  get:    (sessionId)           => api.get(`/sessions/${sessionId}`),
  answer: (sessionId, answer)   => api.post(`/sessions/${sessionId}/answer`, { answer }),
  close:  (sessionId)           => api.post(`/sessions/${sessionId}/close`, {}),
};

// ── Progress ──────────────────────────────────────────────────────────────────
export const progressAPI = {
  subtopics:     () => api.get('/progress/subtopics'),
  reviewHistory: () => api.get('/progress/review-history'),
};
