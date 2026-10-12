import React, { useState, useEffect, useRef } from 'react';
import { X, Mic, MicOff, Volume2, VolumeX, Sparkles, PhoneOff, Languages, Globe } from 'lucide-react';
import { useChat } from '../../contexts/ChatContext';
import { useVoiceAssistant } from '../../hooks/useVoiceAssistant';

export function LiveVoiceModal({ isOpen, onClose, theme }) {
  const isLight = theme === 'lavender-glow';
  const { sendMessage, isStreaming, messages } = useChat();
  const {
    isListening,
    isSpeaking,
    hasSpeechRecognition,
    hasSpeechSynthesis,
    startListening,
    stopListening,
    speak,
    stopSpeaking,
  } = useVoiceAssistant();

  const [voiceMode, setVoiceMode] = useState('bengali'); // 'bengali' | 'translate' | 'english'
  const [liveTranscript, setLiveTranscript] = useState('');
  const [aiSpeechText, setAiSpeechText] = useState('');
  const [conversationState, setConversationState] = useState('idle'); // 'idle' | 'listening' | 'thinking' | 'speaking'
  const [isMuted, setIsMuted] = useState(false);
  const [sessionActive, setSessionActive] = useState(false);
  const silenceTimeoutRef = useRef(null);
  const lastAssistantMsgIdRef = useRef(null);

  // When modal opens/closes
  useEffect(() => {
    if (isOpen) {
      setSessionActive(true);
      setConversationState('idle');
      // Auto-start listening after short delay
      const t = setTimeout(() => {
        beginListening();
      }, 500);
      return () => clearTimeout(t);
    } else {
      setSessionActive(false);
      stopListening();
      stopSpeaking();
      setConversationState('idle');
      setLiveTranscript('');
      setAiSpeechText('');
    }
  }, [isOpen, voiceMode]);

  // Watch for assistant's new response arriving in chat
  useEffect(() => {
    if (!sessionActive || !isOpen) return;

    if (isStreaming) {
      setConversationState('thinking');
    } else {
      // Stream finished, find the newest assistant message
      const lastMsg = messages[messages.length - 1];
      if (lastMsg && lastMsg.role === 'assistant' && lastMsg.id !== lastAssistantMsgIdRef.current) {
        lastAssistantMsgIdRef.current = lastMsg.id;
        const text = lastMsg.content;
        setAiSpeechText(text);
        setConversationState('speaking');

        // Speak the assistant's answer aloud with automatic language voice detection
        const voiceLang = voiceMode === 'english' ? 'en-US' : 'bn-BD';
        speak(text, () => {
          // Callback when AI finishes speaking -> Automatically listen again!
          if (sessionActive && !isMuted) {
            beginListening();
          } else {
            setConversationState('idle');
          }
        }, voiceLang);
      }
    }
  }, [messages, isStreaming, sessionActive, isOpen, isMuted, voiceMode]);

  // Start listening for user speech with silence detection
  const beginListening = () => {
    if (isMuted || !hasSpeechRecognition) return;
    setLiveTranscript('');
    setConversationState('listening');

    const activeMicLang = voiceMode === 'english' ? 'en-US' : 'bn-BD';
    startListening((finalText) => {
      if (!finalText.trim()) return;
      setLiveTranscript(finalText);

      // Debounce slightly to allow user to finish their thought
      if (silenceTimeoutRef.current) clearTimeout(silenceTimeoutRef.current);
      silenceTimeoutRef.current = setTimeout(() => {
        handleSendVoiceQuery(finalText);
      }, 1100);
    }, activeMicLang);
  };

  const handleSendVoiceQuery = (query) => {
    if (!query.trim()) return;
    stopListening();
    setConversationState('thinking');

    let textToSend = query;
    if (voiceMode === 'translate') {
      textToSend = `[Real-Time Voice Translation Mode]: The user spoke: "${query}". If this is English, translate it accurately, naturally, and fluently into Bengali (বাংলা) and provide phonetic pronunciation. If this is Bengali, translate it accurately into clear English. Provide the translated speech directly so it sounds completely natural when spoken aloud.`;
    } else if (voiceMode === 'bengali') {
      textToSend = `[বাংলা কণ্ঠ সহকারী মোড]: "${query}"। অনুগ্রহ করে সম্পূর্ণ প্রাকৃতিক ও প্রাঞ্জল বাংলায় উত্তর দিন।`;
    }

    sendMessage(textToSend);
  };

  const toggleMute = () => {
    if (isMuted) {
      setIsMuted(false);
      beginListening();
    } else {
      setIsMuted(true);
      stopListening();
      setConversationState('idle');
    }
  };

  const handleInterrupt = () => {
    stopSpeaking();
    if (silenceTimeoutRef.current) clearTimeout(silenceTimeoutRef.current);
    beginListening();
  };

  if (!isOpen) return null;

  return (
    <div className={`fixed inset-0 z-50 flex flex-col justify-between p-4 sm:p-6 backdrop-blur-2xl select-none animate-in fade-in duration-300 ${
      isLight ? 'bg-white/95 text-slate-900' : 'bg-slate-950/95 text-slate-100'
    }`}>
      {/* Top Bar with Title & Bangla Translation Switcher */}
      <div className="flex flex-col sm:flex-row items-center justify-between w-full max-w-4xl mx-auto gap-3 flex-shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-brand-500 to-indigo-500 flex items-center justify-center shadow-lg shadow-brand-500/25">
            <Sparkles size={16} className="text-white animate-spin-slow" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className={`font-semibold text-sm tracking-wide ${
                isLight ? 'text-slate-900' : 'text-white'
              }`}>
                Nova Live Voice
              </span>
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium bg-emerald-500/10 text-emerald-500 border border-emerald-500/20">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-ping" />
                Live
              </span>
            </div>
            <p className={`text-xs ${isLight ? 'text-slate-500' : 'text-slate-400'}`}>
              বাংলা ও ইংরেজি কণ্ঠ সহকারী ও অনুবাদ
            </p>
          </div>
        </div>

        {/* Voice Mode Selector: [ 🇧🇩 বাংলা | 🔄 অনুবাদ (Translate) | 🇺🇸 English ] */}
        <div className={`flex items-center p-1 rounded-full border text-xs shadow-xs transition-colors ${
          isLight
            ? 'bg-purple-50 border-purple-200'
            : 'bg-slate-900/90 border-slate-700/80'
        }`}>
          <button
            onClick={() => {
              setVoiceMode('bengali');
              stopSpeaking();
              if (sessionActive && !isMuted) beginListening();
            }}
            className={`px-3 py-1.5 rounded-full font-medium transition-all flex items-center gap-1.5 ${
              voiceMode === 'bengali'
                ? isLight
                  ? 'bg-white text-purple-950 shadow-xs font-semibold'
                  : 'bg-emerald-600 text-white shadow-xs font-semibold'
                : isLight
                ? 'text-slate-600 hover:text-slate-900'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            <span>🇧🇩 বাংলা</span>
          </button>

          <button
            onClick={() => {
              setVoiceMode('translate');
              stopSpeaking();
              if (sessionActive && !isMuted) beginListening();
            }}
            className={`px-3 py-1.5 rounded-full font-medium transition-all flex items-center gap-1.5 ${
              voiceMode === 'translate'
                ? isLight
                  ? 'bg-white text-purple-950 shadow-xs font-semibold'
                  : 'bg-indigo-600 text-white shadow-xs font-semibold'
                : isLight
                ? 'text-slate-600 hover:text-slate-900'
                : 'text-slate-400 hover:text-white'
            }`}
            title="বাংলা ⇄ English লাইভ কণ্ঠ অনুবাদ"
          >
            <Languages size={13} />
            <span>🔄 লাইভ অনুবাদ</span>
          </button>

          <button
            onClick={() => {
              setVoiceMode('english');
              stopSpeaking();
              if (sessionActive && !isMuted) beginListening();
            }}
            className={`px-3 py-1.5 rounded-full font-medium transition-all flex items-center gap-1.5 ${
              voiceMode === 'english'
                ? isLight
                  ? 'bg-white text-purple-950 shadow-xs font-semibold'
                  : 'bg-slate-800 text-white shadow-xs font-semibold'
                : isLight
                ? 'text-slate-600 hover:text-slate-900'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            <span>🇺🇸 English</span>
          </button>
        </div>

        <button
          onClick={onClose}
          className={`p-2.5 rounded-full border transition-all shadow-md ${
            isLight
              ? 'bg-purple-50 hover:bg-purple-100 border-purple-200 text-slate-600 hover:text-slate-900'
              : 'bg-slate-900/80 hover:bg-slate-800 border-slate-800 text-slate-400 hover:text-white'
          }`}
          title="Exit Voice Mode"
        >
          <X size={20} />
        </button>
      </div>

      {/* Center Interactive Animated Audio Orb */}
      <div className="flex-1 flex flex-col items-center justify-center relative my-4 sm:my-6">
        {/* Pulsating Orb Visualization */}
        <div
          onClick={conversationState === 'speaking' ? handleInterrupt : beginListening}
          className="relative cursor-pointer group flex items-center justify-center"
        >
          {/* Outer glowing pulsing rings */}
          <div
            className={`absolute w-72 h-72 rounded-full blur-3xl transition-all duration-700 pointer-events-none opacity-40 ${
              conversationState === 'listening'
                ? voiceMode === 'translate' ? 'bg-indigo-500 scale-125 animate-pulse' : 'bg-emerald-500 scale-125 animate-pulse'
                : conversationState === 'speaking'
                ? 'bg-indigo-500 scale-125 animate-pulse'
                : conversationState === 'thinking'
                ? 'bg-amber-500 scale-110 animate-spin-slow'
                : 'bg-brand-600 scale-95 opacity-20'
            }`}
          />

          <div
            className={`absolute w-60 h-60 rounded-full border border-brand-500/20 transition-all duration-500 ${
              conversationState === 'listening'
                ? voiceMode === 'translate' ? 'border-indigo-400/50 scale-110' : 'border-emerald-400/50 scale-110'
                : conversationState === 'speaking'
                ? 'border-indigo-400/50 scale-115 animate-ping duration-1000'
                : 'scale-100'
            }`}
          />

          {/* Core Orb */}
          <div
            className={`w-44 h-44 rounded-full flex items-center justify-center shadow-2xl transition-all duration-500 relative overflow-hidden ${
              conversationState === 'listening'
                ? voiceMode === 'translate'
                  ? 'bg-gradient-to-tr from-indigo-600 via-purple-600 to-pink-500 scale-105 shadow-indigo-500/50 ring-4 ring-indigo-400/30'
                  : 'bg-gradient-to-tr from-emerald-600 via-teal-500 to-cyan-400 scale-105 shadow-emerald-500/50 ring-4 ring-emerald-400/30'
                : conversationState === 'speaking'
                ? 'bg-gradient-to-tr from-indigo-600 via-purple-600 to-brand-500 scale-110 shadow-indigo-500/50 ring-4 ring-indigo-400/30'
                : conversationState === 'thinking'
                ? 'bg-gradient-to-tr from-amber-600 via-brand-600 to-indigo-600 scale-95 shadow-amber-500/30 ring-2 ring-amber-400/20'
                : 'bg-gradient-to-tr from-slate-800 via-slate-700 to-brand-900 scale-95 shadow-brand-900/20 ring-1 ring-slate-700'
            }`}
          >
            {/* Dynamic Sound Wave Icon inside core */}
            {conversationState === 'listening' && (
              <div className="flex items-center gap-1.5 h-12">
                <span className="w-1.5 h-6 bg-white/90 rounded-full animate-bounce [animation-delay:-0.3s]" />
                <span className="w-1.5 h-12 bg-white rounded-full animate-bounce [animation-delay:-0.15s]" />
                <span className="w-1.5 h-8 bg-white/90 rounded-full animate-bounce [animation-delay:-0.4s]" />
                <span className="w-1.5 h-10 bg-white rounded-full animate-bounce [animation-delay:-0.2s]" />
                <span className="w-1.5 h-5 bg-white/90 rounded-full animate-bounce" />
              </div>
            )}

            {conversationState === 'speaking' && (
              <div className="flex items-center gap-1.5 h-12">
                <span className="w-1.5 h-8 bg-white rounded-full animate-bounce [animation-delay:-0.2s]" />
                <span className="w-1.5 h-12 bg-white rounded-full animate-bounce [animation-delay:-0.35s]" />
                <span className="w-1.5 h-10 bg-white rounded-full animate-bounce [animation-delay:-0.1s]" />
                <span className="w-1.5 h-14 bg-white rounded-full animate-bounce [animation-delay:-0.25s]" />
                <span className="w-1.5 h-7 bg-white rounded-full animate-bounce" />
              </div>
            )}

            {conversationState === 'thinking' && (
              <div className="w-10 h-10 border-3 border-white/20 border-t-white rounded-full animate-spin" />
            )}

            {conversationState === 'idle' && (
              <Mic size={36} className="text-slate-300 group-hover:scale-110 transition-transform" />
            )}
          </div>
        </div>

        {/* Live Conversation State Indicator Pill */}
        <div className="mt-8 flex items-center justify-center">
          <span
            className={`px-4 py-1.5 rounded-full text-xs font-medium tracking-wide border shadow-md transition-all duration-300 ${
              conversationState === 'listening'
                ? voiceMode === 'translate'
                  ? isLight ? 'bg-indigo-50 text-indigo-700 border-indigo-300' : 'bg-indigo-500/10 text-indigo-300 border-indigo-500/30'
                  : isLight ? 'bg-emerald-50 text-emerald-700 border-emerald-300' : 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30'
                : conversationState === 'speaking'
                ? isLight ? 'bg-purple-100 text-purple-700 border-purple-300' : 'bg-indigo-500/10 text-indigo-300 border-indigo-500/30'
                : conversationState === 'thinking'
                ? isLight ? 'bg-amber-50 text-amber-700 border-amber-300' : 'bg-amber-500/10 text-amber-300 border-amber-500/30'
                : isLight ? 'bg-purple-50 text-purple-800 border-purple-200' : 'bg-slate-800/80 text-slate-300 border-slate-700'
            }`}
          >
            {conversationState === 'listening' && (
              voiceMode === 'translate'
                ? 'শুনছি... বাংলা বা ইংরেজিতে কথা বলুন (Listening...)'
                : voiceMode === 'bengali'
                ? 'আপনার কথা শুনছি... বাংলায় বলুন'
                : 'Listening to you... Speak freely'
            )}
            {conversationState === 'speaking' && (
              voiceMode === 'translate'
                ? 'নোভা লাইভ অনুবাদ বলছে (থামাতে স্পর্শ করুন)'
                : voiceMode === 'bengali'
                ? 'নোভা বাংলায় কথা বলছে (থামাতে স্পর্শ করুন)'
                : 'Nova is speaking (Click orb to interrupt)'
            )}
            {conversationState === 'thinking' && (
              voiceMode === 'translate'
                ? 'অনুবাদ ও চিন্তা করছে...'
                : voiceMode === 'bengali'
                ? 'নোভা বাংলায় চিন্তা করছে...'
                : 'Nova is thinking...'
            )}
            {conversationState === 'idle' && (
              isMuted
                ? 'মাইক্রোফোন বন্ধ (Muted)'
                : voiceMode === 'translate'
                ? 'অনুবাদ করতে কথা বলুন (Live Bangla ⇄ EN)'
                : voiceMode === 'bengali'
                ? 'কথা বলতে স্পর্শ করুন (বাংলা কণ্ঠ সহকারী)'
                : 'Tap orb or mic to start speaking'
            )}
          </span>
        </div>

        {/* Live Subtitle / Transcript Area */}
        <div className={`w-full max-w-xl mt-6 min-h-[90px] px-6 py-4 rounded-2xl border backdrop-blur-md flex flex-col justify-center text-center ${
          isLight ? 'bg-white/80 border-purple-200 shadow-lg text-slate-800' : 'bg-slate-900/60 border-slate-800/80 text-slate-100'
        }`}>
          {liveTranscript && (
            <p className={`text-sm italic font-medium ${isLight ? 'text-purple-700' : 'text-cyan-300'}`}>
              &ldquo;{liveTranscript}&rdquo;
            </p>
          )}
          {!liveTranscript && aiSpeechText && conversationState === 'speaking' && (
            <p className={`text-xs line-clamp-3 leading-relaxed ${isLight ? 'text-slate-700' : 'text-slate-300'}`}>
              {aiSpeechText}
            </p>
          )}
          {!liveTranscript && (!aiSpeechText || conversationState !== 'speaking') && (
            <p className={`text-xs ${isLight ? 'text-slate-500' : 'text-slate-500'}`}>
              {voiceMode === 'translate'
                ? 'বাংলা অথবা ইংরেজিতে কথা বলুন, নোভা সরাসরি অনুবাদ করে বাংলায়/ইংরেজিতে পড়ে শোনাবে।'
                : voiceMode === 'bengali'
                ? 'বাংলায় যেকোনো প্রশ্ন করুন, নোভা বাংলায় উত্তর দেবে ও পড়ে শোনাবে।'
                : 'Start speaking in English, Nova will listen and answer aloud automatically.'}
            </p>
          )}
        </div>
      </div>

      {/* Bottom Controls Bar */}
      <div className="w-full max-w-md mx-auto flex items-center justify-center gap-5 pb-4">
        {/* Mute Button */}
        <button
          onClick={toggleMute}
          className={`p-4 rounded-full border transition-all duration-200 shadow-lg ${
            isMuted
              ? isLight ? 'bg-rose-100 text-rose-700 border-rose-300 hover:bg-rose-200' : 'bg-rose-500/20 text-rose-300 border-rose-500/40 hover:bg-rose-500/30'
              : isLight ? 'bg-purple-100 text-purple-900 border-purple-200 hover:bg-purple-200' : 'bg-slate-800 text-slate-200 border-slate-700 hover:bg-slate-700'
          }`}
          title={isMuted ? 'Unmute Microphone' : 'Mute Microphone'}
        >
          {isMuted ? <MicOff size={22} /> : <Mic size={22} />}
        </button>

        {/* Interrupt / Stop speaking Button */}
        {conversationState === 'speaking' ? (
          <button
            onClick={handleInterrupt}
            className={`p-4 rounded-full border transition-all shadow-lg flex items-center gap-2 ${
              isLight ? 'bg-amber-100 text-amber-800 border-amber-300 hover:bg-amber-200' : 'bg-amber-500/20 text-amber-300 border-amber-500/40 hover:bg-amber-500/30'
            }`}
            title="Interrupt AI"
          >
            <VolumeX size={22} />
          </button>
        ) : (
          <button
            onClick={beginListening}
            disabled={conversationState === 'listening' || isMuted}
            className={`p-4 rounded-full border transition-all shadow-lg ${
              conversationState === 'listening'
                ? isLight ? 'bg-cyan-100 text-cyan-800 border-cyan-300' : 'bg-cyan-500/20 text-cyan-300 border-cyan-500/40'
                : isLight ? 'bg-purple-100 text-purple-900 border-purple-200 hover:bg-purple-200' : 'bg-slate-800 text-slate-200 border-slate-700 hover:bg-slate-700'
            }`}
            title="Listen now"
          >
            <Volume2 size={22} />
          </button>
        )}

        {/* End Voice Session Button */}
        <button
          onClick={onClose}
          className="p-4 rounded-full bg-rose-600 hover:bg-rose-700 text-white border border-rose-500 shadow-xl transition-transform hover:scale-105"
          title="End Voice Call"
        >
          <PhoneOff size={22} />
        </button>
      </div>
    </div>
  );
}
