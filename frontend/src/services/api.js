/**
 * Axios API client configured for the FastAPI backend.
 * All API calls go through this client.
 */

import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000, // 30s (AI endpoints may be slower)
});

// Response interceptor: normalize errors
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const message =
      error.response?.data?.detail ||
      error.response?.data?.message ||
      error.message ||
      'An unexpected error occurred';
    return Promise.reject(new Error(message));
  }
);

export default apiClient;

// ===========================
// Groups API
// ===========================

export const groupsApi = {
  list: () => apiClient.get('/groups/').then((r) => r.data),
  create: (data) => apiClient.post('/groups/', data).then((r) => r.data),
  get: (id) => apiClient.get(`/groups/${id}`).then((r) => r.data),
  delete: (id) => apiClient.delete(`/groups/${id}`),

  // Members
  listMembers: (groupId) => apiClient.get(`/groups/${groupId}/members`).then((r) => r.data),
  addMember: (groupId, data) => apiClient.post(`/groups/${groupId}/members`, data).then((r) => r.data),
  removeMember: (groupId, memberId) => apiClient.delete(`/groups/${groupId}/members/${memberId}`),
};

// ===========================
// Expenses API
// ===========================

export const expensesApi = {
  list: (groupId) => apiClient.get(`/groups/${groupId}/expenses`).then((r) => r.data),
  create: (groupId, data) => apiClient.post(`/groups/${groupId}/expenses`, data).then((r) => r.data),
  get: (groupId, expenseId) => apiClient.get(`/groups/${groupId}/expenses/${expenseId}`).then((r) => r.data),
  delete: (groupId, expenseId) => apiClient.delete(`/groups/${groupId}/expenses/${expenseId}`),
};

// ===========================
// Balances & Settlements API
// ===========================

export const balancesApi = {
  getBalances: (groupId) => apiClient.get(`/groups/${groupId}/balances`).then((r) => r.data),
  listSettlements: (groupId) => apiClient.get(`/groups/${groupId}/settlements`).then((r) => r.data),
  recordSettlement: (groupId, data) => apiClient.post(`/groups/${groupId}/settlements`, data).then((r) => r.data),
  deleteSettlement: (groupId, settlementId) => apiClient.delete(`/groups/${groupId}/settlements/${settlementId}`),
};

// ===========================
// AI API
// ===========================

export const aiApi = {
  parseExpense: (data) => apiClient.post('/ai/parse-expense', data).then((r) => r.data),
};
