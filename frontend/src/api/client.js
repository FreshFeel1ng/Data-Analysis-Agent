import axios from 'axios';

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const client = axios.create({
  baseURL: API_BASE,
  headers: { 'Content-Type': 'application/json' },
});

client.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

client.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      window.location.href = '/login';
    }
    return Promise.reject(err);
  }
);

export const api = {
  // Auth
  login: (data) => client.post('/api/auth/login', data),
  register: (data) => client.post('/api/auth/register', data),
  getMe: () => client.get('/api/auth/me'),

  // Query
  ask: (data) => client.post('/api/query/ask', data),

  // History
  getQueryHistory: (params) => client.get('/api/history/queries', { params }),

  // Training
  addTraining: (data) => client.post('/api/training/', data),
  listTrainings: (params) => client.get('/api/training/', { params }),
  deleteTraining: (id) => client.delete(`/api/training/${id}`),
  autoImportSchema: (dbConnectionId) =>
    client.post(`/api/training/auto-schema?db_connection_id=${dbConnectionId}`),

  // Connections
  createConnection: (data) => client.post('/api/connections/', data),
  listConnections: () => client.get('/api/connections/'),
  deleteConnection: (id) => client.delete(`/api/connections/${id}`),

  // Audit (admin)
  getAuditLogs: (params) => client.get('/api/history/audit', { params }),
};

export default client;
