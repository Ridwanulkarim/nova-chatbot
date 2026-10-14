import React, { useRef, useEffect, useState } from 'react';
import {
  Menu,
  PanelLeft,
  Share2,
  Settings,
  ArrowDown,
  AlertCircle,
  Headphones,
  Zap,
  ImageIcon,
  Boxes,
  Palette,
  Sparkles,
  SquarePen,
} from 'lucide-react';
import { useChat } from '../../contexts/ChatContext';
import { useAuth } from '../../contexts/AuthContext';
import { MessageItem } from './MessageItem';
import { WelcomeScreen } from './WelcomeScreen';
import { ChatComposer } from './ChatComposer';

export function ChatArea({
  onToggleSidebar,
  onOpenSettings,
  onOpenDocModal,
  onOpenShareModal,
  onOpenVoiceModal,
  onOpenPluginsModal,
  theme,
  onToggleTheme,
}) {
  const {
    activeConversation,
    createNewChat,
    messages,
    selectedModel,
    setSelectedModel,
    availableModels,
    errorMessage,
    setErrorMessage,
    sendMessage,
    isStreaming,
    dailyQuota,
  } = useChat();
  const { isAuthenticated, setIsAuthModalOpen, user } = useAuth();

  const messagesEndRef = useRef(null);
  const scrollContainerRef = useRef(null);
  const [showScrollBottom, setShowScrollBottom] = useState(false);
  const [showQuotaTooltip, setShowQuotaTooltip] = useState(false);

  // Auto-scroll on new message tokens if user is near bottom
  useEffect(() => {
    if (messagesEndRef.current && !showScrollBottom) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, isStreaming, showScrollBottom]);

  const handleScroll = () => {
    if (!scrollContainerRef.current) return;
    const { scrollTop, scrollHeight, clientHeight } = scrollContainerRef.current;
    const isUp = scrollHeight - scrollTop - clientHeight > 100;
    setShowScrollBottom(isUp);
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    setShowScrollBottom(false);
  };

  const handleEditUserMessage = (newText) => {
    sendMessage(newText);
  };

  return (
    <div
      className={`flex-1 flex flex-col h-full overflow-hidden relative ${
        theme === 'lavender-glow'
          ? 'bg-transparent text-slate-900'
          : theme === 'lavender-dark'
          ? 'bg-transparent text-slate-100'
          : 'bg-slate-950 text-slate-100'
      }`}
    >
      {/* Top Header */}
      <header
        className={`h-14 border-b px-2 sm:px-4 flex items-center justify-between backdrop-blur-md z-10 flex-shrink-0 max-w-full overflow-x-hidden ${
          theme === 'lavender-glow'
            ? 'border-purple-200/40 bg-white/40 text-slate-800'
            : 'border-slate-800/80 bg-slate-950/80 text-slate-100'
        }`}
      >
        <div className="flex items-center gap-1.5 sm:gap-2.5 min-w-0">
          <button
            onClick={onToggleSidebar}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors flex-shrink-0"
            title="Toggle Sidebar"
          >
            <PanelLeft size={18} />
          </button>

          {/* New Chat Button */}
          <button
            onClick={createNewChat}
            className="flex items-center gap-1.5 px-2 sm:px-3 py-1.5 rounded-xl bg-brand-600 hover:bg-brand-500 text-white font-semibold text-xs shadow-md shadow-brand-600/25 transition-all flex-shrink-0 cursor-pointer"
            title="Start New Chat"
          >
            <SquarePen size={14} />
            <span className="hidden sm:inline">New Chat</span>
          </button>

          {/* Conversation Title (if inside conversation with messages) */}
          {activeConversation && messages.length > 0 && activeConversation.title !== 'New Chat' && (
            <div className="truncate min-w-0 hidden md:block">
              <span
                className={`text-xs truncate max-w-[120px] lg:max-w-xs ${
                  theme === 'lavender-glow' ? 'text-slate-600' : 'text-slate-400'
                }`}
              >
                / {activeConversation.title}
              </span>
            </div>
          )}
        </div>

        {/* Top Center Pill Switcher: [ Pluto Chat | + Workspace ] - only on very wide screens */}
        <div className={`hidden xl:flex items-center rounded-full p-0.5 text-xs shadow-xs border ${
          theme === 'lavender-glow'
            ? 'bg-purple-100/80 border-purple-200'
            : 'bg-[#202123]/80 border-white/10'
        }`}>
          <button className={`px-3.5 py-1 rounded-full font-medium shadow-xs ${
            theme === 'lavender-glow'
              ? 'bg-white text-purple-950 font-semibold'
              : 'bg-slate-800 text-white'
          }`}>
            Pluto Chat
          </button>
          <button
            onClick={onOpenDocModal}
            className={`px-3.5 py-1 rounded-full transition-colors flex items-center gap-1 ${
              theme === 'lavender-glow'
                ? 'text-slate-600 hover:text-slate-900'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            <span>+ Workspace</span>
          </button>
        </div>

        {/* Top Controls */}
        <div className="flex items-center gap-1 sm:gap-1.5 flex-shrink-0">
          {/* Daily Quota Indicator Pill (Responsive) */}
          {(() => {
            const quota = dailyQuota || {
              message_count: 0,
              message_limit: 50,
              remaining_messages: 50,
              image_count: 0,
              image_limit: 10,
              remaining_images: 10,
              resets_in_hours: 24,
            };
            return (
              <div className="relative">
                <button
                  onClick={() => setShowQuotaTooltip((v) => !v)}
                  onMouseEnter={() => setShowQuotaTooltip(true)}
                  onMouseLeave={() => setShowQuotaTooltip(false)}
                  className={`flex items-center gap-1 sm:gap-2 px-1.5 sm:px-3 py-1 sm:py-1.5 rounded-full text-[11px] sm:text-xs font-medium border transition-all ${
                    quota.remaining_messages <= 5 || quota.remaining_images <= 2
                      ? 'bg-amber-500/10 border-amber-500/30 text-amber-500'
                      : theme === 'lavender-glow'
                      ? 'bg-white/90 border-purple-200 hover:border-purple-300 text-slate-800 shadow-xs'
                      : 'bg-slate-900/90 border-slate-800 text-slate-300 hover:border-slate-700'
                  }`}
                  title="Daily quota: messages and AI images"
                >
                  <div className="flex items-center gap-0.5 sm:gap-1">
                    <Zap size={12} className="text-amber-500 fill-amber-500/20 flex-shrink-0" />
                    <span>
                      {quota.remaining_messages}<span className="hidden md:inline">/{quota.message_limit} msgs</span>
                    </span>
                  </div>
                  <span className={theme === 'lavender-glow' ? 'text-purple-300' : 'text-slate-600'}>|</span>
                  <div className={`flex items-center gap-0.5 sm:gap-1 font-semibold ${
                    theme === 'lavender-glow' ? 'text-purple-700' : 'text-indigo-300'
                  }`}>
                    <ImageIcon size={12} className={`${theme === 'lavender-glow' ? 'text-purple-600' : 'text-indigo-400'} flex-shrink-0`} />
                    <span>{quota.remaining_images}<span className="hidden md:inline">/{quota.image_limit} AI Images</span></span>
                  </div>
                </button>

                {/* Quota Popover Dropdown */}
                {showQuotaTooltip && (
                  <>
                    <div
                      className="fixed inset-0 z-40"
                      onClick={() => setShowQuotaTooltip(false)}
                    />
                    <div className={`absolute right-0 top-full mt-2 w-72 p-3.5 rounded-2xl shadow-2xl backdrop-blur-xl z-50 text-xs border ${
                    theme === 'lavender-glow'
                      ? 'bg-white/95 border-purple-200 text-slate-800 shadow-purple-950/10'
                      : 'bg-slate-900/95 border-slate-700 text-slate-200'
                  }`}>
                    <div className={`flex items-center justify-between pb-2 mb-2.5 border-b ${
                      theme === 'lavender-glow' ? 'border-purple-100' : 'border-slate-800'
                    }`}>
                      <span className={`font-semibold ${theme === 'lavender-glow' ? 'text-slate-900' : 'text-white'}`}>
                        Daily Usage Limits
                      </span>
                      <span className={`text-[10px] ${theme === 'lavender-glow' ? 'text-slate-500' : 'text-slate-400'}`}>
                        Resets in ~{quota.resets_in_hours}h
                      </span>
                    </div>
                    <div className="space-y-3">
                      <div>
                        <div className={`flex justify-between text-[11px] mb-1.5 ${theme === 'lavender-glow' ? 'text-slate-600' : 'text-slate-300'}`}>
                          <span className="flex items-center gap-1"><Zap size={12} className="text-amber-500" /> Messages</span>
                          <span className={`font-mono font-medium ${theme === 'lavender-glow' ? 'text-slate-900' : 'text-white'}`}>
                            {quota.message_count} / {quota.message_limit}
                          </span>
                        </div>
                        <div className={`w-full h-1.5 rounded-full overflow-hidden ${theme === 'lavender-glow' ? 'bg-purple-100' : 'bg-slate-800'}`}>
                          <div
                            className="bg-brand-500 h-full rounded-full transition-all"
                            style={{
                              width: `${Math.min(100, (quota.message_count / quota.message_limit) * 100)}%`,
                            }}
                          />
                        </div>
                      </div>

                      <div>
                        <div className={`flex justify-between text-[11px] mb-1.5 ${theme === 'lavender-glow' ? 'text-slate-600' : 'text-slate-300'}`}>
                          <span className="flex items-center gap-1"><ImageIcon size={12} className="text-purple-500" /> AI Images</span>
                          <span className={`font-mono font-medium ${theme === 'lavender-glow' ? 'text-slate-900' : 'text-white'}`}>
                            {quota.image_count} / {quota.image_limit}
                          </span>
                        </div>
                        <div className={`w-full h-1.5 rounded-full overflow-hidden ${theme === 'lavender-glow' ? 'bg-purple-100' : 'bg-slate-800'}`}>
                          <div
                            className="bg-purple-500 h-full rounded-full transition-all"
                            style={{
                              width: `${Math.min(100, (quota.image_count / quota.image_limit) * 100)}%`,
                            }}
                          />
                        </div>
                      </div>
                    </div>
                    <p className={`mt-3 text-[10px] leading-tight ${theme === 'lavender-glow' ? 'text-slate-500' : 'text-slate-400'}`}>
                      Free quota renews daily at midnight UTC.
                    </p>
                  </div>
                </>
              )}
              </div>
            );
          })()}

          {/* Model Selector (Desktop) */}
          <div className="hidden lg:block">
            <select
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value)}
              className={`text-xs rounded-xl px-2.5 py-1.5 focus:outline-none cursor-pointer border font-medium transition-all ${
                theme === 'lavender-glow'
                  ? 'bg-white border-purple-200 text-slate-800 hover:border-purple-300 focus:border-purple-500 shadow-xs'
                  : 'bg-slate-900 border-slate-700 text-slate-200 hover:border-slate-600 focus:border-brand-500'
              }`}
            >
              {(availableModels && availableModels.length > 0 ? availableModels : [
                { id: 'openai/gpt-oss-120b', name: 'GPT-OSS 120B (Groq)' },
                { id: 'qwen/qwen3.8-27b', name: 'Qwen 3.8 27B (Groq)' },
                { id: 'openai/gpt-oss-20b', name: 'GPT-OSS 20B (Groq)' },
              ]).map((m) => (
                <option key={m.id} value={m.id} className="text-slate-900 bg-white">
                  {m.name}
                </option>
              ))}
            </select>
          </div>

          {/* Upgrade Button (Desktop & Tablet) */}
          <button
            onClick={() => setShowQuotaTooltip((v) => !v)}
            className={`hidden md:flex items-center gap-1.5 px-2.5 sm:px-3 py-1.5 rounded-full text-xs font-semibold transition-all shadow-xs border ${
              theme === 'lavender-glow'
                ? 'bg-purple-50 hover:bg-purple-100 border-purple-200 text-purple-700 hover:text-purple-900'
                : 'bg-slate-900/90 hover:bg-slate-800 border-slate-700/60 text-sky-400 hover:text-sky-300'
            }`}
            title="View Plan & Quota"
          >
            <Sparkles size={13} className={theme === 'lavender-glow' ? 'text-purple-600' : 'text-sky-400'} />
            <span>Upgrade</span>
          </button>

          {/* Live Voice Mode Button */}
          <button
            onClick={onOpenVoiceModal}
            className={`flex items-center gap-1.5 p-1.5 sm:px-2.5 sm:py-1.5 rounded-lg text-xs font-medium transition-all shadow-xs group border ${
              theme === 'lavender-glow'
                ? 'bg-purple-100 hover:bg-purple-200 text-purple-900 border-purple-200'
                : 'bg-gradient-to-r from-brand-600/30 to-indigo-600/30 hover:from-brand-600/50 hover:to-indigo-600/50 border-brand-500/30 text-brand-200'
            }`}
            title="Start Live Voice Assistant"
          >
            <Headphones size={15} className={`${theme === 'lavender-glow' ? 'text-purple-700' : 'text-brand-300'} group-hover:scale-110 transition-transform`} />
            <span className="hidden lg:inline">Voice Mode</span>
          </button>

          {/* Share Button (Desktop/Tablet) */}
          {activeConversation && (
            <button
              onClick={onOpenShareModal}
              className={`hidden sm:flex p-2 rounded-lg transition-colors ${
                theme === 'lavender-glow'
                  ? 'text-slate-600 hover:text-slate-900 hover:bg-purple-100/70'
                  : 'text-slate-400 hover:text-white hover:bg-slate-850'
              }`}
              title="Share conversation"
            >
              <Share2 size={16} />
            </button>
          )}

          {/* Plugins & Skills Directory Button (Desktop) */}
          <button
            onClick={onOpenPluginsModal}
            className={`hidden md:flex p-2 rounded-lg transition-colors ${
              theme === 'lavender-glow'
                ? 'text-slate-600 hover:text-slate-900 hover:bg-purple-100/70'
                : 'text-slate-400 hover:text-white hover:bg-slate-850'
            }`}
            title="Plugins & Skills Directory"
          >
            <Boxes size={16} />
          </button>

          {/* Theme Palette Switcher */}
          <button
            onClick={onToggleTheme}
            className={`p-1.5 sm:p-2 rounded-lg transition-colors ${
              theme === 'lavender-glow'
                ? 'text-slate-600 hover:text-slate-900 hover:bg-purple-100/70'
                : 'text-slate-400 hover:text-white hover:bg-slate-850'
            }`}
            title={`Switch Theme (Current: ${theme})`}
          >
            <Palette size={16} />
          </button>

          {/* Settings Button */}
          <button
            onClick={onOpenSettings}
            className={`p-1.5 sm:p-2 rounded-lg transition-colors ${
              theme === 'lavender-glow'
                ? 'text-slate-600 hover:text-slate-900 hover:bg-purple-100/70'
                : 'text-slate-400 hover:text-white hover:bg-slate-850'
            }`}
            title="Settings"
          >
            <Settings size={16} />
          </button>

          {/* Auth Button (Sign In / User Avatar) */}
          {!isAuthenticated ? (
            <button
              onClick={() => setIsAuthModalOpen(true)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-purple-600 hover:bg-purple-500 text-white font-semibold text-xs shadow-md shadow-purple-600/25 transition-all flex-shrink-0 cursor-pointer"
              title="Sign in or register"
            >
              <span>Sign in</span>
            </button>
          ) : (
            <button
              onClick={onOpenSettings}
              className="w-7 h-7 rounded-full border border-purple-300 dark:border-slate-700 flex items-center justify-center text-xs font-bold overflow-hidden transition-transform hover:scale-105 flex-shrink-0 cursor-pointer"
              title={user?.full_name || user?.email || 'Account settings'}
            >
              {user?.photo_url || user?.photoURL ? (
                <img
                  src={user.photo_url || user.photoURL}
                  alt=""
                  referrerPolicy="no-referrer"
                  className="w-full h-full object-cover"
                />
              ) : (
                <span className={`text-[11px] ${theme === 'lavender-glow' ? 'text-purple-800' : 'text-brand-300'}`}>
                  {user?.email ? user.email[0].toUpperCase() : 'U'}
                </span>
              )}
            </button>
          )}
        </div>
      </header>

      {/* Error notification banner */}
      {errorMessage && !errorMessage.toLowerCase().includes('conversation not found') && !errorMessage.includes('404') && (
        <div className="bg-rose-950/90 border-b border-rose-800 px-4 py-2.5 flex items-center justify-between text-xs text-rose-200">
          <div className="flex items-center gap-2">
            <AlertCircle size={15} className="text-rose-400 flex-shrink-0" />
            <span>{errorMessage}</span>
          </div>
          <button
            onClick={() => setErrorMessage(null)}
            className="text-rose-400 hover:text-rose-200 ml-4 font-semibold"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Messages Scroll Area */}
      <div
        ref={scrollContainerRef}
        onScroll={handleScroll}
        className="flex-1 overflow-y-auto overflow-x-hidden flex flex-col"
      >
        {messages.length === 0 ? (
          <WelcomeScreen
            onOpenDocModal={onOpenDocModal}
            onOpenPluginsModal={onOpenPluginsModal}
            onOpenVoiceModal={onOpenVoiceModal}
            theme={theme}
          />
        ) : (
          <div className="pb-4">
            {messages.map((msg, idx) => (
              <MessageItem
                key={msg.id || idx}
                message={msg}
                isLast={idx === messages.length - 1}
                onEdit={msg.role === 'user' ? handleEditUserMessage : undefined}
              />
            ))}
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Scroll to bottom button */}
      {showScrollBottom && (
        <button
          onClick={scrollToBottom}
          className="absolute bottom-28 right-6 p-2 rounded-full bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 shadow-xl transition-all"
          title="Scroll to latest"
        >
          <ArrowDown size={16} />
        </button>
      )}

      {/* Chat Composer - Only rendered during active conversation to keep homepage centered */}
      {messages.length > 0 && <ChatComposer onOpenDocModal={onOpenDocModal} theme={theme} />}
    </div>
  );
}
