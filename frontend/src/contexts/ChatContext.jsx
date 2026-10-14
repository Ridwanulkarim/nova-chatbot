import React, { createContext, useContext, useState, useEffect, useRef, useCallback } from 'react';
import { api, setAuthToken } from '../services/api';
import { streamMessage } from '../services/chatStream';
import { useAuth } from './AuthContext';
import { auth } from '../firebase';

const ChatContext = createContext(null);

export const DEFAULT_QUOTA = {
  message_count: 0,
  message_limit: 50,
  remaining_messages: 50,
  image_count: 0,
  image_limit: 10,
  remaining_images: 10,
  resets_in_hours: 24,
};

export const DEFAULT_MODELS = [
  { id: 'gemini-3.5-flash', name: 'Gemini 3.5 Flash (Google Vision)', supports_vision: true },
  { id: 'gemini-3.8-flash', name: 'Gemini 3.8 Flash (Google Vision)', supports_vision: true },
  { id: 'openai/gpt-oss-120b', name: 'GPT-OSS 120B (Groq)', supports_vision: false },
  { id: 'qwen/qwen3.8-27b', name: 'Qwen 3.8 27B (Groq)', supports_vision: false },
  { id: 'openai/gpt-oss-20b', name: 'GPT-OSS 20B (Groq)', supports_vision: false },
];

export function generateSmartTitle(content) {
  if (!content || typeof content !== 'string') return 'New Chat';
  const raw = content.trim();
  const cleanLow = raw.toLowerCase();

  const greetings = {
    'hello': 'Hello & Greeting',
    'hi': 'Hello & Greeting',
    'hey': 'Hello & Greeting',
    'hi there': 'Hello & Greeting',
    'hello pluto': 'Hello & Greeting',
    'hola': 'Hello & Greeting',
    'salam': 'Greetings & Assistance',
    'assalamu alaikum': 'Greetings & Assistance',
    'ki khobor': 'Casual Conversation',
    'ki kora laghbe': 'Guidance & Assistance',
    'ki kora lagbe': 'Guidance & Assistance',
    'help': 'Help & Support',
  };

  for (const [k, v] of Object.entries(greetings)) {
    if (cleanLow === k || cleanLow.startsWith(k + ' ') || cleanLow.startsWith(k + '!') || cleanLow.startsWith(k + '?') || cleanLow.startsWith(k + ',')) {
      return v;
    }
  }

  const imagePrefixes = ['generate an image of', 'generate a picture of', 'create an image of', 'draw an image of', '/image'];
  for (const prefix of imagePrefixes) {
    if (cleanLow.startsWith(prefix)) {
      const subj = raw.slice(prefix.length).replace(/^[:\s,-]+/, '');
      if (subj) {
        const words = subj.split(/\s+/).slice(0, 5).map((w) => w.charAt(0).toUpperCase() + w.slice(1));
        return `Image: ${words.join(' ')}`.slice(0, 38);
      }
    }
  }

  const questionFillers = [
    'can you please tell me about',
    'can you please help me with',
    'can you help me with',
    'can you help me',
    'can you explain',
    'could you please',
    'could you tell me',
    'i want you to',
    'i would like to',
    'how do i',
    'how to',
    'what is',
    'tell me about',
    'write a',
    'please',
  ];

  let trimmed = raw;
  for (const filler of questionFillers) {
    if (cleanLow.startsWith(filler)) {
      trimmed = raw.slice(filler.length).replace(/^[:\s,-?]+/, '');
      break;
    }
  }

  let words = trimmed.split(/\s+/).filter(Boolean);
  if (words.length === 0) words = raw.split(/\s+/).slice(0, 5);
  const titleWords = words.slice(0, 5).map((w) => w.charAt(0).toUpperCase() + w.slice(1));
  const result = titleWords.join(' ').replace(/[.,?!:;-]+$/, '').trim();
  return result ? result.slice(0, 38) : 'New Chat';
}

