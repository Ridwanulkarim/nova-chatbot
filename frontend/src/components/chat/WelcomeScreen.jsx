import React, { useState, useRef } from 'react';
import {
  Plus,
  Brain,
  Mic,
  AudioLines,
  Image as ImageIcon,
  PenLine,
  Globe,
  Calculator,
  X,
  Paperclip,
  Sparkles,
  FileText,
  Boxes,
  Loader2,
  UploadCloud,
} from 'lucide-react';
import { useChat } from '../../contexts/ChatContext';
import { useAuth } from '../../contexts/AuthContext';
import { useVoiceAssistant } from '../../hooks/useVoiceAssistant';
import { api } from '../../services/api';

export function WelcomeScreen({
  onOpenDocModal,
  onOpenPluginsModal,
  onOpenVoiceModal,
  theme,
}) {
  const {
    sendMessage,
    setWebSearchEnabled,
    attachedFiles,
    setAttachedFiles,
    isStreaming,
  } = useChat();

  const { user } = useAuth();
  const { isListening, startListening, stopListening, language, setLanguage } = useVoiceAssistant();

  const [input, setInput] = useState('');
  const [isThinking, setIsThinking] = useState(false);
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const [uploadingFile, setUploadingFile] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [dismissedFeatured, setDismissedFeatured] = useState(false);
  const fileInputRef = useRef(null);

  // Derive user's first name, or fallback gracefully
  const firstName =
    user?.full_name?.trim()?.split(' ')[0] ||
    (user?.email ? user.email.split('@')[0] : 'there');

  const isLight = theme === 'lavender-glow';

  const handleFiles = async (filesList) => {
    const files = Array.from(filesList || []);
    if (files.length === 0) return;

    setUploadingFile(true);
    try {
      for (const file of files) {
        const uploaded = await api.uploadDocument(file);
        setAttachedFiles((prev) => [...prev, uploaded]);
      }
    } catch (err) {
      console.error('File upload failed:', err);
    } finally {
      setUploadingFile(false);
    }
  };

  const handlePaste = async (e) => {
    const items = e.clipboardData?.items;
    if (!items) return;

    const imageFiles = [];
    for (let i = 0; i < items.length; i++) {
      const item = items[i];
      if (item.type && item.type.indexOf('image') !== -1) {
        const blob = item.getAsFile();
        if (blob) {
          const extension = blob.type.split('/')[1] || 'png';
          const file = new File(
            [blob],
            `Screenshot_${new Date().toISOString().slice(11, 19).replace(/:/g, '-')}.${extension}`,
            { type: blob.type }
          );
          imageFiles.push(file);
        }
      }
    }

    if (imageFiles.length > 0) {
      e.preventDefault();
      await handleFiles(imageFiles);
    }
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const handleDrop = async (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    if (e.dataTransfer?.files?.length > 0) {
      await handleFiles(e.dataTransfer.files);
    }
  };

  const handleToggleListening = () => {
    if (isListening) {
      stopListening();
    } else {
      startListening((transcript) => {
        setInput((prev) => (prev ? `${prev} ${transcript}` : transcript));
      }, language);
    }
  };

  const handleSend = (textOverride) => {
    const textToSend = (typeof textOverride === 'string' ? textOverride : input).trim();
    if ((!textToSend && attachedFiles.length === 0) || isStreaming || uploadingFile) return;

    let finalPrompt = textToSend;
    if (!finalPrompt && attachedFiles.length > 0) {
      const hasImg = attachedFiles.some((f) =>
        f.media_type === 'image' || f.filename?.match(/\.(png|jpg|jpeg|webp)$/i)
      );
      finalPrompt = hasImg
        ? "Please analyze and describe this attached image/screenshot in detail, reading all text and explaining what is shown."
        : "Please review and explain the attached document.";
    }

    if (isThinking && !finalPrompt.toLowerCase().startsWith('think') && !finalPrompt.toLowerCase().startsWith('reason')) {
      finalPrompt = `[Thinking / Deep Reasoning Mode Enabled]: ${finalPrompt}`;
    }

    sendMessage(finalPrompt);
    setInput('');
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      className="flex-1 flex flex-col items-center justify-center px-4 w-full max-w-3xl mx-auto my-auto relative select-none"
    >
      {/* Drag & Drop Visual Overlay */}
      {isDragging && (
        <div className="absolute inset-0 z-50 bg-slate-950/85 border-2 border-dashed border-purple-400 rounded-3xl flex flex-col items-center justify-center backdrop-blur-md">
          <UploadCloud size={44} className="text-purple-400 animate-bounce mb-2" />
          <p className="text-base font-semibold text-white">Drop your image, screenshot, or document</p>
          <p className="text-xs text-purple-300">Pluto AI will visually analyze and inspect it</p>
        </div>
      )}

      {/* 1. Personalized Greeting (matching screenshot style) */}
      <h1
        className={`text-2xl sm:text-3xl font-medium tracking-tight mb-7 text-center transition-colors ${
          isLight ? 'text-slate-900' : 'text-slate-100'
        }`}
      >
        Hey, {firstName}. Ready to dive in?
      </h1>

      {/* 2. Main Search/Chat Input Capsule */}
      <div className="w-full max-w-2xl relative">
        {/* Attached files preview chips above input */}
        {attachedFiles.length > 0 && (
          <div className="flex flex-wrap gap-2 mb-2 px-2">
            {attachedFiles.map((f, idx) => (
              <div
                key={idx}
                className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-slate-800/90 border border-slate-700 text-xs text-slate-200"
              >
                <Paperclip size={12} className="text-purple-400" />
                <span className="truncate max-w-[140px]">{f.filename}</span>
                <button
                  onClick={() => setAttachedFiles((prev) => prev.filter((_, i) => i !== idx))}
                  className="p-0.5 rounded-full hover:bg-slate-700 text-slate-400 hover:text-white ml-1"
                >
                  <X size={11} />
                </button>
              </div>
            ))}
          </div>
        )}

        <div
          className={`relative rounded-full transition-all shadow-xl flex items-center px-3 sm:px-4 py-2.5 sm:py-3 gap-2 border ${
            isLight
              ? 'bg-white/80 border-purple-200/80 shadow-purple-900/5 focus-within:border-purple-400/80 focus-within:ring-2 focus-within:ring-purple-300/30'
              : 'bg-[#202123] hover:bg-[#25262a] focus-within:bg-[#25262a] border-white/10 hover:border-white/15 focus-within:border-white/20'
          }`}
        >
          {/* Plus (+) Button for Attachments & Tools */}
          <div className="relative">
            <button
              type="button"
              onClick={() => setIsMenuOpen((prev) => !prev)}
              className={`p-1.5 rounded-full transition-colors ${
                isLight
                  ? 'text-slate-600 hover:text-slate-900 hover:bg-purple-100'
                  : 'text-slate-400 hover:text-white hover:bg-white/10'
              }`}
              title="Add attachment or select tool"
            >
              {uploadingFile ? (
                <Loader2 size={18} className="animate-spin text-purple-400" />
              ) : (
                <Plus size={18} />
              )}
            </button>

            {/* Plus Button Context Menu */}
            {isMenuOpen && (
              <div
                className={`absolute left-0 bottom-full mb-3 w-56 rounded-2xl p-1.5 shadow-2xl border z-50 text-xs backdrop-blur-xl ${
                  isLight
                    ? 'bg-white/95 border-purple-200 text-slate-800'
                    : 'bg-[#1e1f23] border-white/10 text-slate-200'
                }`}
              >
                <button
                  type="button"
                  onClick={() => {
                    fileInputRef.current?.click();
                    setIsMenuOpen(false);
                  }}
                  className="w-full flex items-center gap-2.5 px-3 py-2 rounded-xl hover:bg-purple-500/10 hover:text-purple-400 transition-colors text-left"
                >
                  <Paperclip size={15} />
                  <span>Attach photos & files</span>
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setInput('generate image of ');
                    setIsMenuOpen(false);
                  }}
                  className="w-full flex items-center gap-2.5 px-3 py-2 rounded-xl hover:bg-purple-500/10 hover:text-purple-400 transition-colors text-left"
                >
                  <Sparkles size={15} />
                  <span>Generate AI image</span>
                </button>
                <button
                  type="button"
                  onClick={() => {
                    onOpenDocModal?.();
                    setIsMenuOpen(false);
                  }}
                  className="w-full flex items-center gap-2.5 px-3 py-2 rounded-xl hover:bg-purple-500/10 hover:text-purple-400 transition-colors text-left"
                >
                  <FileText size={15} />
                  <span>Document Knowledge RAG</span>
                </button>
                <button
                  type="button"
                  onClick={() => {
                    onOpenPluginsModal?.();
                    setIsMenuOpen(false);
                  }}
                  className="w-full flex items-center gap-2.5 px-3 py-2 rounded-xl hover:bg-purple-500/10 hover:text-purple-400 transition-colors text-left"
                >
                  <Boxes size={15} />
                  <span>Plugins & Skills Store</span>
                </button>
              </div>
            )}
          </div>

          {/* Hidden File Input */}
          <input
            type="file"
            ref={fileInputRef}
            onChange={(e) => {
              if (e.target.files) handleFiles(e.target.files);
            }}
            multiple
            accept="image/*,video/*,audio/*,.pdf,.doc,.docx,.txt,.csv,.json,.py,.js"
            className="hidden"
          />

          {/* Text Input (matching Ask ChatGPT pill) */}
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            onPaste={handlePaste}
            placeholder={
              isListening
                ? 'Listening to your voice...'
                : isThinking
                ? 'Ask Pluto AI with Deep Reasoning...'
                : 'Ask Pluto AI...'
            }
            className={`flex-1 bg-transparent text-sm focus:outline-none min-w-0 ${
              isLight
                ? 'text-slate-900 placeholder-slate-400'
                : 'text-slate-100 placeholder-slate-400'
            }`}
          />

          {/* Right Controls inside pill: [Think] [Mic] [Waveform] */}
          <div className="flex items-center gap-1.5 sm:gap-2 flex-shrink-0">
            {/* Think Button */}
            <button
              type="button"
              onClick={() => setIsThinking((v) => !v)}
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium transition-all ${
                isThinking
                  ? 'bg-purple-600/30 text-purple-300 border border-purple-500/50 shadow-sm'
                  : isLight
                  ? 'text-slate-500 hover:text-slate-800 hover:bg-purple-100/60'
                  : 'text-slate-400 hover:text-white hover:bg-white/10'
              }`}
              title="Toggle Deep Reasoning (Think mode)"
            >
              <Brain size={14} className={isThinking ? 'text-purple-400' : 'text-slate-400'} />
              <span className="hidden sm:inline">Think</span>
            </button>

            {/* Mic Voice-to-Text Button & Language Switch */}
            <div className="flex items-center gap-0.5">
              <button
                type="button"
                onClick={() => setLanguage((l) => (l === 'bn-BD' ? 'en-US' : 'bn-BD'))}
                className={`text-[10px] font-bold px-1.5 py-0.5 rounded transition-all border ${
                  language === 'bn-BD'
                    ? 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30'
                    : isLight
                    ? 'bg-purple-100 text-purple-700 border-purple-200'
                    : 'bg-white/10 text-slate-300 border-white/15'
                }`}
                title="কণ্ঠের ভাষা পরিবর্তন করুন (বাংলা ⇄ English)"
              >
                {language === 'bn-BD' ? 'বাং' : 'EN'}
              </button>
              <button
                type="button"
                onClick={handleToggleListening}
                className={`p-1.5 rounded-full transition-colors ${
                  isListening
                    ? 'text-rose-400 animate-pulse bg-rose-500/10'
                    : isLight
                    ? 'text-slate-500 hover:text-slate-800 hover:bg-purple-100/60'
                    : 'text-slate-400 hover:text-white hover:bg-white/10'
                }`}
                title={isListening ? 'কণ্ঠ গ্রহণ বন্ধ করুন' : `কণ্ঠ সহকারী টাইপিং (${language === 'bn-BD' ? 'বাংলা' : 'English'})`}
              >
                <Mic size={17} />
              </button>
            </div>

            {/* Blue Circular Waveform Button (launches Live Voice Mode) */}
            <button
              type="button"
              onClick={onOpenVoiceModal}
              className="w-8 h-8 rounded-full bg-blue-600 hover:bg-blue-500 text-white flex items-center justify-center shadow-lg shadow-blue-600/30 transition-transform hover:scale-105"
              title="Start Live Voice Assistant"
            >
              <AudioLines size={16} />
            </button>
          </div>
        </div>
      </div>

      {/* 3. Stack of Suggestions directly under Input Capsule */}
      <div className="w-full max-w-2xl mt-3 space-y-2 text-left">
        {/* Row 1: Featured (Create an image or concept) with X dismiss button */}
        {!dismissedFeatured && (
          <div
            onClick={() => {
              setInput('generate image of ');
            }}
            className={`w-full rounded-2xl border px-4 py-2.5 sm:py-3 flex items-center justify-between cursor-pointer group transition-all text-xs sm:text-sm ${
              isLight
                ? 'bg-white/60 hover:bg-white/90 border-purple-200/70 text-slate-800 shadow-xs'
                : 'bg-[#202123]/70 hover:bg-[#25262a] border-white/5 text-slate-200'
            }`}
          >
            <div className="flex items-center gap-3 min-w-0">
              <ImageIcon
                size={16}
                className="text-slate-400 group-hover:text-purple-400 transition-colors flex-shrink-0"
              />
              <span className="truncate">Create an image or concept</span>
            </div>
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                setDismissedFeatured(true);
              }}
              className="p-1 rounded-md text-slate-500 hover:text-slate-300 transition-colors ml-2"
              title="Dismiss suggestion"
            >
              <X size={14} />
            </button>
          </div>
        )}

        {/* Row 2: Write, code, or edit */}
        <div
          onClick={() => {
            setInput('Write a clean, production-ready implementation of ');
          }}
          className={`w-full rounded-2xl border px-4 py-2 sm:py-2.5 flex items-center gap-3 cursor-pointer group transition-all text-xs ${
            isLight
              ? 'hover:bg-white/70 border-transparent hover:border-purple-200/50 text-slate-700'
              : 'hover:bg-[#202123]/60 border-transparent hover:border-white/5 text-slate-300'
          }`}
        >
          <PenLine
            size={16}
            className="text-slate-400 group-hover:text-indigo-400 transition-colors flex-shrink-0"
          />
          <span className="truncate">Write, code, or edit</span>
        </div>

        {/* Row 3: Search the web */}
        <div
          onClick={() => {
            setWebSearchEnabled(true);
            setInput('What are the latest developments in ');
          }}
          className={`w-full rounded-2xl border px-4 py-2 sm:py-2.5 flex items-center gap-3 cursor-pointer group transition-all text-xs ${
            isLight
              ? 'hover:bg-white/70 border-transparent hover:border-purple-200/50 text-slate-700'
              : 'hover:bg-[#202123]/60 border-transparent hover:border-white/5 text-slate-300'
          }`}
        >
          <Globe
            size={16}
            className="text-slate-400 group-hover:text-emerald-400 transition-colors flex-shrink-0"
          />
          <span className="truncate">Search the web</span>
        </div>

        {/* Row 4: Solve complex mathematics */}
        <div
          onClick={() => {
            setInput('Solve the equation x^2 - 5x + 6 = 0 with step-by-step SymPy verification');
          }}
          className={`w-full rounded-2xl border px-4 py-2 sm:py-2.5 flex items-center gap-3 cursor-pointer group transition-all text-xs ${
            isLight
              ? 'hover:bg-white/70 border-transparent hover:border-purple-200/50 text-slate-700'
              : 'hover:bg-[#202123]/60 border-transparent hover:border-white/5 text-slate-300'
          }`}
        >
          <Calculator
            size={16}
            className="text-slate-400 group-hover:text-amber-400 transition-colors flex-shrink-0"
          />
          <span className="truncate">Solve complex mathematics</span>
        </div>
      </div>
    </div>
  );
}
