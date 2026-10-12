import React, { createContext, useContext, useState, useEffect, useRef } from 'react';
import { api } from '../services/api';
import { streamMessage } from '../services/chatStream';
import { useAuth } from './AuthContext';

const ChatContext = createContext(null);

export function ChatProvider({ children }) {
  const { isAuthenticated, setIsAuthModalOpen } = useAuth();
  const [conversations, setConversations] = useState([]);
  const [activeConversation, setActiveConversation] = useState(null);
  const [messages, setMessages] = useState([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [availableModels, setAvailableModels] = useState([]);
  const [selectedModel, setSelectedModel] = useState('gpt-4o-mini');
  const [webSearchEnabled, setWebSearchEnabled] = useState(false);
  const [attachedFiles, setAttachedFiles] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [errorMessage, setErrorMessage] = useState(null);
  const [dailyQuota, setDailyQuota] = useState(null);

  const fetchQuota = async () => {
    if (!isAuthenticated) return;
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
        setAvailableModels(models);
        if (models.length > 0) {
          setSelectedModel(models[0].id);
        }
      } catch (err) {
        console.warn('Could not load models list:', err);
      }
    };
    fetchModels();
  }, []);

  // Load conversations when user is authenticated
  const loadConversations = async () => {
    if (!isAuthenticated) {
      setConversations([]);
      setActiveConversation(null);
      setMessages([]);
      return;
    }
    try {
      const list = await api.listConversations(searchQuery);
      setConversations(list);
    } catch (err) {
      console.error('Failed to load conversations:', err);
    }
  };

  useEffect(() => {
    loadConversations();
  }, [isAuthenticated, searchQuery]);

  // Select a conversation and load its messages
  const selectConversation = async (conversationId) => {
    setErrorMessage(null);
    try {
      const conv = await api.getConversation(conversationId);
      setActiveConversation(conv);
      setMessages(conv.messages || []);
      if (conv.model) {
        setSelectedModel(conv.model);
      }
    } catch (err) {
      console.error('Failed to get conversation:', err);
      setErrorMessage('Could not load conversation');
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
      setConversations((prev) => prev.filter((c) => c.id !== id));
      if (activeConversation?.id === id) {
        setActiveConversation(null);
        setMessages([]);
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
      onError: (err) => {
        setIsStreaming(false);
        abortControllerRef.current = null;
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
