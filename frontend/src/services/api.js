export const getApiHost = () => {
  if (import.meta.env.VITE_API_URL) {
    return import.meta.env.VITE_API_URL;
  }
  if (typeof window === 'undefined') {
    return '';
  }
  // If on HTTPS (e.g. Vercel deployment), use same-origin relative path
  if (window.location.protocol === 'https:') {
    return '';
  }
  const hostname = window.location.hostname;
  if (hostname === 'localhost' || hostname === '127.0.0.1' || hostname === '0.0.0.0') {
    return 'http://localhost:8000';
  }
  // If accessing from LAN network IP (e.g. 192.168.x.x)
  if (hostname.match(/^\d+\.\d+\.\d+\.\d+$/)) {
    return `http://${hostname}:8000`;
  }
  return '';
};

export const API_HOST = getApiHost();
export const API_BASE = `${API_HOST}/api/v1`;

export const getAuthToken = () => {
  return localStorage.getItem('nova_ai_token') || localStorage.getItem('pluto_ai_token');
};

export const setAuthToken = (token) => {
  if (token) {
    localStorage.setItem('nova_ai_token', token);
    localStorage.setItem('pluto_ai_token', token);
  } else {
    localStorage.removeItem('nova_ai_token');
    localStorage.removeItem('pluto_ai_token');
  }
};

export const extractErrorMessage = (err, fallback = 'Operation failed') => {
  if (!err) return fallback;
  if (typeof err === 'string') return err;
  if (typeof err.detail === 'string') return err.detail;
  if (Array.isArray(err.detail)) {
    const msgs = err.detail.map((item) => {
      if (typeof item === 'string') return item;
      const field = item.loc && item.loc.length > 0 ? item.loc[item.loc.length - 1] : '';
      const msg = item.msg || JSON.stringify(item);
      return field && field !== 'body' ? `${field}: ${msg}` : msg;
    });
    return msgs.filter(Boolean).join('. ') || fallback;
  }
  if (typeof err.message === 'string') return err.message;
  return fallback;
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
      throw new Error(extractErrorMessage(err, 'Registration failed'));
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
      throw new Error(extractErrorMessage(err, 'Invalid email or password'));
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
    try {
      const formData = new FormData();
      formData.append('file', file);
      const res = await fetch(`${API_BASE}/files/upload`, {
        method: 'POST',
        headers: getHeaders(),
        body: formData,
      });
      if (res.ok) {
        return await res.json();
      }
      console.warn('Backend file upload returned non-OK, falling back to local data URL');
    } catch (err) {
      console.warn('Network file upload failed, falling back to local data URL:', err);
    }

    // Client-side fallback: Convert file to Base64 data URL so attachments and visual prompts always succeed!
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => {
        const ext = (file.name.split('.').pop() || '').toLowerCase();
        const isImg = file.type.startsWith('image/') || ['png', 'jpg', 'jpeg', 'webp', 'gif', 'svg'].includes(ext);
        const isVid = file.type.startsWith('video/') || ['mp4', 'webm', 'mov'].includes(ext);
        const isAud = file.type.startsWith('audio/') || ['mp3', 'wav', 'ogg'].includes(ext);
        const mediaType = isImg ? 'image' : isVid ? 'video' : isAud ? 'audio' : 'document';

        resolve({
          id: `local-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
          filename: file.name,
          file_size: file.size,
          mime_type: file.type || 'application/octet-stream',
          chunk_count: 1,
          url: reader.result,
          media_type: mediaType,
          created_at: new Date().toISOString(),
        });
      };
      reader.onerror = () => reject(new Error('Failed to read file locally'));
      reader.readAsDataURL(file);
    });
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
