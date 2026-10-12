import React, { useState } from 'react';
import { X, Share2, Copy, Check, ShieldCheck, Link2 } from 'lucide-react';
import { api } from '../../services/api';
import { useChat } from '../../contexts/ChatContext';

export function ShareModal({ isOpen, onClose, theme }) {
  const isLight = theme === 'lavender-glow';
  const { activeConversation, updateConversationMeta } = useChat();
  const [copied, setCopied] = useState(false);
  const [loading, setLoading] = useState(false);

  if (!isOpen || !activeConversation) return null;

  const shareUrl = activeConversation.share_token
    ? `${window.location.origin}/share/${activeConversation.share_token}`
    : '';

  const handleToggleShare = async () => {
    setLoading(true);
    try {
      const res = await api.toggleShare(activeConversation.id);
      updateConversationMeta(activeConversation.id, {
        share_token: res.share_token,
      });
    } catch (err) {
      console.error('Failed to toggle share:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleCopyLink = () => {
    if (!shareUrl) return;
    navigator.clipboard.writeText(shareUrl);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className={`fixed inset-0 z-50 flex items-center justify-center p-4 backdrop-blur-sm ${
      isLight ? 'bg-slate-900/30' : 'bg-black/70'
    }`}>
      <div className={`relative w-full max-w-md rounded-2xl border shadow-2xl p-6 transition-colors ${
        isLight
          ? 'bg-white text-slate-900 border-purple-200/90 shadow-purple-950/10'
          : 'bg-slate-900 border-slate-800 text-slate-100 shadow-2xl'
      }`}>
        <button
          onClick={onClose}
          className={`absolute top-4 right-4 p-1.5 rounded-lg transition-colors ${
            isLight
              ? 'text-slate-400 hover:text-slate-900 hover:bg-purple-50'
              : 'text-slate-400 hover:text-white hover:bg-slate-800'
          }`}
        >
          <X size={18} />
        </button>

        <div className="flex items-center gap-2 mb-2">
          <Share2 size={18} className="text-purple-500" />
          <h2 className={`text-base font-bold ${
            isLight ? 'text-slate-900' : 'text-white'
          }`}>
            Share Conversation
          </h2>
        </div>
        <p className={`text-xs mb-5 ${
          isLight ? 'text-slate-500' : 'text-slate-400'
        }`}>
          Generate a public, read-only link to share this conversation. Anyone with the link will be able to view the messages.
        </p>

        {activeConversation.share_token ? (
          <div className="space-y-4">
            <div className={`p-3 rounded-xl flex items-center justify-between text-xs font-mono border ${
              isLight
                ? 'bg-purple-50/70 border-purple-200 text-purple-950'
                : 'bg-slate-950 border-slate-800 text-slate-300'
            }`}>
              <span className={`truncate mr-2 ${isLight ? 'text-purple-700' : 'text-brand-300'}`}>{shareUrl}</span>
              <button
                onClick={handleCopyLink}
                className={`p-1.5 rounded-lg transition-colors flex items-center gap-1 ${
                  isLight
                    ? 'hover:bg-purple-100 text-purple-700'
                    : 'hover:bg-slate-800 text-slate-400 hover:text-white'
                }`}
                title="Copy Link"
              >
                {copied ? <Check size={14} className="text-emerald-500" /> : <Copy size={14} />}
                <span>{copied ? 'Copied' : 'Copy'}</span>
              </button>
            </div>

            <div className={`flex items-center gap-2 text-xs ${
              isLight ? 'text-emerald-700' : 'text-emerald-400'
            }`}>
              <ShieldCheck size={15} />
              <span>Link is active. Only messages up to this point will be shown.</span>
            </div>

            <div className="flex gap-2 justify-end pt-2">
              <button
                onClick={handleToggleShare}
                disabled={loading}
                className={`px-3 py-1.5 rounded-xl border text-xs font-medium transition-colors ${
                  isLight
                    ? 'border-rose-200 text-rose-600 hover:bg-rose-50'
                    : 'border-rose-800/80 text-rose-400 hover:bg-rose-950/30'
                }`}
              >
                Revoke Public Link
              </button>
            </div>
          </div>
        ) : (
          <div className="text-center py-4">
            <button
              onClick={handleToggleShare}
              disabled={loading}
              className="px-4 py-2.5 rounded-xl bg-purple-600 hover:bg-purple-500 text-white font-semibold text-xs shadow-md shadow-purple-600/30 transition-all flex items-center gap-2 mx-auto"
            >
              <Link2 size={15} />
              <span>{loading ? 'Creating...' : 'Create Public Share Link'}</span>
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
