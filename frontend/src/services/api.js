/**
 * Axios API client configured for the FastAPI backend.
 * All API calls go through this client.
 *
 * withCredentials: true ensures the browser sends the httpOnly `access_token`
 * cookie on every request — JWT is NEVER stored in localStorage.
 */

import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true, // Send httpOnly auth cookie on every request
  timeout: 30000, // 30s global default (AI endpoints may be slower)
});

/**
 * Response interceptor: normalize errors while preserving HTTP status.
 *
 * We re-throw an Error with a human-readable message BUT also attach
 * `error.status` so callers (e.g. AuthContext) can distinguish a genuine
 * 401 Unauthorized from a network timeout or server error.
 *
 * This prevents transient backend failures from being misidentified as
 * authentication failures and triggering spurious logouts.
 */
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const message =
      error.response?.data?.detail ||
      error.response?.data?.message ||
      error.message ||
      'An unexpected error occurred';

    const normalizedError = new Error(message);
    // Preserve the HTTP status so callers can inspect it
    normalizedError.status = error.response?.status ?? null;
    // Preserve the full response for callers that need it
    normalizedError.response = error.response ?? null;
    return Promise.reject(normalizedError);
  }
);

export default apiClient;

// ===========================
// Auth API
// ===========================

export const authApi = {
  register: (data) => apiClient.post('/auth/register', data).then((r) => r.data),
  login: (data) => apiClient.post('/auth/login', data).then((r) => r.data),
  logout: () => apiClient.post('/auth/logout').then((r) => r.data),
  me: () => apiClient.get('/auth/me').then((r) => r.data),
  forgotPassword: (data) => apiClient.post('/auth/forgot-password', data).then((r) => r.data),
  verifyOTP: (data) => apiClient.post('/auth/verify-otp', data).then((r) => r.data),
  resetPassword: (data) => apiClient.post('/auth/reset-password', data).then((r) => r.data),
};

// ===========================
// Dashboard API
// ===========================

export const dashboardApi = {
  get: () => apiClient.get('/dashboard').then((r) => r.data),
};

// ===========================
// Groups API
// ===========================

export const groupsApi = {
  list: () => apiClient.get('/groups').then((r) => r.data),
  create: (data) => apiClient.post('/groups', data).then((r) => r.data),
  get: (id) => apiClient.get(`/groups/${id}`).then((r) => r.data),
  update: (id, data) => apiClient.patch(`/groups/${id}`, data).then((r) => r.data),
  delete: (id) => apiClient.delete(`/groups/${id}`),

  // Members — add by email (registered users only)
  addMember: (groupId, data) => apiClient.post(`/groups/${groupId}/members`, data).then((r) => r.data),
  removeMember: (groupId, userId) => apiClient.delete(`/groups/${groupId}/members/${userId}`),
};

// ===========================
// Expenses API
// ===========================

export const expensesApi = {
  list: (groupId) => apiClient.get(`/groups/${groupId}/expenses`).then((r) => r.data),
  create: (groupId, data) => apiClient.post(`/groups/${groupId}/expenses`, data).then((r) => r.data),
  update: (expenseId, data) => apiClient.patch(`/expenses/${expenseId}`, data).then((r) => r.data),
  delete: (expenseId) => apiClient.delete(`/expenses/${expenseId}`),
  // AI parse
  parseAI: (groupId, data) => apiClient.post(`/groups/${groupId}/expenses/parse-ai`, data).then((r) => r.data),
};

// ===========================
// Balances & Settlements API
// ===========================

export const balancesApi = {
  getBalances: (groupId) => apiClient.get(`/groups/${groupId}/balances`).then((r) => r.data),
  listSettlements: (groupId) => apiClient.get(`/groups/${groupId}/settlements`).then((r) => r.data),
  recordSettlement: (groupId, data) =>
    apiClient.post(`/groups/${groupId}/settlements`, data).then((r) => r.data),
  updateSettlement: (settlementId, data) =>
    apiClient.patch(`/settlements/${settlementId}`, data).then((r) => r.data),
};

// ===========================
// Notifications API
// ===========================

export const notificationsApi = {
  list: () => apiClient.get('/notifications').then((r) => r.data),
  markRead: (id) => apiClient.patch(`/notifications/${id}/read`).then((r) => r.data),
  markAllRead: () => apiClient.post('/notifications/read-all').then((r) => r.data),
};

// ===========================
// Profile / User API
// ===========================

export const profileApi = {
  get: () => apiClient.get('/users/me').then((r) => r.data),
  update: (data) => apiClient.patch('/users/me', data).then((r) => r.data),
};

// ===========================
// AI API (legacy fallback)
// ===========================

export const aiApi = {
  // New endpoint routed per-group
  parseExpense: (groupId, data) => expensesApi.parseAI(groupId, data),
};

// ===========================
// Insights API
// ===========================

export const insightsApi = {
  getGroupInsights: (groupId) =>
    apiClient.get(`/groups/${groupId}/insights`).then((r) => r.data),
  getAIInsights: (groupId, stats) =>
    apiClient.post(`/groups/${groupId}/insights/ai`, { stats }).then((r) => r.data),
};