export function ChatProvider({ children }) {
  const { isAuthenticated, loading: authLoading, setIsAuthModalOpen, logout } = useAuth();
  const [conversations, setConversations] = useState(() => {
    try {
      const saved = localStorage.getItem('pluto_conversations');
      return saved ? JSON.parse(saved) : [];
    } catch (e) {
      return [];
    }
  });
  const [activeConversation, setActiveConversation] = useState(() => {
    try {
      const saved = localStorage.getItem('pluto_active_conversation');
      return saved ? JSON.parse(saved) : null;
    } catch (e) {
      return null;
    }
  });
  const [messages, setMessages] = useState(() => {
    try {
      const savedConvId = localStorage.getItem('pluto_active_conv_id');
      if (savedConvId) {
        const convSaved = localStorage.getItem(`pluto_messages_${savedConvId}`);
        if (convSaved) {
          const parsed = JSON.parse(convSaved);
          if (Array.isArray(parsed) && parsed.length > 0) return parsed;
        }
      }
      const saved = localStorage.getItem('pluto_messages');
      if (saved) {
        const parsed = JSON.parse(saved);
        if (Array.isArray(parsed) && parsed.length > 0) return parsed;
      }
      return [];
    } catch (e) {
      return [];
    }
  });
  const [isStreaming, setIsStreaming] = useState(false);
  const [availableModels, setAvailableModels] = useState(() => {
    try {
      const saved = localStorage.getItem('pluto_available_models');
      return saved ? JSON.parse(saved) : DEFAULT_MODELS;
    } catch (e) {
      return DEFAULT_MODELS;
    }
  });
  const [selectedModel, setSelectedModel] = useState(() => {
    return localStorage.getItem('pluto_selected_model') || 'openai/gpt-oss-120b';
  });
  const [webSearchEnabled, setWebSearchEnabled] = useState(false);
  const [attachedFiles, setAttachedFiles] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [errorMessage, _setErrorMessage] = useState(null);
  const setErrorMessage = useCallback((msg) => {
    if (!msg) {
      _setErrorMessage(null);
      return;
    }
    const str = typeof msg === 'string' ? msg : (msg?.message || String(msg));
    if (
      str.toLowerCase().includes('conversation not found') ||
      str.toLowerCase().includes('not found') ||
      str.includes('404')
    ) {
      _setErrorMessage(null);
      return;
    }
    _setErrorMessage(str);
  }, []);
  const [dailyQuota, setDailyQuota] = useState(() => {
    try {
      const saved = localStorage.getItem('pluto_daily_quota');
      return saved ? JSON.parse(saved) : DEFAULT_QUOTA;
    } catch (e) {
      return DEFAULT_QUOTA;
    }
  });

  // Persist conversations to localStorage
  useEffect(() => {
    try {
      if (conversations && conversations.length > 0) {
        localStorage.setItem('pluto_conversations', JSON.stringify(conversations));
      }
    } catch (e) {}
  }, [conversations]);

  // Persist selectedModel
  useEffect(() => {
    if (selectedModel) {
      try {
        localStorage.setItem('pluto_selected_model', selectedModel);
      } catch (e) {}
    }
  }, [selectedModel]);

  // Persist dailyQuota
  useEffect(() => {
    if (dailyQuota) {
      try {
        localStorage.setItem('pluto_daily_quota', JSON.stringify(dailyQuota));
      } catch (e) {}
    }
  }, [dailyQuota]);

  // Persist availableModels
  useEffect(() => {
    if (availableModels && availableModels.length > 0) {
      try {
        localStorage.setItem('pluto_available_models', JSON.stringify(availableModels));
      } catch (e) {}
    }
  }, [availableModels]);

  // Sync activeConversation to localStorage
  useEffect(() => {
    try {
      if (activeConversation) {
        localStorage.setItem('pluto_active_conversation', JSON.stringify(activeConversation));
        localStorage.setItem('pluto_active_conv_id', String(activeConversation.id));
      } else {
        localStorage.removeItem('pluto_active_conversation');
        localStorage.removeItem('pluto_active_conv_id');
      }
    } catch (e) {}
  }, [activeConversation]);

  // Helper for safely persisting messages to localStorage without QuotaExceeded errors
  const safeSaveMessages = useCallback((msgs, convId = null) => {
    if (!msgs || !Array.isArray(msgs) || msgs.length === 0) return;
    const targetId = convId || activeConversation?.id;
    try {
      localStorage.setItem('pluto_messages', JSON.stringify(msgs));
      if (targetId) {
        localStorage.setItem(`pluto_messages_${targetId}`, JSON.stringify(msgs));
      }
    } catch (err) {
      try {
        const sanitized = msgs.map((m) => {
          if (!m.attachments) return m;
          try {
            const parsed = typeof m.attachments === 'string' ? JSON.parse(m.attachments) : m.attachments;
            if (Array.isArray(parsed)) {
              const lighter = parsed.map((a) => {
                if (a.data_url && a.data_url.length > 2000) {
                  return { ...a, data_url: a.url || a.filename || 'stored_image' };
                }
                return a;
              });
              return { ...m, attachments: JSON.stringify(lighter) };
            }
          } catch (e) {}
          return m;
        });
        localStorage.setItem('pluto_messages', JSON.stringify(sanitized));
        if (targetId) {
          localStorage.setItem(`pluto_messages_${targetId}`, JSON.stringify(sanitized));
        }
      } catch (e) {
        console.warn('Could not cache messages to localStorage:', e);
      }
    }
  }, [activeConversation?.id]);

  // Sync messages to localStorage
  useEffect(() => {
    try {
      if (messages && messages.length > 0) {
        safeSaveMessages(messages, activeConversation?.id);
      }
    } catch (e) {}
  }, [messages, activeConversation?.id, safeSaveMessages]);

  const fetchQuota = async () => {
    try {
      const q = await api.getQuota();
      if (q) setDailyQuota(q);
    } catch (e) {}
  };

  useEffect(() => {
    fetchQuota();
  }, [isAuthenticated]);

  const abortControllerRef = useRef(null);

  // Load available models from backend
  useEffect(() => {
    const fetchModels = async () => {
      try {
        const models = await api.getAvailableModels();
        if (models && models.length > 0) {
          setAvailableModels(models);
          setSelectedModel((prev) => (models.some((m) => m.id === prev) ? prev : models[0].id));
        }
      } catch (err) {
        console.warn('Could not load models list:', err);
      }
    };
    fetchModels();
  }, []);

  // Load conversations when user is authenticated
  const loadConversations = async () => {
    if (authLoading) return;

    if (!isAuthenticated) {
      // Keep cached conversations and messages visible for guest / demo / restored state
      return;
    }
    try {
      const list = await api.listConversations(searchQuery);
      if (Array.isArray(list) && list.length > 0) {
        setConversations(list);
        try {
          localStorage.setItem('pluto_conversations', JSON.stringify(list));
        } catch (e) {}

        // Auto-restore active conversation if not searching
        if (!searchQuery) {
          const savedConvId = localStorage.getItem('pluto_active_conv_id') || activeConversation?.id;
          let targetConv = null;
          if (savedConvId) {
            targetConv = list.find((c) => String(c.id) === String(savedConvId));
          }

          const chosenConv = targetConv || activeConversation || list[0];
          if (chosenConv) {
            try {
              const conv = await api.getConversation(chosenConv.id);
              setActiveConversation(conv);
              if (conv.messages && conv.messages.length > 0) {
                setMessages(conv.messages);
                safeSaveMessages(conv.messages, conv.id);
              }
              if (conv.model) {
                setSelectedModel(conv.model);
              }
            } catch (e) {
              console.warn('Could not re-fetch active conversation from server, using local cache:', e);
            }
          }
        }
      }
    } catch (err) {
      console.warn('Failed to load conversations from server, retaining local cache:', err);
    }
  };

  useEffect(() => {
    if (!authLoading) {
      loadConversations();
    }
  }, [isAuthenticated, authLoading, searchQuery]);

  // Select a conversation and load its messages
  const selectConversation = async (conversationId) => {
    setErrorMessage(null);

    // 1. Instantly restore from local cache if available so UI does not flash blank
    try {
      const cachedMsgs = localStorage.getItem(`pluto_messages_${conversationId}`);
      if (cachedMsgs) {
        const parsed = JSON.parse(cachedMsgs);
        if (Array.isArray(parsed) && parsed.length > 0) {
          setMessages(parsed);
        }
      }
    } catch (e) {}

    const localConv = conversations.find((c) => String(c.id) === String(conversationId));
    if (localConv) {
      setActiveConversation(localConv);
      try {
        localStorage.setItem('pluto_active_conversation', JSON.stringify(localConv));
        localStorage.setItem('pluto_active_conv_id', String(localConv.id));
      } catch (e) {}
    }

    try {
      const conv = await api.getConversation(conversationId);
      setActiveConversation(conv);
      const convMsgs = conv.messages || [];
      if (convMsgs.length > 0) {
        setMessages(convMsgs);
        safeSaveMessages(convMsgs, conv.id);
      }
      try {
        localStorage.setItem('pluto_active_conversation', JSON.stringify(conv));
        localStorage.setItem('pluto_active_conv_id', String(conv.id));
      } catch (e) {}
      if (conv.model) {
        setSelectedModel(conv.model);
      }
      return conv;
    } catch (err) {
      console.warn('Failed to get conversation from server, keeping local cache:', err);
      if (localConv) {
        return localConv;
      }
      return null;
    }
  };

  // Create a brand new conversation
  const createNewChat = async () => {
    if (!isAuthenticated) {
      setIsAuthModalOpen(true);
      return null;
    }
    // Cache current active messages to its own ID before creating fresh chat
    if (activeConversation?.id && messages.length > 0) {
      safeSaveMessages(messages, activeConversation.id);
    }

    try {
      const newConv = await api.createConversation('New Chat', selectedModel);
      setConversations((prev) => [newConv, ...prev.filter((c) => c.id !== newConv.id)]);
      setActiveConversation(newConv);
      setMessages([]);
      try {
        localStorage.setItem('pluto_active_conversation', JSON.stringify(newConv));
        localStorage.setItem('pluto_active_conv_id', String(newConv.id));
        localStorage.removeItem('pluto_messages');
      } catch (e) {}
      return newConv;
    } catch (err) {
      console.warn('Backend createConversation failed, falling back to local conversation:', err);
      const fallbackId = (typeof crypto !== 'undefined' && crypto.randomUUID)
        ? crypto.randomUUID()
        : `conv-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
      const fallbackConv = {
        id: fallbackId,
        title: 'New Chat',
        model: selectedModel || 'openai/gpt-oss-120b',
        is_pinned: false,
        is_archived: false,
        is_local_fallback: true,
        created_at: new Date().toISOString(),
      };
      setConversations((prev) => [fallbackConv, ...prev.filter((c) => c.id !== fallbackId)]);
      setActiveConversation(fallbackConv);
      setMessages([]);
      try {
        localStorage.setItem('pluto_active_conversation', JSON.stringify(fallbackConv));
        localStorage.setItem('pluto_active_conv_id', fallbackId);
        localStorage.removeItem('pluto_messages');
      } catch (e) {}
      return fallbackConv;
    }
  };

  // Update conversation title or pin
  const updateConversationMeta = async (id, updates) => {
    // 1. Optimistically update local state & localStorage immediately
    setConversations((prev) => {
      const next = prev.map((c) => (c.id === id ? { ...c, ...updates } : c));
      try {
        localStorage.setItem('pluto_conversations', JSON.stringify(next));
      } catch (e) {}
      return next;
    });

    if (activeConversation?.id === id) {
      setActiveConversation((prev) => {
        const next = { ...prev, ...updates };
        try {
          localStorage.setItem('pluto_active_conversation', JSON.stringify(next));
        } catch (e) {}
        return next;
      });
    }

    // 2. Sync to server in background
    try {
      const updated = await api.updateConversation(id, updates);
      if (updated) {
        setConversations((prev) => {
          const next = prev.map((c) => (c.id === id ? { ...c, ...updated } : c));
          try {
            localStorage.setItem('pluto_conversations', JSON.stringify(next));
          } catch (e) {}
          return next;
        });
      }
    } catch (err) {
      console.warn('Backend updateConversation warning (retained locally):', err);
    }
  };

  // Delete conversation
  const deleteConversation = async (id) => {
    try {
      await api.deleteConversation(id);
    } catch (err) {
      console.warn('Backend deleteConversation warning:', err);
    }

    const remaining = conversations.filter((c) => c.id !== id);
    setConversations(remaining);
    try {
      localStorage.setItem('pluto_conversations', JSON.stringify(remaining));
      localStorage.removeItem(`pluto_messages_${id}`);
    } catch (e) {}

    if (activeConversation?.id === id) {
      if (remaining.length > 0) {
        await selectConversation(remaining[0].id);
      } else {
        setActiveConversation(null);
        setMessages([]);
        try {
          localStorage.removeItem('pluto_active_conversation');
          localStorage.removeItem('pluto_active_conv_id');
          localStorage.removeItem('pluto_messages');
        } catch (e) {}
      }
    }
  };

  // Stop streaming generation
  const stopGeneration = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
      setIsStreaming(false);
    }
  };

  // Send a message
  const sendMessage = async (content = '', customAttachments = null) => {
    const hasPendingAttachments =
      (customAttachments?.length ?? 0) > 0 ||
      attachedFiles.length > 0;

    if ((!content?.trim() && !hasPendingAttachments) || isStreaming) return;

    if (!isAuthenticated) {
      setIsAuthModalOpen(true);
      return;
    }

    setErrorMessage(null);

    // If no active conversation or if current conversation was corrupted/errored, create a fresh one
    let currentConv = activeConversation;
    const hasConvError = messages.some((m) => m.content && (m.content.toLowerCase().includes('conversation not found') || m.content.toLowerCase().includes('not found')));
    if (!currentConv || hasConvError) {
      currentConv = await createNewChat();
    }
    if (!currentConv) {
      try {
        currentConv = await api.createConversation('New Chat', selectedModel);
        setActiveConversation(currentConv);
      } catch (err) {
        setErrorMessage(err.message || 'Failed to connect to chat session. Please refresh the page and try again.');
        return;
      }
    }

    let finalAttachments = customAttachments || (attachedFiles.length > 0 ? [...attachedFiles] : null);

    // If user is asking a follow-up question in the same conversation without re-uploading the image,
    // carry forward the most recent image attachment from this conversation so stateless serverless calls still see it
    let carriedAttachments = null;
    if (!finalAttachments && messages.length > 0) {
      for (let i = messages.length - 1; i >= Math.max(0, messages.length - 6); i--) {
        const m = messages[i];
        if (m.role === 'user' && m.attachments) {
          try {
            const parsed = typeof m.attachments === 'string' ? JSON.parse(m.attachments) : m.attachments;
            if (Array.isArray(parsed) && parsed.some((a) => a.media_type === 'image' || a.data_url?.startsWith('data:image'))) {
              carriedAttachments = parsed;
              break;
            }
          } catch (e) {}
        }
      }
    }

    const effectiveAttachments = finalAttachments || carriedAttachments;

    const hasImages = (effectiveAttachments || []).some(
      (f) => f.media_type === 'image' || f.data_url?.startsWith('data:image') || (f.filename && f.filename.match(/\.(png|jpg|jpeg|webp|gif|bmp)$/i))
    );
    let modelToUse = selectedModel;
    if (hasImages && (!modelToUse || modelToUse.includes('oss') || modelToUse.includes('qwen') || modelToUse.includes('llama') || modelToUse.includes('groq'))) {
      modelToUse = 'gemini-3.5-flash';
    }

    const trimmedContent = (content || '').trim();
    const effectiveContent = trimmedContent || (
      hasImages
        ? 'Please analyze this attached image thoroughly and solve any questions or explain all visible details.'
        : 'Please review and summarize the attached document.'
    );

    // Assign smart relevant title immediately if first message or default title
    const isDefaultTitle = !currentConv.title || currentConv.title === 'New Chat' || currentConv.title === 'Untitled' || currentConv.title === 'Live Test';
    if (isDefaultTitle) {
      const smartTitle = generateSmartTitle(effectiveContent);
      currentConv = { ...currentConv, title: smartTitle };
      setActiveConversation(currentConv);
      setConversations((prev) =>
        prev.map((c) => (c.id === currentConv.id ? { ...c, title: smartTitle } : c))
      );
      try {
        localStorage.setItem('pluto_active_conversation', JSON.stringify(currentConv));
        const storedConvs = JSON.parse(localStorage.getItem('pluto_conversations') || '[]');
        const updatedList = storedConvs.map((c) => (c.id === currentConv.id ? { ...c, title: smartTitle } : c));
        localStorage.setItem('pluto_conversations', JSON.stringify(updatedList));
      } catch (e) {}
    }

    // Add optimistic user message to local state
    const optimisticUserMsg = {
      id: `temp-user-${Date.now()}`,
      conversation_id: currentConv.id,
      role: 'user',
      content: effectiveContent,
      attachments: finalAttachments ? JSON.stringify(finalAttachments) : null,
      created_at: new Date().toISOString(),
    };

    // Add placeholder assistant message
    const optimisticAssistantMsg = {
      id: `temp-assistant-${Date.now()}`,
      conversation_id: currentConv.id,
      role: 'assistant',
      content: '',
      model: modelToUse,
      isStreaming: true,
      created_at: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, optimisticUserMsg, optimisticAssistantMsg]);
    setIsStreaming(true);
    setAttachedFiles([]);

    const controller = new AbortController();
    abortControllerRef.current = controller;

    const fileIds = finalAttachments
      ? finalAttachments
          .filter((f) => f.media_type !== 'image' && !f.data_url?.startsWith('data:image'))
          .map((f) => f.id)
      : null;

    await streamMessage({
      conversationId: currentConv.id,
      content: effectiveContent,
      model: modelToUse,
      webSearch: webSearchEnabled,
      fileIds: fileIds && fileIds.length > 0 ? fileIds : null,
      attachments: effectiveAttachments,
      signal: controller.signal,
      onToken: (token) => {
        setMessages((prev) => {
          const last = prev[prev.length - 1];
          if (last && last.role === 'assistant') {
            return [
              ...prev.slice(0, -1),
              { ...last, content: last.content + token, isStreaming: true, isError: false },
            ];
          }
          return prev;
        });
      },
      onDone: (data) => {
        setIsStreaming(false);
        abortControllerRef.current = null;
        fetchQuota();
        if (data.title) {
          updateConversationMeta(currentConv.id, { title: data.title });
        }
        if (data.message_id) {
          setMessages((prev) => {
            const last = prev[prev.length - 1];
            if (last) {
              return [
                ...prev.slice(0, -1),
                {
                  ...last,
                  id: data.message_id,
                  isStreaming: false,
                  citations: data.citations ? JSON.stringify(data.citations) : null,
                },
              ];
            }
            return prev;
          });
        }
      },
      onError: async (err) => {
        setIsStreaming(false);
        abortControllerRef.current = null;
        const errStr = typeof err === 'string' ? err : (err?.message || '');

        const isAuthErr = (
          errStr.toLowerCase().includes('token') ||
          errStr.toLowerCase().includes('session expired') ||
          errStr.toLowerCase().includes('not authenticated') ||
          errStr.includes('401')
        );

        if (isAuthErr) {
          if (!auth?.currentUser) {
            try {
              if (logout) logout();
              else setAuthToken(null);
            } catch (e) {}
            setIsAuthModalOpen(true);
          }
          const authMsg = 'Session expired. Please sign in or use the 1-click Demo Account in the popup to continue.';
          setErrorMessage(authMsg);
          setMessages((prev) => {
            const last = prev[prev.length - 1];
            if (last && last.role === 'assistant') {
              return [
                ...prev.slice(0, -1),
                {
                  ...last,
                  content: '⚠️ **Session Expired**: Your session has expired or the security token was refreshed. Please click **"Sign In"** or use the **"⚡ One-Click Instant Guest / Demo Session"** in the popup to continue chatting.',
                  isStreaming: false,
                  isError: true,
                },
              ];
            }
            return prev;
          });
          return;
        }

        const isConvErr = (
          errStr.toLowerCase().includes('conversation not found') ||
          errStr.includes('404') ||
          errStr.toLowerCase().includes('not found')
        );

        if (isConvErr) {
          try {
            const freshId = (typeof crypto !== 'undefined' && crypto.randomUUID)
              ? crypto.randomUUID()
              : `conv-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
            
            const freshConv = {
              id: freshId,
              title: content.slice(0, 30) || 'New Chat',
              model: modelToUse,
            };
            setActiveConversation(freshConv);
            try {
              localStorage.setItem('pluto_active_conv_id', freshId);
              localStorage.setItem('pluto_active_conversation', JSON.stringify(freshConv));
            } catch (e) {}

            setIsStreaming(true);
            const retryController = new AbortController();
            abortControllerRef.current = retryController;
            await streamMessage({
              conversationId: freshId,
              content,
              model: modelToUse,
              webSearch: webSearchEnabled,
              fileIds: fileIds && fileIds.length > 0 ? fileIds : null,
              attachments: effectiveAttachments,
              signal: retryController.signal,
              onToken: (tok) => {
                setMessages((prev) => {
                  const last = prev[prev.length - 1];
                  if (last && last.role === 'assistant') {
                    return [
                      ...prev.slice(0, -1),
                      { ...last, content: last.content + tok, isStreaming: true, isError: false },
                    ];
                  }
                  return prev;
                });
              },
              onDone: (d) => {
                setIsStreaming(false);
                abortControllerRef.current = null;
                fetchQuota();
                if (d.title) {
                  updateConversationMeta(freshId, { title: d.title });
                }
                setMessages((prev) => {
                  const last = prev[prev.length - 1];
                  if (last) {
                    return [
                      ...prev.slice(0, -1),
                      { ...last, id: d.message_id || last.id, isStreaming: false, isError: false },
                    ];
                  }
                  return prev;
                });
              },
              onError: (retryErr) => {
                setIsStreaming(false);
                abortControllerRef.current = null;
                const retryStr = typeof retryErr === 'string' ? retryErr : (retryErr?.message || '');
                const isRetryAuth = (
                  retryStr.toLowerCase().includes('token') ||
                  retryStr.toLowerCase().includes('session expired') ||
                  retryStr.toLowerCase().includes('not authenticated') ||
                  retryStr.includes('401')
                );
                if (isRetryAuth) {
                  try {
                    if (logout) logout();
                    else setAuthToken(null);
                  } catch (e) {}
                  setIsAuthModalOpen(true);
                  const authMsg = 'Session expired. Please sign in or use the 1-click Demo Account in the popup to continue.';
                  setErrorMessage(authMsg);
                  setMessages((prev) => {
                    const last = prev[prev.length - 1];
                    if (last && last.role === 'assistant') {
                      return [
                        ...prev.slice(0, -1),
                        {
                          ...last,
                          content: '⚠️ **Session Expired**: Your session has expired. Please click **"Sign In"** or use the **"⚡ One-Click Instant Guest / Demo Session"** to continue.',
                          isStreaming: false,
                          isError: true,
                        },
                      ];
                    }
                    return prev;
                  });
                  return;
                }
                const safeErr = typeof retryErr === 'string' && (retryErr.toLowerCase().includes('not found') || retryErr.includes('404'))
                  ? 'Connection refreshed. Please click Send to continue.'
                  : retryErr;
                setErrorMessage(safeErr);
                setMessages((prev) => {
                  const last = prev[prev.length - 1];
                  if (last && last.role === 'assistant') {
                    return [
                      ...prev.slice(0, -1),
                      {
                        ...last,
                        content: (last.content ? last.content + '\n\n' : '') + `⚠️ **Error**: ${safeErr}`,
                        isStreaming: false,
                      },
                    ];
                  }
                  return prev;
                });
              },
            });
            return;
          } catch (e) {
            console.error('Silent conversation auto-recovery failed:', e);
          }
        }

        const displayErr = typeof errStr === 'string' && (errStr.toLowerCase().includes('not found') || errStr.includes('404'))
          ? 'Session refreshed. Please click Send again.'
          : errStr;
        setErrorMessage(displayErr);
        setMessages((prev) => {
          const last = prev[prev.length - 1];
          if (last && last.role === 'assistant') {
            return [
              ...prev.slice(0, -1),
              {
                ...last,
                content: (last.content ? last.content + '\n\n' : '') + `⚠️ **Error**: ${displayErr}`,
                isStreaming: false,
              },
            ];
          }
          return prev;
        });
      },
    });
  };

  // Regenerate assistant response
  const regenerateLastResponse = async () => {
    if (messages.length < 2 || isStreaming) return;
    const lastUserMsg = [...messages].reverse().find((m) => m.role === 'user');
    if (!lastUserMsg) return;

    let origAttachments = null;
    if (lastUserMsg.attachments) {
      try {
        origAttachments = typeof lastUserMsg.attachments === 'string'
          ? JSON.parse(lastUserMsg.attachments)
          : lastUserMsg.attachments;
      } catch (e) {
        origAttachments = null;
      }
    }

    // Remove the last assistant message
    setMessages((prev) => prev.filter((m) => m.id !== prev[prev.length - 1].id));
    await sendMessage(lastUserMsg.content, origAttachments);
  };

  // Submit feedback
  const sendFeedback = async (messageId, rating) => {
    try {
      await api.setMessageFeedback(messageId, rating);
      setMessages((prev) =>
        prev.map((m) => (m.id === messageId ? { ...m, feedback: rating } : m))
      );
    } catch (err) {
      console.error('Failed to submit feedback:', err);
    }
  };

  return (
    <ChatContext.Provider
      value={{
        conversations,
        activeConversation,
        messages,
        isStreaming,
        availableModels,
        selectedModel,
        setSelectedModel,
        webSearchEnabled,
        setWebSearchEnabled,
        attachedFiles,
        setAttachedFiles,
        searchQuery,
        setSearchQuery,
        errorMessage,
        setErrorMessage,
        dailyQuota,
        fetchQuota,
        selectConversation,
        createNewChat,
        updateConversationMeta,
        deleteConversation,
        sendMessage,
        stopGeneration,
        regenerateLastResponse,
        sendFeedback,
        loadConversations,
      }}
    >
      {children}
    </ChatContext.Provider>
  );
}

export function useChat() {
  const ctx = useContext(ChatContext);
  if (!ctx) throw new Error('useChat must be used within ChatProvider');
  return ctx;
}
