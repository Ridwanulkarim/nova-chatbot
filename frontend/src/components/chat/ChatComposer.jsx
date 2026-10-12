import React, { useState, useRef, useEffect } from 'react';
import { Send, Square, Globe, Paperclip, X, Mic, MicOff, Palette, Image as ImageIcon, Film, FileText, Loader2, UploadCloud } from 'lucide-react';
import { useChat } from '../../contexts/ChatContext';
import { useVoiceAssistant } from '../../hooks/useVoiceAssistant';
import { api, API_HOST } from '../../services/api';

export function ChatComposer({ onOpenDocModal, theme }) {
  const isLight = theme === 'lavender-glow';
  const {
    sendMessage,
    stopGeneration,
    isStreaming,
    webSearchEnabled,
    setWebSearchEnabled,
    attachedFiles,
    setAttachedFiles,
    selectedModel,
    availableModels,
    setSelectedModel,
    setErrorMessage,
  } = useChat();

  const [input, setInput] = useState('');
  const [imageMode, setImageMode] = useState(false);
  const [uploadingFile, setUploadingFile] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const textareaRef = useRef(null);
  const fileInputRef = useRef(null);

  const { isListening, startListening, stopListening, hasSpeechRecognition, language, setLanguage } = useVoiceAssistant();

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 180)}px`;
    }
  }, [input]);

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
      if (setErrorMessage) {
        setErrorMessage(err.message || 'Image upload failed. Please try again.');
      }
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

  const handleSubmit = (e) => {
    if (e) e.preventDefault();
    if ((!input.trim() && attachedFiles.length === 0) || isStreaming || uploadingFile) return;
    
    let textToSend = input.trim();
    if (!textToSend && attachedFiles.length > 0) {
      const hasImg = attachedFiles.some((f) => f.media_type === 'image' || f.filename?.match(/\.(png|jpg|jpeg|webp)$/i));
      textToSend = hasImg
        ? "Please analyze and describe this attached image/screenshot in detail, reading all text and explaining what is shown."
        : "Please review and explain the attached file.";
    } else if (imageMode && !textToSend.toLowerCase().startsWith('/image')) {
      textToSend = `/image ${textToSend}`;
    }

    setInput('');
    setImageMode(false);
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
    sendMessage(textToSend);
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleMicToggle = () => {
    if (isListening) {
      stopListening();
    } else {
      startListening((text) => {
        setInput((prev) => (prev ? `${prev} ${text}` : text));
      }, language);
    }
  };

  const handleDirectFileUpload = async (e) => {
    await handleFiles(e.target.files);
    e.target.value = '';
  };

  const removeFile = (fileId) => {
    setAttachedFiles((prev) => prev.filter((f) => f.id !== fileId));
  };

  return (
    <div className="w-full max-w-3xl mx-auto px-4 pb-4">
      {/* Attached Media & Files Preview Bar */}
      {attachedFiles.length > 0 && (
        <div className="flex flex-wrap gap-2 mb-2.5 px-1 max-h-36 overflow-y-auto">
          {attachedFiles.map((f) => {
            const isImg = f.media_type === 'image' || f.url?.match(/\.(jpeg|jpg|gif|png|webp)$/i);
            const rawUrl = f.data_url || f.url || '';
            const fUrl = rawUrl ? (rawUrl.startsWith('/') ? `${API_HOST}${rawUrl}` : rawUrl) : '';

            return (
              <div
                key={f.id}
                className={`group relative flex items-center gap-2 p-1.5 pr-2.5 rounded-xl border shadow-md text-xs ${
                  isLight
                    ? 'bg-purple-50/90 border-purple-200 text-slate-800'
                    : 'bg-slate-900 border-slate-700/80 text-slate-200'
                }`}
              >
                {isImg && fUrl ? (
                  <img
                    src={fUrl}
                    alt={f.filename}
                    className={`w-8 h-8 rounded-lg object-cover border flex-shrink-0 ${
                      isLight ? 'border-purple-200' : 'border-slate-700'
                    }`}
                  />
                ) : isVid ? (
                  <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${
                    isLight ? 'bg-indigo-100 text-indigo-700' : 'bg-indigo-950 text-indigo-400'
                  }`}>
                    <Film size={16} />
                  </div>
                ) : (
                  <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${
                    isLight ? 'bg-purple-100 text-purple-700' : 'bg-slate-800 text-brand-400'
                  }`}>
                    <FileText size={16} />
                  </div>
                )}

                <div className="truncate max-w-[140px]">
                  <div className="truncate font-medium">{f.filename}</div>
                  <div className={`text-[10px] uppercase tracking-wider ${
                    isLight ? 'text-slate-500' : 'text-slate-400'
                  }`}>
                    {f.media_type || 'file'}
                  </div>
                </div>

                <button
                  type="button"
                  onClick={() => removeFile(f.id)}
                  className={`p-1 rounded-full transition-colors ml-1 ${
                    isLight
                      ? 'hover:bg-purple-200/60 text-slate-500 hover:text-rose-600'
                      : 'hover:bg-slate-800 text-slate-400 hover:text-rose-400'
                  }`}
                >
                  <X size={12} />
                </button>
              </div>
            );
          })}
        </div>
      )}

      {/* Main Composer Box */}
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={`relative rounded-2xl border transition-all shadow-lg overflow-hidden ${
          isLight
            ? 'bg-white/95 text-slate-900 shadow-purple-950/5'
            : 'bg-slate-900 text-slate-100'
        } ${
          isDragging
            ? 'border-brand-400 ring-2 ring-brand-400/50'
            : imageMode
            ? 'border-purple-500/80 ring-1 ring-purple-500/40'
            : isListening
            ? 'border-rose-500/80 ring-1 ring-rose-500/40 animate-pulse'
            : isLight
            ? 'border-purple-200/90 focus-within:border-purple-400 focus-within:ring-1 focus-within:ring-purple-300/30'
            : 'border-slate-700/70 focus-within:border-brand-500/80 focus-within:ring-1 focus-within:ring-brand-500/30'
        }`}
      >
        {/* Full Drop Overlay */}
        {isDragging && (
          <div className="absolute inset-0 z-30 bg-slate-950/90 border-2 border-dashed border-brand-400 flex flex-col items-center justify-center backdrop-blur-sm pointer-events-none">
            <UploadCloud size={36} className="text-brand-400 animate-bounce mb-1" />
            <p className="text-sm font-semibold text-white">Drop your image, screenshot, or file</p>
            <p className="text-xs text-brand-300">Pluto AI will visually analyze and inspect it</p>
          </div>
        )}

        {/* Image Mode Banner */}
        {imageMode && (
          <div className={`px-4 pt-2.5 pb-0 flex items-center justify-between text-xs font-medium ${
            isLight ? 'text-purple-700' : 'text-purple-300'
          }`}>
            <span className="flex items-center gap-1.5">
              <Palette size={14} className={isLight ? 'text-purple-600' : 'text-purple-400'} />
              <span>AI Image Generation Mode Active</span>
            </span>
            <button
              onClick={() => setImageMode(false)}
              className={isLight ? 'text-slate-500 hover:text-slate-900' : 'text-slate-400 hover:text-white'}
            >
              <X size={13} />
            </button>
          </div>
        )}

        <textarea
          ref={textareaRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          onPaste={handlePaste}
          placeholder={
            imageMode
              ? 'Describe the image you want Pluto AI to generate in detail...'
              : isListening
              ? 'Listening to your voice... Speak now.'
              : 'Ask anything, paste screenshots (Cmd+V), attach files, or drag & drop...'
          }
          rows={1}
          className={`w-full bg-transparent px-4 pt-3.5 pb-12 text-sm resize-none focus:outline-none max-h-48 ${
            isLight
              ? 'text-slate-900 placeholder-slate-400'
              : 'text-slate-100 placeholder-slate-400'
          }`}
        />

        {/* Hidden Multimedia Input */}
        <input
          type="file"
          ref={fileInputRef}
          onChange={handleDirectFileUpload}
          multiple
          accept="image/*,video/*,audio/*,.pdf,.doc,.docx,.txt,.csv,.json,.py,.js,.html"
          className="hidden"
        />

        {/* Bottom Toolbar Controls */}
        <div className="absolute bottom-2.5 left-3 right-3 flex items-center justify-between pointer-events-none">
          <div className="flex items-center gap-2 pointer-events-auto">
            {/* Attach Photos, Videos, Files Button */}
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              disabled={uploadingFile}
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium border border-transparent transition-all ${
                isLight
                  ? 'text-slate-600 hover:text-slate-900 hover:bg-purple-100/70'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
              }`}
              title="Attach photos, files, or videos"
            >
              {uploadingFile ? (
                <Loader2 size={13} className="animate-spin text-brand-400" />
              ) : (
                <Paperclip size={13} />
              )}
              <span>{uploadingFile ? 'Uploading...' : 'Attach'}</span>
            </button>

            {/* AI Image Generator Toggle */}
            <button
              type="button"
              onClick={() => setImageMode((prev) => !prev)}
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium transition-all ${
                imageMode
                  ? 'bg-purple-500/20 text-purple-700 border border-purple-400/50 shadow-xs'
                  : isLight
                  ? 'text-slate-600 hover:text-slate-900 hover:bg-purple-100/70 border border-transparent'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800 border border-transparent'
              }`}
              title="Generate AI images"
            >
              <Palette size={13} className={imageMode ? 'text-purple-600' : ''} />
              <span>Generate Image</span>
            </button>

            {/* Web Search Toggle */}
            <button
              type="button"
              onClick={() => setWebSearchEnabled((prev) => !prev)}
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium transition-all ${
                webSearchEnabled
                  ? isLight
                    ? 'bg-purple-100 text-purple-900 border border-purple-300 shadow-xs'
                    : 'bg-brand-500/20 text-brand-300 border border-brand-500/50 shadow-sm shadow-brand-500/20'
                  : isLight
                  ? 'text-slate-600 hover:text-slate-900 hover:bg-purple-100/70 border border-transparent'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800 border border-transparent'
              }`}
              title="Search live web for real-time sources"
            >
              <Globe size={13} className={webSearchEnabled ? (isLight ? 'text-purple-600' : 'text-brand-400') : ''} />
              <span className="hidden sm:inline">Web Search</span>
            </button>

            {/* Quick Model Selector */}
            {availableModels.length > 1 && (
              <select
                value={selectedModel}
                onChange={(e) => setSelectedModel(e.target.value)}
                className={`border rounded-md text-[11px] px-2 py-0.5 focus:outline-none cursor-pointer hidden md:block ${
                  isLight
                    ? 'bg-purple-50 text-slate-800 border-purple-200 focus:border-purple-400'
                    : 'bg-slate-850 text-slate-300 border-slate-700/60 focus:border-brand-500'
                }`}
              >
                {availableModels.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.name}
                  </option>
                ))}
              </select>
            )}
          </div>

          {/* Right Action Controls: Voice Mic & Send */}
          <div className="flex items-center gap-2 pointer-events-auto">
            {/* Voice Input Microphone & Language Switcher */}
            {hasSpeechRecognition && (
              <div className="flex items-center gap-1">
                <button
                  type="button"
                  onClick={() => setLanguage((l) => (l === 'bn-BD' ? 'en-US' : 'bn-BD'))}
                  className={`text-[10px] font-bold px-1.5 py-0.5 rounded transition-all border ${
                    language === 'bn-BD'
                      ? 'bg-emerald-500/15 text-emerald-500 border-emerald-500/30'
                      : isLight
                      ? 'bg-purple-100 text-purple-700 border-purple-200'
                      : 'bg-slate-800 text-slate-300 border-slate-700'
                  }`}
                  title="কণ্ঠের ভাষা পরিবর্তন করুন (বাংলা ⇄ English)"
                >
                  {language === 'bn-BD' ? 'বাং' : 'EN'}
                </button>
                <button
                  type="button"
                  onClick={handleMicToggle}
                  className={`p-1.5 rounded-lg transition-all ${
                    isListening
                      ? 'bg-rose-600 text-white shadow-md shadow-rose-600/40 animate-pulse'
                      : isLight
                      ? 'text-slate-600 hover:text-slate-900 hover:bg-purple-100'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
                  }`}
                  title={isListening ? 'Stop listening' : `Voice dictation (${language === 'bn-BD' ? 'বাংলা' : 'English'})`}
                >
                  {isListening ? <MicOff size={16} /> : <Mic size={16} />}
                </button>
              </div>
            )}

            {/* Send / Stop Action Button */}
            {isStreaming ? (
              <button
                type="button"
                onClick={stopGeneration}
                className="flex items-center justify-center w-8 h-8 rounded-lg bg-rose-600 hover:bg-rose-500 text-white shadow-md transition-colors"
                title="Stop response"
              >
                <Square size={14} fill="currentColor" />
              </button>
            ) : (
              <button
                type="button"
                onClick={handleSubmit}
                disabled={!input.trim() && attachedFiles.length === 0}
                className={`flex items-center justify-center w-8 h-8 rounded-lg text-white shadow-md transition-all ${
                  input.trim() || attachedFiles.length > 0
                    ? imageMode
                      ? 'bg-purple-600 hover:bg-purple-500 shadow-purple-600/30'
                      : 'bg-brand-600 hover:bg-brand-500 shadow-brand-500/30'
                    : isLight
                    ? 'bg-purple-100 text-purple-300 cursor-not-allowed'
                    : 'bg-slate-800 text-slate-500 cursor-not-allowed'
                }`}
                title="Send message"
              >
                <Send size={14} />
              </button>
            )}
          </div>
        </div>
      </div>
      <p className={`text-[11px] text-center mt-2 ${
        isLight ? 'text-slate-500' : 'text-slate-400'
      }`}>
        Pluto AI can analyze photos, files, generate artwork, and speak responses.
      </p>
    </div>
  );
}
