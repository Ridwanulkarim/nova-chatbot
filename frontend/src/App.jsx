import React, { useState, useEffect } from 'react';
import { AuthProvider } from './contexts/AuthContext';
import { ChatProvider } from './contexts/ChatContext';
import { Sidebar } from './components/sidebar/Sidebar';
import { ChatArea } from './components/chat/ChatArea';
import { AuthModal } from './components/modals/AuthModal';
import { SettingsModal } from './components/modals/SettingsModal';
import { DocumentModal } from './components/modals/DocumentModal';
import { ShareModal } from './components/modals/ShareModal';
import { LiveVoiceModal } from './components/modals/LiveVoiceModal';
import { PluginsModal } from './components/modals/PluginsModal';

function MainLayout() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [isDocModalOpen, setIsDocModalOpen] = useState(false);
  const [isShareModalOpen, setIsShareModalOpen] = useState(false);
  const [isVoiceModalOpen, setIsVoiceModalOpen] = useState(false);
  const [isPluginsModalOpen, setIsPluginsModalOpen] = useState(false);
  const [theme, setTheme] = useState(() => {
    return localStorage.getItem('nova_theme') || 'lavender-glow';
  });

  useEffect(() => {
    if (theme === 'lavender-glow') {
      document.documentElement.classList.remove('dark');
      document.documentElement.classList.add('light');
      document.body.className = 'theme-lavender font-sans antialiased overflow-hidden selection:bg-purple-500/30 selection:text-purple-900';
    } else {
      document.documentElement.classList.add('dark');
      document.documentElement.classList.remove('light');
      document.body.className = `${
        theme === 'lavender-dark' ? 'theme-lavender-dark' : 'theme-midnight'
      } font-sans antialiased overflow-hidden selection:bg-brand-500/30 selection:text-brand-200`;
    }
  }, [theme]);

  const handleToggleTheme = () => {
    setTheme((prev) => {
      const next = prev === 'lavender-glow' ? 'lavender-dark' : prev === 'lavender-dark' ? 'midnight' : 'lavender-glow';
      localStorage.setItem('nova_theme', next);
      return next;
    });
  };

  return (
    <div
      className={`flex h-screen h-[100dvh] max-h-[100dvh] w-screen overflow-hidden font-sans transition-all duration-300 ${
        theme === 'lavender-glow'
          ? 'theme-lavender text-slate-900'
          : theme === 'lavender-dark'
          ? 'theme-lavender-dark text-slate-100'
          : 'theme-midnight text-slate-100'
      }`}
    >
      {/* Sidebar */}
      <Sidebar
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        onOpenSettings={() => setIsSettingsOpen(true)}
        onOpenDocModal={() => setIsDocModalOpen(true)}
        onOpenPluginsModal={() => setIsPluginsModalOpen(true)}
        theme={theme}
      />

      {/* Main Chat Area */}
      <ChatArea
        onToggleSidebar={() => setSidebarOpen((prev) => !prev)}
        onOpenSettings={() => setIsSettingsOpen(true)}
        onOpenDocModal={() => setIsDocModalOpen(true)}
        onOpenShareModal={() => setIsShareModalOpen(true)}
        onOpenVoiceModal={() => setIsVoiceModalOpen(true)}
        onOpenPluginsModal={() => setIsPluginsModalOpen(true)}
        theme={theme}
        onToggleTheme={handleToggleTheme}
      />

      {/* Modals */}
      <AuthModal theme={theme} />
      <SettingsModal
        isOpen={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
        theme={theme}
      />
      <DocumentModal
        isOpen={isDocModalOpen}
        onClose={() => setIsDocModalOpen(false)}
        theme={theme}
      />
      <ShareModal
        isOpen={isShareModalOpen}
        onClose={() => setIsShareModalOpen(false)}
        theme={theme}
      />
      <LiveVoiceModal
        isOpen={isVoiceModalOpen}
        onClose={() => setIsVoiceModalOpen(false)}
        theme={theme}
      />
      <PluginsModal
        isOpen={isPluginsModalOpen}
        onClose={() => setIsPluginsModalOpen(false)}
        theme={theme}
      />
    </div>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <ChatProvider>
        <MainLayout />
      </ChatProvider>
    </AuthProvider>
  );
}
