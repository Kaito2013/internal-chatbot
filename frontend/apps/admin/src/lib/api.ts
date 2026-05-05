import axios, { AxiosInstance, AxiosError } from 'axios';

// API Base URL - relative path for Next.js rewrites
const API_BASE = process.env.NEXT_PUBLIC_API_URL || '';

// Create axios instance
const api: AxiosInstance = axios.create({
  baseURL: API_BASE,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Token storage
const TOKEN_KEY = 'admin_token';
const USER_KEY = 'admin_user';

// Token management
export const tokenStorage = {
  get: (): string | null => {
    if (typeof window === 'undefined') return null;
    return localStorage.getItem(TOKEN_KEY);
  },
  
  set: (token: string) => {
    localStorage.setItem(TOKEN_KEY, token);
  },
  
  remove: () => {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
  },
};

// User type
export interface AdminUser {
  id: number;
  username: string;
  is_superadmin: boolean;
  can_upload: boolean;
  can_delete: boolean;
  can_view_stats: boolean;
}

// Auth responses
export interface LoginResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: AdminUser;
}

// Document types
export interface Document {
  id: number;
  source: string;
  filename: string;
  file_type: string;
  file_size: number;
  chunk_count: number;
  chunk_strategy: string;
  processing_time_ms: number;
  uploaded_at: string;
  last_ingested_at: string;
  is_active: boolean;
}

export interface DocumentListResponse {
  documents: Document[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

// Session types
export interface Session {
  id: string;
  user_id: string | null;
  username: string | null;
  created_at: string;
  updated_at: string;
  message_count: number;
  is_active: boolean;
}

export interface ChatLog {
  id: number;
  session_id: string;
  role: string;
  question: string;
  answer: string;
  sources_json: string | null;
  tokens_input: number;
  tokens_output: number;
  model_used: string;
  mode: string;
  used_crm: boolean;
  latency_ms: number;
  created_at: string;
}

export interface SessionDetail {
  id: string;
  user_id: string | null;
  username: string | null;
  created_at: string;
  updated_at: string;
  message_count: number;
  is_active: boolean;
  messages: ChatLog[];
}

export interface SessionListResponse {
  sessions: Session[];
  total: number;
  page: number;
  page_size: number;
}

export interface SessionSearchResponse {
  sessions: Session[];
  total: number;
  query: string;
}

// Stats types
export interface TokenStats {
  total_input_tokens: number;
  total_output_tokens: number;
  total_tokens: number;
  avg_input_tokens: number;
  avg_output_tokens: number;
}

export interface OverviewStats {
  total_sessions: number;
  total_messages: number;
  total_users: number;
  total_documents: number;
  total_chunks: number;
  avg_latency_ms: number;
  token_stats: TokenStats;
  period_days: number;
}

export interface TokenUsageDataPoint {
  date: string;
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
  request_count: number;
}

export interface TokenUsageResponse {
  period: string;
  data: TokenUsageDataPoint[];
  total_input_tokens: number;
  total_output_tokens: number;
  total_requests: number;
}

export interface RAGEffectivenessDataPoint {
  date: string;
  rag_requests: number;
  total_requests: number;
  effectiveness_rate: number;
}

export interface RAGEffectivenessResponse {
  period: string;
  data: RAGEffectivenessDataPoint[];
  overall_effectiveness_rate: number;
  total_rag_requests: number;
  total_requests: number;
}

export interface TopSource {
  source: string;
  filename: string;
  reference_count: number;
  last_referenced: string;
}

export interface TopSourcesResponse {
  sources: TopSource[];
  period: string;
}

// API Client functions
export const apiClient = {
  // Auth
  login: async (username: string, password: string): Promise<LoginResponse> => {
    const res = await api.post<LoginResponse>('/api/admin/auth/login', { username, password });
    tokenStorage.set(res.data.access_token);
    localStorage.setItem(USER_KEY, JSON.stringify(res.data.user));
    return res.data;
  },
  
  verifyToken: async (): Promise<{ valid: boolean; user: AdminUser }> => {
    const token = tokenStorage.get();
    if (!token) throw new Error('No token');
    
    api.defaults.headers.common['Authorization'] = `Bearer ${token}`;
    const res = await api.post('/api/admin/auth/verify');
    return res.data;
  },
  
  logout: () => {
    tokenStorage.remove();
    delete api.defaults.headers.common['Authorization'];
  },
  
  // Documents
  getDocuments: async (params?: { page?: number; page_size?: number; is_active?: boolean }): Promise<DocumentListResponse> => {
    const token = tokenStorage.get();
    if (!token) throw new Error('No token');
    api.defaults.headers.common['Authorization'] = `Bearer ${token}`;
    
    const res = await api.get('/api/admin/documents', { params });
    return res.data;
  },
  
  uploadDocument: async (file: File, chunkStrategy: string = 'recursive'): Promise<Document> => {
    const token = tokenStorage.get();
    if (!token) throw new Error('No token');
    api.defaults.headers.common['Authorization'] = `Bearer ${token}`;
    
    const formData = new FormData();
    formData.append('file', file);
    formData.append('chunk_strategy', chunkStrategy);
    
    const res = await api.post('/api/admin/documents/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return res.data;
  },
  
  deleteDocument: async (source: string): Promise<void> => {
    const token = tokenStorage.get();
    if (!token) throw new Error('No token');
    api.defaults.headers.common['Authorization'] = `Bearer ${token}`;
    
    await api.delete(`/api/admin/documents/${encodeURIComponent(source)}`);
  },
  
  reingestDocument: async (source: string): Promise<{ status: string; chunk_count: number; processing_time_ms: number }> => {
    const token = tokenStorage.get();
    if (!token) throw new Error('No token');
    api.defaults.headers.common['Authorization'] = `Bearer ${token}`;
    
    const res = await api.post(`/api/admin/documents/${encodeURIComponent(source)}/reingest`);
    return res.data;
  },
  
  // Sessions
  getSessions: async (params?: { page?: number; page_size?: number; user_id?: string }): Promise<SessionListResponse> => {
    const token = tokenStorage.get();
    if (!token) throw new Error('No token');
    api.defaults.headers.common['Authorization'] = `Bearer ${token}`;
    
    const res = await api.get('/api/admin/sessions', { params });
    return res.data;
  },
  
  searchSessions: async (query: string, limit?: number): Promise<SessionSearchResponse> => {
    const token = tokenStorage.get();
    if (!token) throw new Error('No token');
    api.defaults.headers.common['Authorization'] = `Bearer ${token}`;
    
    const res = await api.get('/api/admin/sessions/search', { params: { q: query, limit } });
    return res.data;
  },
  
  getSessionDetail: async (sessionId: string): Promise<SessionDetail> => {
    const token = tokenStorage.get();
    if (!token) throw new Error('No token');
    api.defaults.headers.common['Authorization'] = `Bearer ${token}`;
    
    const res = await api.get(`/api/admin/sessions/${sessionId}`);
    return res.data;
  },
  
  deleteSession: async (sessionId: string): Promise<void> => {
    const token = tokenStorage.get();
    if (!token) throw new Error('No token');
    api.defaults.headers.common['Authorization'] = `Bearer ${token}`;
    
    await api.delete(`/api/admin/sessions/${sessionId}`);
  },
  
  exportSession: async (sessionId: string, format: 'json' | 'csv'): Promise<Blob> => {
    const token = tokenStorage.get();
    if (!token) throw new Error('No token');
    api.defaults.headers.common['Authorization'] = `Bearer ${token}`;
    
    const res = await api.get(`/api/admin/sessions/export/${sessionId}`, {
      params: { format },
      responseType: 'blob',
    });
    return res.data;
  },
  
  // Stats
  getOverviewStats: async (period: number = 30): Promise<OverviewStats> => {
    const token = tokenStorage.get();
    if (!token) throw new Error('No token');
    api.defaults.headers.common['Authorization'] = `Bearer ${token}`;
    
    const res = await api.get('/api/admin/stats/overview', { params: { period } });
    return res.data;
  },
  
  getTokenUsage: async (period: '7d' | '30d' | '90d' = '7d'): Promise<TokenUsageResponse> => {
    const token = tokenStorage.get();
    if (!token) throw new Error('No token');
    api.defaults.headers.common['Authorization'] = `Bearer ${token}`;
    
    const res = await api.get('/api/admin/stats/tokens', { params: { period } });
    return res.data;
  },
  
  getRAGEffectiveness: async (period: '7d' | '30d' | '90d' = '7d'): Promise<RAGEffectivenessResponse> => {
    const token = tokenStorage.get();
    if (!token) throw new Error('No token');
    api.defaults.headers.common['Authorization'] = `Bearer ${token}`;
    
    const res = await api.get('/api/admin/stats/rag-effectiveness', { params: { period } });
    return res.data;
  },
  
  getTopSources: async (period: '7d' | '30d' | '90d' = '7d', limit: number = 10): Promise<TopSourcesResponse> => {
    const token = tokenStorage.get();
    if (!token) throw new Error('No token');
    api.defaults.headers.common['Authorization'] = `Bearer ${token}`;
    
    const res = await api.get('/api/admin/stats/top-sources', { params: { period, limit } });
    return res.data;
  },
};

// Error handler
export const getErrorMessage = (error: unknown): string => {
  if (axios.isAxiosError(error)) {
    const axiosError = error as AxiosError<{ detail?: string }>;
    return axiosError.response?.data?.detail || axiosError.message || 'An error occurred';
  }
  if (error instanceof Error) {
    return error.message;
  }
  return 'An unexpected error occurred';
};

export default api;
