import axios from "axios";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const api = axios.create({
  baseURL: `${API_URL}/api/v1`,
  headers: { "Content-Type": "application/json" },
});

// Request interceptor - attach token
api.interceptors.request.use((config) => {
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("access_token");
    if (token) config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor - handle 401, auto refresh
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config;
    if (error.response?.status === 401 && !original._retry) {
      original._retry = true;
      try {
        const refresh = localStorage.getItem("refresh_token");
        if (refresh) {
          const { data } = await axios.post(`${API_URL}/api/v1/auth/refresh`, {
            refresh_token: refresh,
          });
          localStorage.setItem("access_token", data.access_token);
          original.headers.Authorization = `Bearer ${data.access_token}`;
          return api(original);
        }
      } catch {
        localStorage.removeItem("access_token");
        localStorage.removeItem("refresh_token");
        window.location.href = "/auth/login";
      }
    }
    return Promise.reject(error);
  }
);

// =====================================================
// AUTH
// =====================================================
export const authApi = {
  login: (email: string, password: string) =>
    api.post("/auth/login", { email, password }).then((r) => r.data),
  register: (name: string, email: string, password: string) =>
    api.post("/auth/register", { name, email, password }).then((r) => r.data),
  googleLogin: (token: string) =>
    api.post("/auth/google", { token }).then((r) => r.data),
  forgotPassword: (email: string) =>
    api.post("/auth/forgot-password", { email }).then((r) => r.data),
  resetPassword: (token: string, new_password: string) =>
    api.post("/auth/reset-password", { token, new_password }).then((r) => r.data),
  me: () => api.get("/users/me").then((r) => r.data),
};

// =====================================================
// ACCOUNTS
// =====================================================
export const accountsApi = {
  list: () => api.get("/accounts").then((r) => r.data),
  create: (data: any) => api.post("/accounts", data).then((r) => r.data),
  update: (id: string, data: any) => api.patch(`/accounts/${id}`, data).then((r) => r.data),
  delete: (id: string) => api.delete(`/accounts/${id}`).then((r) => r.data),
};

// =====================================================
// CATEGORIES
// =====================================================
export const categoriesApi = {
  list: (type?: string) =>
    api.get("/categories", { params: type ? { type } : {} }).then((r) => r.data),
  create: (data: any) => api.post("/categories", data).then((r) => r.data),
  update: (id: string, data: any) => api.patch(`/categories/${id}`, data).then((r) => r.data),
  delete: (id: string) => api.delete(`/categories/${id}`).then((r) => r.data),
};

// =====================================================
// TRANSACTIONS
// =====================================================
export const transactionsApi = {
  list: (params?: any) => api.get("/transactions", { params }).then((r) => r.data),
  summary: (params?: any) => api.get("/transactions/summary", { params }).then((r) => r.data),
  create: (data: any) => api.post("/transactions", data).then((r) => r.data),
  update: (id: string, data: any) => api.patch(`/transactions/${id}`, data).then((r) => r.data),
  delete: (id: string) => api.delete(`/transactions/${id}`).then((r) => r.data),
  suggestCategory: (description: string) =>
    api.post("/transactions/suggest-category", { description }).then((r) => r.data),
};

// =====================================================
// IMPORTS
// =====================================================
export const importsApi = {
  upload: (file: File, account_id: string) => {
    const form = new FormData();
    form.append("file", file);
    form.append("account_id", account_id);
    return api.post("/imports/upload", form, {
      headers: { "Content-Type": "multipart/form-data" },
    }).then((r) => r.data);
  },
  history: () => api.get("/imports/history").then((r) => r.data),
};

// =====================================================
// SUBSCRIPTIONS
// =====================================================
export const subscriptionsApi = {
  list: () => api.get("/subscriptions").then((r) => r.data),
  detect: () => api.post("/subscriptions/detect").then((r) => r.data),
  update: (id: string, status: string) =>
    api.patch(`/subscriptions/${id}`, null, { params: { status } }).then((r) => r.data),
};

// =====================================================
// CASHFLOW
// =====================================================
export const cashflowApi = {
  predict: (days = 90) =>
    api.get("/cashflow/predict", { params: { days } }).then((r) => r.data),
};

// =====================================================
// AI
// =====================================================
export const aiApi = {
  chat: (message: string, conversation_id?: string) =>
    api.post("/ai/chat", { message, conversation_id }).then((r) => r.data),
  conversations: () => api.get("/ai/conversations").then((r) => r.data),
  getConversation: (id: string) => api.get(`/ai/conversations/${id}`).then((r) => r.data),
};

// =====================================================
// ANALYTICS
// =====================================================
export const analyticsApi = {
  monthlyComparison: (months = 6) =>
    api.get("/analytics/monthly-comparison", { params: { months } }).then((r) => r.data),
  categoryTrends: (months = 3) =>
    api.get("/analytics/category-trends", { params: { months } }).then((r) => r.data),
  cashflowStatement: (start_date: string, end_date: string) =>
    api.get("/reports/cashflow-statement", { params: { start_date, end_date } }).then((r) => r.data),
};

// =====================================================
// ADMIN
// =====================================================
export const adminApi = {
  stats: () => api.get("/admin/stats").then((r) => r.data),
  users: (params?: any) => api.get("/admin/users", { params }).then((r) => r.data),
  blockUser: (id: string) => api.patch(`/admin/users/${id}/block`).then((r) => r.data),
  resetUserPassword: (id: string) =>
    api.post(`/admin/users/${id}/reset-password`).then((r) => r.data),
  changeRole: (id: string, role: string) =>
    api.patch(`/admin/users/${id}/role`, null, { params: { role } }).then((r) => r.data),
  transactions: (params?: any) => api.get("/admin/transactions", { params }).then((r) => r.data),
  categories: () => api.get("/admin/categories").then((r) => r.data),
  auditLogs: (params?: any) => api.get("/admin/audit-logs", { params }).then((r) => r.data),
  imports: (params?: any) => api.get("/admin/imports", { params }).then((r) => r.data),
};
