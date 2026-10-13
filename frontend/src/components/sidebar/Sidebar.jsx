import React, { useState } from 'react';
import {
  Plus,
  Search,
  MessageSquare,
  Pin,
  Trash2,
  Edit2,
  FileText,
  Settings,
  LogOut,
  Sparkles,
  ChevronLeft,
  X,
  Check,
  Boxes,
} from 'lucide-react';
import { useChat } from '../../contexts/ChatContext';
import { useAuth } from '../../contexts/AuthContext';

export function Sidebar({ isOpen, onClose, onOpenSettings, onOpenDocModal, onOpenPluginsModal, theme }) {
  const {
    conversations,
    activeConversation,
    selectConversation,
    createNewChat,
    updateConversationMeta,
    deleteConversation,
    searchQuery,
    setSearchQuery,
  } = useChat();

  const { user, isAuthenticated, logout, setIsAuthModalOpen } = useAuth();
  const isLight = theme === 'lavender-glow';

  const [editingId, setEditingId] = useState(null);
  const [editTitle, setEditTitle] = useState('');
  const [confirmDeleteId, setConfirmDeleteId] = useState(null);

  const handleStartRename = (conv, e) => {
    e.stopPropagation();
    setEditingId(conv.id);
    setEditTitle(conv.title);
  };

  const handleSaveRename = (id, e) => {
    e.stopPropagation();
    if (editTitle.trim()) {
      updateConversationMeta(id, { title: editTitle.trim() });
    }
    setEditingId(null);
  };

  const handleTogglePin = (conv, e) => {
    e.stopPropagation();
    updateConversationMeta(conv.id, { is_pinned: !conv.is_pinned });
  };

  const handleDelete = (id, e) => {
    e.stopPropagation();
    deleteConversation(id);
    setConfirmDeleteId(null);
  };

  // Group conversations by Pinned vs Dates
  const pinnedConversations = conversations.filter((c) => c.is_pinned);
  const unpinnedConversations = conversations.filter((c) => !c.is_pinned);

  const groupConversationsByDate = (list) => {
    const today = new Date();
    today.setHours(0, 0, 0, 0);

    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);

    const lastWeek = new Date(today);
    lastWeek.setDate(lastWeek.getDate() - 7);

    const groups = {
      Today: [],
      Yesterday: [],
      'Previous 7 Days': [],
      Older: [],
    };

    list.forEach((c) => {
      const d = new Date(c.updated_at || c.created_at);
      if (d >= today) {
        groups.Today.push(c);
      } else if (d >= yesterday) {
        groups.Yesterday.push(c);
      } else if (d >= lastWeek) {
        groups['Previous 7 Days'].push(c);
      } else {
        groups.Older.push(c);
      }
    });

    return groups;
  };

  const dateGroups = groupConversationsByDate(unpinnedConversations);

  const renderConvItem = (conv) => {
    const isActive = activeConversation?.id === conv.id;
    const isEditing = editingId === conv.id;
    const isConfirmingDelete = confirmDeleteId === conv.id;

    return (
      <div
        key={conv.id}
        onClick={() => {
          selectConversation(conv.id);
          if (typeof window !== 'undefined' && window.innerWidth < 768 && onClose) {
            onClose();
          }
        }}
        className={`group relative flex items-center justify-between px-3 py-2 rounded-xl text-xs font-medium cursor-pointer transition-all ${
          isActive
            ? theme === 'lavender-glow'
              ? 'bg-purple-200/70 text-purple-950 font-semibold shadow-xs border border-purple-300/60'
              : 'bg-slate-800 text-slate-100 shadow-sm border border-slate-700/60'
            : theme === 'lavender-glow'
            ? 'text-slate-600 hover:text-slate-900 hover:bg-purple-100/60'
            : 'text-slate-400 hover:text-slate-200 hover:bg-slate-850'
        }`}
      >
        <div className="flex items-center gap-2.5 min-w-0 flex-1">
          <MessageSquare
            size={14}
            className={`flex-shrink-0 ${isActive ? 'text-brand-400' : 'text-slate-500'}`}
          />
          {isEditing ? (
            <input
              type="text"
              value={editTitle}
              onChange={(e) => setEditTitle(e.target.value)}
              onClick={(e) => e.stopPropagation()}
              onKeyDown={(e) => {
                if (e.key === 'Enter') handleSaveRename(conv.id, e);
                if (e.key === 'Escape') setEditingId(null);
              }}
              autoFocus
              className={`border rounded px-1.5 py-0.5 text-xs w-full focus:outline-none ${
                isLight
                  ? 'bg-white border-purple-400 text-slate-900'
                  : 'bg-slate-900 border-brand-500/80 text-slate-100'
              }`}
            />
          ) : (
            <span className="truncate flex-1">{conv.title}</span>
          )}
        </div>

        {/* Action icons */}
        <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity ml-1">
          {isEditing ? (
            <button
              onClick={(e) => handleSaveRename(conv.id, e)}
              className="p-1 hover:text-emerald-400 text-slate-400"
              title="Save"
            >
              <Check size={12} />
            </button>
          ) : isConfirmingDelete ? (
            <div className="flex items-center gap-1 bg-slate-900 px-1 py-0.5 rounded border border-rose-800">
              <button
                onClick={(e) => handleDelete(conv.id, e)}
                className="text-rose-400 hover:text-rose-300 text-[10px] font-bold px-1"
                title="Confirm Delete"
              >
                Delete
              </button>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  setConfirmDeleteId(null);
                }}
                className="text-slate-400 hover:text-slate-200"
                title="Cancel"
              >
                <X size={11} />
              </button>
            </div>
          ) : (
            <>
              <button
                onClick={(e) => handleTogglePin(conv, e)}
                className={`p-1 rounded hover:bg-slate-700/60 transition-colors ${
                  conv.is_pinned ? 'text-amber-400' : 'text-slate-400 hover:text-slate-200'
                }`}
                title={conv.is_pinned ? 'Unpin' : 'Pin'}
              >
                <Pin size={12} />
              </button>
              <button
                onClick={(e) => handleStartRename(conv, e)}
                className="p-1 rounded text-slate-400 hover:text-slate-200 hover:bg-slate-700/60 transition-colors"
                title="Rename"
              >
                <Edit2 size={12} />
              </button>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  setConfirmDeleteId(conv.id);
                }}
                className="p-1 rounded text-slate-400 hover:text-rose-400 hover:bg-slate-700/60 transition-colors"
                title="Delete"
              >
                <Trash2 size={12} />
              </button>
            </>
          )}
        </div>
      </div>
    );
  };

  return (
    <>
      {/* Mobile Backdrop */}
      {isOpen && (
        <div
          onClick={onClose}
          className="fixed inset-0 bg-black/60 backdrop-blur-sm z-30 md:hidden"
        />
      )}

      {/* Sidebar Container */}
      <aside
        className={`fixed md:static inset-y-0 left-0 z-40 transition-all duration-200 ease-in-out flex flex-col ${
          isOpen
            ? 'w-72 max-w-[85vw] translate-x-0 opacity-100 shadow-2xl md:shadow-none'
            : '-translate-x-full md:w-0 md:translate-x-0 md:opacity-0 md:overflow-hidden'
        } ${
          theme === 'lavender-glow'
            ? 'bg-white/95 md:bg-white/70 backdrop-blur-2xl border-r border-purple-200/50 text-slate-800'
            : theme === 'lavender-dark'
            ? 'bg-slate-950/95 md:bg-slate-950/70 backdrop-blur-2xl border-r border-purple-900/30 text-slate-100'
            : 'bg-slate-925 border-r border-slate-800/80 text-slate-100'
        }`}
      >
        <div className={`p-4 flex items-center justify-between border-b ${
          theme === 'lavender-glow' ? 'border-purple-200/40' : 'border-slate-800/60'
        }`}>
          <div className="flex items-center gap-2.5">
            <img
              src="/pluto_logo.png"
              alt="Pluto AI"
              className="w-8 h-8 rounded-xl object-contain shadow-md shadow-purple-500/20"
            />
            <div>
              <h1 className={`font-bold text-sm tracking-tight flex items-center gap-1.5 ${
                theme === 'lavender-glow' ? 'text-slate-900' : 'text-white'
              }`}>
                Pluto AI
                <span className="text-[10px] px-1.5 py-0.2 rounded-full bg-brand-500/20 text-brand-500 font-medium">
                  v1.0
                </span>
              </h1>
            </div>
          </div>
          <button
            onClick={onClose}
            className="md:hidden p-1.5 rounded-lg text-slate-400 hover:text-white"
          >
            <ChevronLeft size={18} />
          </button>
        </div>

        {/* New Chat Button & Search */}
        <div className="p-3 space-y-2.5">
          <button
            onClick={() => {
              createNewChat();
              if (typeof window !== 'undefined' && window.innerWidth < 768 && onClose) {
                onClose();
              }
            }}
            className="w-full flex items-center justify-center gap-2 px-3 py-2.5 rounded-xl bg-brand-600 hover:bg-brand-500 text-white text-xs font-semibold shadow-md shadow-brand-600/20 transition-all"
          >
            <Plus size={16} />
            <span>New Chat</span>
          </button>

          {/* Search bar */}
          <div className="relative">
            <Search
              size={13}
              className={`absolute left-3 top-1/2 -translate-y-1/2 ${
                isLight ? 'text-purple-400' : 'text-slate-500'
              }`}
            />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search chats..."
              className={`w-full rounded-xl pl-8 pr-3 py-1.5 text-xs transition-colors focus:outline-none border ${
                isLight
                  ? 'bg-purple-50/70 border-purple-200 text-slate-900 placeholder-slate-400 focus:border-purple-400 focus:bg-white'
                  : 'bg-slate-900 border-slate-800 text-slate-200 placeholder-slate-500 focus:border-slate-700'
              }`}
            />
          </div>
        </div>

        {/* Conversation List */}
        <div className="flex-1 overflow-y-auto px-3 py-2 space-y-4">
          {/* Pinned Section */}
          {pinnedConversations.length > 0 && (
            <div>
              <div className={`px-2 pb-1.5 flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wider ${
                isLight ? 'text-slate-500' : 'text-slate-400'
              }`}>
                <Pin size={10} className="text-amber-400" />
                <span>Pinned</span>
              </div>
              <div className="space-y-1">
                {pinnedConversations.map(renderConvItem)}
              </div>
            </div>
          )}

          {/* Date-grouped list */}
          {Object.entries(dateGroups).map(([groupTitle, list]) => {
            if (list.length === 0) return null;
            return (
              <div key={groupTitle}>
                <div className={`px-2 pb-1.5 text-[11px] font-semibold uppercase tracking-wider ${
                  isLight ? 'text-slate-500' : 'text-slate-400'
                }`}>
                  {groupTitle}
                </div>
                <div className="space-y-1">
                  {list.map(renderConvItem)}
                </div>
              </div>
            );
          })}

          {conversations.length === 0 && (
            <div className={`text-center py-8 text-xs ${
              isLight ? 'text-slate-500' : 'text-slate-500'
            }`}>
              No conversations yet
            </div>
          )}
        </div>

        {/* Knowledge & Tools Quick Access */}
        <div className={`p-3 border-t space-y-1 ${
          isLight ? 'border-purple-200/50' : 'border-slate-800/60'
        }`}>
          <button
            onClick={() => {
              onOpenDocModal();
              if (typeof window !== 'undefined' && window.innerWidth < 768 && onClose) {
                onClose();
              }
            }}
            className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-xs transition-colors ${
              isLight
                ? 'text-slate-700 hover:text-slate-950 hover:bg-purple-100/70'
                : 'text-slate-300 hover:text-white hover:bg-slate-850'
            }`}
          >
            <FileText size={15} className="text-brand-500" />
            <span>Document Knowledge Base</span>
          </button>
          <button
            onClick={() => {
              onOpenPluginsModal();
              if (typeof window !== 'undefined' && window.innerWidth < 768 && onClose) {
                onClose();
              }
            }}
            className={`w-full flex items-center justify-between px-3 py-2 rounded-xl text-xs transition-colors group ${
              isLight
                ? 'text-slate-700 hover:text-slate-950 hover:bg-purple-100/70'
                : 'text-slate-300 hover:text-white hover:bg-slate-850'
            }`}
          >
            <div className="flex items-center gap-2.5">
              <Boxes size={15} className="text-indigo-500 group-hover:scale-110 transition-transform" />
              <span>Plugins & Skills</span>
            </div>
            <span className={`px-1.5 py-0.5 rounded text-[10px] font-semibold border ${
              isLight
                ? 'bg-purple-100 text-purple-900 border-purple-200'
                : 'bg-indigo-500/10 text-indigo-400 border-indigo-500/20'
            }`}>
              Directory
            </span>
          </button>
        </div>

        {/* User Account Footer */}
        <div className={`p-3 border-t ${
          isLight
            ? 'border-purple-200/60 bg-purple-50/50'
            : 'border-slate-800/80 bg-slate-950/60'
        }`}>
          {isAuthenticated ? (
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2.5 min-w-0">
                <div className={`w-8 h-8 rounded-full border flex items-center justify-center text-xs font-bold ${
                  isLight
                    ? 'bg-purple-100 border-purple-300 text-purple-800'
                    : 'bg-slate-800 border-slate-700 text-brand-300'
                }`}>
                  {user?.email ? user.email[0].toUpperCase() : 'U'}
                </div>
                <div className="truncate">
                  <div className={`text-xs font-semibold truncate ${
                    isLight ? 'text-slate-900' : 'text-slate-200'
                  }`}>
                    {user?.full_name || user?.email?.split('@')[0]}
                  </div>
                  <div className={`text-[10px] truncate ${
                    isLight ? 'text-slate-500' : 'text-slate-400'
                  }`}>
                    {user?.email}
                  </div>
                </div>
              </div>
              <button
                onClick={logout}
                className={`p-1.5 rounded-lg transition-colors ${
                  isLight
                    ? 'text-slate-500 hover:text-rose-600 hover:bg-purple-100'
                    : 'text-slate-400 hover:text-rose-400 hover:bg-slate-800'
                }`}
                title="Log out"
              >
                <LogOut size={15} />
              </button>
            </div>
          ) : (
            <button
              onClick={() => setIsAuthModalOpen(true)}
              className={`w-full py-2 px-3 rounded-xl text-xs font-semibold border transition-all text-center ${
                isLight
                  ? 'bg-white hover:bg-purple-100 text-purple-900 border-purple-200 shadow-xs'
                  : 'bg-slate-850 hover:bg-slate-800 text-brand-300 border-slate-700/80'
              }`}
            >
              Sign In / Register
            </button>
          )}
        </div>
      </aside>
    </>
  );
}
