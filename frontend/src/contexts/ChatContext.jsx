import React, { createContext, useContext, useState, useEffect, useRef } from 'react';
import { api } from '../services/api';
import { streamMessage } from '../services/chatStream';
import { useAuth } from './AuthContext';

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
  { id: 'openai/gpt-oss-120b', name: 'GPT-OSS 120B (Groq)' },
  { id: 'qwen/qwen3.8-27b', name: 'Qwen 3.8 27B (Groq)' },
  { id: 'openai/gpt-oss-20b', name: 'GPT-OSS 20B (Groq)' },
];

export function ChatProvider({ children }) {
  const { isAuthenticated, loading: authLoading, setIsAuthModalOpen } = useAuth();
  const [conversations, setConversations] = useState([]);
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
      const saved = localStorage.getItem('pluto_messages');
      return saved ? JSON.parse(saved) : [];
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
  const [errorMessage, setErrorMessage] = useState(null);
  const [dailyQuota, setDailyQuota] = useState(() => {
    try {
      const saved = localStorage.getItem('pluto_daily_quota');
      return saved ? JSON.parse(saved) : DEFAULT_QUOTA;
    } catch (e) {
      return DEFAULT_QUOTA;
    }
  });

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

  // Sync messages to localStorage
  useEffect(() => {
    try {
      if (messages && messages.length > 0) {
        localStorage.setItem('pluto_messages', JSON.stringify(messages));
      } else if (!activeConversation) {
        localStorage.removeItem('pluto_messages');
      }
    } catch (e) {}
  }, [messages, activeConversation]);

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
      setConversations([]);
      setActiveConversation(null);
      setMessages([]);
      try {
        localStorage.removeItem('pluto_active_conversation');
        localStorage.removeItem('pluto_active_conv_id');
        localStorage.removeItem('pluto_messages');
      } catch (e) {}
      return;
    }
    try {
      const list = await api.listConversations(searchQuery);
      setConversations(list);

      // Auto-restore active conversation if not searching
      if (!searchQuery && list.length > 0) {
        const savedConvId = localStorage.getItem('pluto_active_conv_id') || activeConversation?.id;
        let targetConv = null;
        if (savedConvId) {
          targetConv = list.find((c) => String(c.id) === String(savedConvId));
        }

        // If target exists in list, sync latest messages from backend
        if (targetConv) {
          try {
            const conv = await api.getConversation(targetConv.id);
            setActiveConversation(conv);
            if (conv.messages) {
              setMessages(conv.messages);
            }
            if (conv.model) {
              setSelectedModel(conv.model);
            }
          } catch (e) {
            console.warn('Could not re-fetch active conversation:', e);
          }
        } else if (!savedConvId && (!messages || messages.length === 0)) {
          // If no active conversation saved and no messages currently showing, pick latest
          const latest = list[0];
          try {
            const conv = await api.getConversation(latest.id);
            setActiveConversation(conv);
            setMessages(conv.messages || []);
            if (conv.model) {
              setSelectedModel(conv.model);
            }
          } catch (e) {}
        }
      } else if (!searchQuery && list.length === 0) {
        // Clear stale local storage if no conversations exist on server
        try {
          localStorage.removeItem('pluto_active_conv_id');
          localStorage.removeItem('pluto_active_conversation');
          localStorage.removeItem('pluto_messages');
        } catch (e) {}
        setActiveConversation(null);
        setMessages([]);
      }
    } catch (err) {
      console.error('Failed to load conversations:', err);
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
    try {
      const conv = await api.getConversation(conversationId);
      setActiveConversation(conv);
      const convMsgs = conv.messages || [];
      setMessages(convMsgs);
      try {
        localStorage.setItem('pluto_active_conversation', JSON.stringify(conv));
        localStorage.setItem('pluto_active_conv_id', String(conv.id));
        localStorage.setItem('pluto_messages', JSON.stringify(convMsgs));
      } catch (e) {}
      if (conv.model) {
        setSelectedModel(conv.model);
      }
      return conv;
    } catch (err) {
      console.error('Failed to get conversation:', err);
      try {
        localStorage.removeItem('pluto_active_conv_id');
        localStorage.removeItem('pluto_active_conversation');
      } catch (e) {}
      return createNewChat();
    }
  };

  // Create a brand new conversation
  const createNewChat = async () => {
    if (!isAuthenticated) {
      setIsAuthModalOpen(true);
      return;
    }
    try {
      const newConv = await api.createConversation('New Chat', selectedModel);
      setConversations((prev) => [newConv, ...prev]);
      setActiveConversation(newConv);
      setMessages([]);
      try {
        localStorage.setItem('pluto_active_conversation', JSON.stringify(newConv));
        localStorage.setItem('pluto_active_conv_id', String(newConv.id));
        localStorage.removeItem('pluto_messages');
      } catch (e) {}
      return newConv;
    } catch (err) {
      console.error('Failed to create new chat:', err);
      setErrorMessage('Failed to create new conversation');
    }
  };

  // Update conversation title or pin
  const updateConversationMeta = async (id, updates) => {
    try {
      const updated = await api.updateConversation(id, updates);
      setConversations((prev) =>
        prev.map((c) => (c.id === id ? { ...c, ...updated } : c))
      );
      if (activeConversation?.id === id) {
        setActiveConversation((prev) => ({ ...prev, ...updated }));
      }
    } catch (err) {
      console.error('Failed to update conversation:', err);
    }
  };

  // Delete conversation
  const deleteConversation = async (id) => {
    try {
      await api.deleteConversation(id);
      const remaining = conversations.filter((c) => c.id !== id);
      setConversations(remaining);
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
    } catch (err) {
      console.error('Failed to delete conversation:', err);
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
  const sendMessage = async (content, customAttachments = null) => {
    if (!content.trim() || isStreaming) return;

    if (!isAuthenticated) {
      setIsAuthModalOpen(true);
      return;
    }

    setErrorMessage(null);

    // If no active conversation, create one first
    let currentConv = activeConversation;
    if (!currentConv) {
      currentConv = await createNewChat();
      if (!currentConv) return;
    }

    const finalAttachments = customAttachments || (attachedFiles.length > 0 ? [...attachedFiles] : null);

    // Add optimistic user message to local state
    const optimisticUserMsg = {
      id: `temp-user-${Date.now()}`,
      conversation_id: currentConv.id,
      role: 'user',
      content,
      attachments: finalAttachments ? JSON.stringify(finalAttachments) : null,
      created_at: new Date().toISOString(),
    };

    // Add placeholder assistant message
    const optimisticAssistantMsg = {
      id: `temp-assistant-${Date.now()}`,
      conversation_id: currentConv.id,
      role: 'assistant',
      content: '',
      model: selectedModel,
      isStreaming: true,
      created_at: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, optimisticUserMsg, optimisticAssistantMsg]);
    setIsStreaming(true);
    setAttachedFiles([]);

    const controller = new AbortController();
    abortControllerRef.current = controller;

    const fileIds = finalAttachments ? finalAttachments.map((f) => f.id) : null;

    await streamMessage({
      conversationId: currentConv.id,
      content,
      model: selectedModel,
      webSearch: webSearchEnabled,
      fileIds: fileIds && fileIds.length > 0 ? fileIds : null,
      attachments: finalAttachments,
      signal: controller.signal,
      onToken: (token) => {
        setMessages((prev) => {
          const last = prev[prev.length - 1];
          if (last && last.role === 'assistant') {
            return [
              ...prev.slice(0, -1),
              { ...last, content: last.content + token },
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
        if (typeof err === 'string' && err.toLowerCase().includes('conversation not found')) {
          try {
            localStorage.removeItem('pluto_active_conv_id');
            localStorage.removeItem('pluto_active_conversation');
            await createNewChat();
          } catch (e) {}
          setErrorMessage('Session refreshed. Please click Send again.');
          setMessages((prev) => {
            const last = prev[prev.length - 1];
            if (last && last.role === 'assistant') {
              return [
                ...prev.slice(0, -1),
                {
                  ...last,
                  content: 'Session refreshed. Please click Send again.',
                  isStreaming: false,
                },
              ];
            }
            return prev;
          });
          return;
        }
        setErrorMessage(err);
        setMessages((prev) => {
          const last = prev[prev.length - 1];
          if (last && last.role === 'assistant') {
            return [
              ...prev.slice(0, -1),
              {
                ...last,
                content: (last.content ? last.content + '\n\n' : '') + `⚠️ **Error**: ${err}`,
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

    // Remove the last assistant message
    setMessages((prev) => prev.filter((m) => m.id !== prev[prev.length - 1].id));
    await sendMessage(lastUserMsg.content);
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
