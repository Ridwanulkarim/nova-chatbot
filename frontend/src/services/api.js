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
  return localStorage.getItem('pluto_ai_token') || localStorage.getItem('nova_ai_token');
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
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(extractErrorMessage(err, `Server error (${res.status}): Failed to load conversations`));
    }
    return res.json();
  },

  async createConversation(title = 'New Chat', model = null) {
    const res = await fetch(`${API_BASE}/conversations`, {
      method: 'POST',
      headers: getHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify({ title, model }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(extractErrorMessage(err, `Server error (${res.status}): Failed to create conversation`));
    }
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
    const ext = (file.name.split('.').pop() || '').toLowerCase();
    const isImg = file.type.startsWith('image/') || ['png', 'jpg', 'jpeg', 'webp', 'gif', 'svg', 'bmp'].includes(ext);

    // Read & optimize local data URL immediately so image bytes are guaranteed to be compact and available
    const localDataUrl = await new Promise((resolve) => {
      const reader = new FileReader();
      reader.onload = () => {
        const rawDataUrl = reader.result;
        if (!isImg || ext === 'svg' || ext === 'gif' || typeof Image === 'undefined') {
          resolve(rawDataUrl);
          return;
        }
        const img = new Image();
        img.onload = () => {
          try {
            const MAX_DIM = 1600;
            let { width, height } = img;
            if (width > MAX_DIM || height > MAX_DIM) {
              const ratio = Math.min(MAX_DIM / width, MAX_DIM / height);
              width = Math.round(width * ratio);
              height = Math.round(height * ratio);
            }
            const canvas = document.createElement('canvas');
            canvas.width = width;
            canvas.height = height;
            const ctx = canvas.getContext('2d');
            // Fill white background for transparent PNGs converted to JPEG
            ctx.fillStyle = '#FFFFFF';
            ctx.fillRect(0, 0, width, height);
            ctx.drawImage(img, 0, 0, width, height);
            const compressed = canvas.toDataURL('image/jpeg', 0.85);
            resolve(compressed || rawDataUrl);
          } catch (e) {
            resolve(rawDataUrl);
          }
        };
        img.onerror = () => resolve(rawDataUrl);
        img.src = rawDataUrl;
      };
      reader.onerror = () => resolve(null);
      reader.readAsDataURL(file);
    });

    let backendData = null;
    try {
      const formData = new FormData();
      formData.append('file', file);
      const res = await fetch(`${API_BASE}/files/upload`, {
        method: 'POST',
        headers: getHeaders(),
        body: formData,
      });
      if (res.ok) {
        backendData = await res.json();
      }
    } catch (err) {
      console.warn('Backend file upload network error:', err);
    }

    const isVid = file.type.startsWith('video/') || ['mp4', 'webm', 'mov'].includes(ext);
    const isAud = file.type.startsWith('audio/') || ['mp3', 'wav', 'ogg'].includes(ext);
    const mediaType = isImg ? 'image' : isVid ? 'video' : isAud ? 'audio' : 'document';

    return {
      id: backendData?.id || `local-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
      filename: file.name,
      file_size: file.size,
      mime_type: isImg ? 'image/jpeg' : (file.type || 'application/octet-stream'),
      chunk_count: backendData?.chunk_count || 1,
      url: localDataUrl || backendData?.data_url || backendData?.url,
      data_url: localDataUrl || backendData?.data_url,
      media_type: mediaType,
      extracted_text: backendData?.extracted_text || null,
      created_at: backendData?.created_at || new Date().toISOString(),
    };
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
