const API_HOST = import.meta.env.VITE_API_URL || (typeof window !== 'undefined' && (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')
  ? 'http://localhost:8000'
  : '');

export const API_BASE = `${API_HOST}/api/v1`;

export const getAuthToken = () => {
  return localStorage.getItem('nova_ai_token');
};

export const setAuthToken = (token) => {
  if (token) {
    localStorage.setItem('nova_ai_token', token);
  } else {
    localStorage.removeItem('nova_ai_token');
  }
};

const getHeaders = (extra = {}) => {
  const headers = { ...extra };
  const token = getAuthToken();
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  return headers;
};

export const api = {
  // Auth
  async register(email, password, fullName = '') {
    const res = await fetch(`${API_BASE}/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password, full_name: fullName }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Registration failed');
    }
    return res.json();
  },

  async login(email, password) {
    const res = await fetch(`${API_BASE}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Invalid email or password');
    }
    return res.json();
  },

  async getMe() {
    const res = await fetch(`${API_BASE}/auth/me`, {
      headers: getHeaders(),
    });
    if (!res.ok) throw new Error('Session expired');
    return res.json();
  },

  async getQuota() {
    const res = await fetch(`${API_BASE}/auth/quota`, {
      headers: getHeaders(),
    });
    if (!res.ok) return null;
    return res.json();
  },

  async generateImage(prompt, conversationId = null) {
    const res = await fetch(`${API_BASE}/images/generate`, {
      method: 'POST',
      headers: getHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify({ prompt, conversation_id: conversationId }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Image generation failed');
    }
    return res.json();
  },

  // Conversations
  async listConversations(search = '') {
    const q = search ? `?search=${encodeURIComponent(search)}` : '';
    const res = await fetch(`${API_BASE}/conversations${q}`, {
      headers: getHeaders(),
    });
    if (!res.ok) throw new Error('Failed to load conversations');
    return res.json();
  },

  async createConversation(title = 'New Chat', model = null) {
    const res = await fetch(`${API_BASE}/conversations`, {
      method: 'POST',
      headers: getHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify({ title, model }),
    });
    if (!res.ok) throw new Error('Failed to create conversation');
    return res.json();
  },

  async getConversation(id) {
    const res = await fetch(`${API_BASE}/conversations/${id}`, {
      headers: getHeaders(),
    });
    if (!res.ok) throw new Error('Failed to retrieve conversation');
    return res.json();
  },

  async updateConversation(id, updates) {
    const res = await fetch(`${API_BASE}/conversations/${id}`, {
      method: 'PATCH',
      headers: getHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify(updates),
    });
    if (!res.ok) throw new Error('Failed to update conversation');
    return res.json();
  },

  async deleteConversation(id) {
    const res = await fetch(`${API_BASE}/conversations/${id}`, {
      method: 'DELETE',
      headers: getHeaders(),
    });
    if (!res.ok) throw new Error('Failed to delete conversation');
    return res.json();
  },

  async toggleShare(id) {
    const res = await fetch(`${API_BASE}/conversations/${id}/share`, {
      method: 'POST',
      headers: getHeaders(),
    });
    if (!res.ok) throw new Error('Failed to update share settings');
    return res.json();
  },

  async setMessageFeedback(messageId, feedback) {
    const res = await fetch(`${API_BASE}/conversations/${messageId}/feedback`, {
      method: 'POST',
      headers: getHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify({ feedback }),
    });
    return res.json();
  },

  // Files & RAG
  async listDocuments() {
    const res = await fetch(`${API_BASE}/files`, {
      headers: getHeaders(),
    });
    if (!res.ok) throw new Error('Failed to load documents');
    return res.json();
  },

  async uploadDocument(file) {
    const formData = new FormData();
    formData.append('file', file);
    const res = await fetch(`${API_BASE}/files/upload`, {
      method: 'POST',
      headers: getHeaders(),
      body: formData,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'File upload failed');
    }
    return res.json();
  },

  async deleteDocument(id) {
    const res = await fetch(`${API_BASE}/files/${id}`, {
      method: 'DELETE',
      headers: getHeaders(),
    });
    if (!res.ok) throw new Error('Failed to delete document');
    return res.json();
  },

  // Settings & Models
  async getSettings() {
    const res = await fetch(`${API_BASE}/settings`, {
      headers: getHeaders(),
    });
    if (!res.ok) throw new Error('Failed to fetch settings');
    return res.json();
  },

  async updateSettings(settings) {
    const res = await fetch(`${API_BASE}/settings`, {
      method: 'PATCH',
      headers: getHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify(settings),
    });
    if (!res.ok) throw new Error('Failed to update settings');
    return res.json();
  },

  async getAvailableModels() {
    const res = await fetch(`${API_BASE}/settings/models`, {
      headers: getHeaders(),
    });
    if (!res.ok) throw new Error('Failed to fetch models');
    return res.json();
  },

  async getMemories() {
    const res = await fetch(`${API_BASE}/settings/memories`, {
      headers: getHeaders(),
    });
    if (!res.ok) return [];
    return res.json();
  },

  async addMemory(content, category = 'preference') {
    const res = await fetch(`${API_BASE}/settings/memories`, {
      method: 'POST',
      headers: getHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify({ content, category }),
    });
    if (!res.ok) throw new Error('Failed to save memory');
    return res.json();
  },

  async deleteMemory(id) {
    const res = await fetch(`${API_BASE}/settings/memories/${id}`, {
      method: 'DELETE',
      headers: getHeaders(),
    });
    return res.json();
  },

  async getInstalledPlugins() {
    try {
      const res = await fetch(`${API_BASE}/plugins/installed`, {
        headers: getHeaders(),
      });
      if (!res.ok) return { installed_plugin_ids: [] };
      return res.json();
    } catch (e) {
      return { installed_plugin_ids: [] };
    }
  },

  async togglePlugin(pluginId, action) {
    const res = await fetch(`${API_BASE}/plugins/toggle`, {
      method: 'POST',
      headers: getHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify({ plugin_id: pluginId, action }),
    });
    if (!res.ok) throw new Error('Failed to toggle plugin');
    return res.json();
  },
};
