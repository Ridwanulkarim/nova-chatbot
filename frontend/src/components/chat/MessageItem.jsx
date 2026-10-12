import React, { useState } from 'react';
import { Bot, User, Copy, Check, RotateCw, ThumbsUp, ThumbsDown, ExternalLink, Edit2, Volume2, VolumeX, FileText, Film, Image as ImageIcon } from 'lucide-react';
import { MarkdownContent } from './MarkdownContent';
import { useChat } from '../../contexts/ChatContext';
import { useVoiceAssistant } from '../../hooks/useVoiceAssistant';

export function MessageItem({ message, isLast, onEdit }) {
  const { sendFeedback, regenerateLastResponse, isStreaming } = useChat();
  const { isSpeaking, speak, stopSpeaking } = useVoiceAssistant();
  const [copied, setCopied] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [editText, setEditText] = useState(message.content);

  const isUser = message.role === 'user';
  const API_HOST = typeof window !== 'undefined' && (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')
    ? 'http://localhost:8000'
    : '';

  const handleCopy = () => {
    navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleFeedback = (rating) => {
    if (message.id && !message.id.startsWith('temp-')) {
      sendFeedback(message.id, rating);
    }
  };

  const handleToggleSpeech = () => {
    if (isSpeaking) {
      stopSpeaking();
    } else {
      speak(message.content);
    }
  };

  const handleSaveEdit = () => {
    if (editText.trim() && onEdit) {
      onEdit(editText.trim());
      setIsEditing(false);
    }
  };

  let attachmentsList = [];
  if (message.attachments) {
    try {
      attachmentsList = typeof message.attachments === 'string' ? JSON.parse(message.attachments) : message.attachments;
    } catch (e) {}
  }

  let citations = [];
  if (message.citations) {
    try {
      citations = typeof message.citations === 'string' ? JSON.parse(message.citations) : message.citations;
    } catch (e) {}
  }

  return (
    <div className={`group py-5 px-4 md:px-6 transition-colors ${isUser ? 'bg-slate-900/40' : 'bg-transparent'}`}>
      <div className="max-w-3xl mx-auto flex gap-4 items-start">
        {/* Avatar */}
        <div className="flex-shrink-0 mt-0.5">
          {isUser ? (
            <div className="w-8 h-8 rounded-full bg-slate-700/80 flex items-center justify-center text-slate-200 border border-slate-600/50 shadow-sm">
              <User size={16} />
            </div>
          ) : (
            <img
              src="/nova_logo.png"
              alt="Nova AI"
              className="w-8 h-8 rounded-full object-contain shadow-md shadow-purple-500/20 ring-1 ring-purple-400/30"
            />
          )}
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1.5">
            <span className="text-xs font-semibold tracking-wide text-slate-300">
              {isUser ? 'You' : 'Nova AI'}
            </span>
            {message.model && !isUser && (
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-400 font-mono border border-slate-700/60">
                {message.model}
              </span>
            )}
          </div>

          {/* User message edit mode */}
          {isEditing ? (
            <div className="mt-2 space-y-2">
              <textarea
                value={editText}
                onChange={(e) => setEditText(e.target.value)}
                className="w-full bg-slate-900 border border-slate-700 rounded-lg p-3 text-sm text-slate-100 focus:outline-none focus:border-brand-500"
                rows={3}
              />
              <div className="flex gap-2 justify-end">
                <button
                  onClick={() => setIsEditing(false)}
                  className="px-3 py-1 text-xs text-slate-400 hover:text-white"
                >
                  Cancel
                </button>
                <button
                  onClick={handleSaveEdit}
                  className="px-3 py-1 text-xs bg-brand-600 text-white rounded hover:bg-brand-500 font-medium"
                >
                  Save & Resend
                </button>
              </div>
            </div>
          ) : (
            <div className="text-slate-100">
              {/* Attached Media Cards (Photos, Videos, Files) */}
              {attachmentsList.length > 0 && (
                <div className="flex flex-wrap gap-2.5 mb-3">
                  {attachmentsList.map((att, aIdx) => {
                    const attUrl = att.url ? (att.url.startsWith('/') ? `${API_HOST}${att.url}` : att.url) : '';
                    if (att.media_type === 'image' || att.url?.match(/\.(jpeg|jpg|gif|png|webp)$/i)) {
                      return (
                        <div key={aIdx} className="rounded-xl overflow-hidden border border-slate-700 bg-slate-900 max-w-xs shadow-md">
                          <img src={attUrl} alt={att.filename} className="w-full h-36 object-cover hover:scale-105 transition-transform" />
                          <div className="p-1.5 bg-slate-850 text-[10px] text-slate-300 truncate">{att.filename}</div>
                        </div>
                      );
                    }
                    if (att.media_type === 'video' || att.url?.match(/\.(mp4|webm|mov)$/i)) {
                      return (
                        <div key={aIdx} className="rounded-xl overflow-hidden border border-slate-700 bg-slate-900 max-w-xs shadow-md p-2.5 flex items-center gap-2 text-xs text-brand-300">
                          <Film size={18} className="text-brand-400 flex-shrink-0" />
                          <span className="truncate">{att.filename}</span>
                        </div>
                      );
                    }
                    return (
                      <a key={aIdx} href={attUrl} download target="_blank" rel="noopener noreferrer" className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-850 border border-slate-700 hover:bg-slate-800 text-xs text-slate-200 transition-colors">
                        <FileText size={14} className="text-brand-400" />
                        <span className="truncate max-w-[180px]">{att.filename}</span>
                      </a>
                    );
                  })}
                </div>
              )}

              <MarkdownContent content={message.content} />
              {message.isStreaming && (
                <span className="inline-block w-2 h-4 bg-brand-400 ml-1 rounded-sm animate-pulse align-middle" />
              )}
            </div>
          )}

          {/* Sourced Citations */}
          {citations && citations.length > 0 && (
            <div className="mt-4 pt-3 border-t border-slate-800/80">
              <span className="text-xs font-medium text-slate-400 uppercase tracking-wider block mb-2">
                Web Sources
              </span>
              <div className="flex flex-wrap gap-2">
                {citations.map((c, cIdx) => (
                  <a
                    key={cIdx}
                    href={c.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-slate-850 hover:bg-slate-800 border border-slate-700/60 text-xs text-brand-300 transition-colors"
                  >
                    <span className="truncate max-w-[200px]">{c.title || c.url}</span>
                    <ExternalLink size={11} className="text-slate-400" />
                  </a>
                ))}
              </div>
            </div>
          )}

          {/* Action Toolbar */}
          {!message.isStreaming && message.content && (
            <div className="flex items-center gap-2 mt-3 opacity-0 group-hover:opacity-100 transition-opacity">
              <button
                onClick={handleCopy}
                className="p-1 rounded text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors"
                title="Copy message"
              >
                {copied ? <Check size={14} className="text-emerald-400" /> : <Copy size={14} />}
              </button>

              {isUser && onEdit && (
                <button
                  onClick={() => setIsEditing(true)}
                  className="p-1 rounded text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors"
                  title="Edit message"
                >
                  <Edit2 size={14} />
                </button>
              )}

              {!isUser && (
                <>
                  <button
                    onClick={handleToggleSpeech}
                    className={`p-1 rounded transition-colors ${
                      isSpeaking
                        ? 'text-brand-400 bg-brand-950/80 ring-1 ring-brand-500 animate-pulse'
                        : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
                    }`}
                    title={isSpeaking ? 'Stop speaking' : 'Read aloud (AI Voice)'}
                  >
                    {isSpeaking ? <VolumeX size={14} /> : <Volume2 size={14} />}
                  </button>
                  <button
                    onClick={() => handleFeedback(1)}
                    className={`p-1 rounded transition-colors ${
                      message.feedback === 1
                        ? 'text-brand-400 bg-brand-950/60'
                        : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
                    }`}
                    title="Good response"
                  >
                    <ThumbsUp size={14} />
                  </button>
                  <button
                    onClick={() => handleFeedback(-1)}
                    className={`p-1 rounded transition-colors ${
                      message.feedback === -1
                        ? 'text-rose-400 bg-rose-950/60'
                        : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
                    }`}
                    title="Poor response"
                  >
                    <ThumbsDown size={14} />
                  </button>
                  {isLast && (
                    <button
                      onClick={regenerateLastResponse}
                      disabled={isStreaming}
                      className="p-1 rounded text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors disabled:opacity-40"
                      title="Regenerate response"
                    >
                      <RotateCw size={14} />
                    </button>
                  )}
                </>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
