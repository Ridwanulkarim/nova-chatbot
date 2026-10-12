import { useState, useEffect, useRef, useCallback } from 'react';

export function useVoiceAssistant() {
  const [isListening, setIsListening] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [language, setLanguage] = useState('bn-BD'); // 'bn-BD' (Bangla) | 'en-US' (English)
  const recognitionRef = useRef(null);

  const hasSpeechRecognition = typeof window !== 'undefined' && ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window);
  const hasSpeechSynthesis = typeof window !== 'undefined' && 'speechSynthesis' in window;

  // Initialize Speech Recognition
  useEffect(() => {
    if (!hasSpeechRecognition) return;
    const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
    const rec = new SpeechRec();
    rec.continuous = false;
    rec.interimResults = true;
    rec.lang = language || 'bn-BD';

    rec.onstart = () => {
      setIsListening(true);
    };

    rec.onresult = (event) => {
      let finalTranscript = '';
      for (let i = event.resultIndex; i < event.results.length; ++i) {
        if (event.results[i].isFinal) {
          finalTranscript += event.results[i][0].transcript;
        } else {
          finalTranscript += event.results[i][0].transcript;
        }
      }
      setTranscript(finalTranscript);
    };

    rec.onerror = (event) => {
      console.warn('Speech recognition error:', event.error);
      setIsListening(false);
    };

    rec.onend = () => {
      setIsListening(false);
    };

    recognitionRef.current = rec;

    return () => {
      if (recognitionRef.current) {
        try {
          recognitionRef.current.abort();
        } catch (e) {}
      }
    };
  }, [hasSpeechRecognition, language]);

  // Start listening with optional language override
  const startListening = useCallback((onResultCallback, langOverride) => {
    if (!recognitionRef.current) return;
    setTranscript('');
    try {
      const activeLang = langOverride || language || 'bn-BD';
      recognitionRef.current.lang = activeLang;

      if (onResultCallback) {
        recognitionRef.current.onresult = (e) => {
          let text = '';
          for (let i = e.resultIndex; i < e.results.length; ++i) {
            text += e.results[i][0].transcript;
          }
          setTranscript(text);
          if (e.results[e.results.length - 1].isFinal) {
            onResultCallback(text);
          }
        };
      }
      recognitionRef.current.start();
    } catch (e) {
      console.warn('Recognition start error:', e);
    }
  }, [language]);

  // Stop listening
  const stopListening = useCallback(() => {
    if (recognitionRef.current) {
      try {
        recognitionRef.current.stop();
      } catch (e) {}
    }
    setIsListening(false);
  }, []);

  // Text to Speech with automatic Bengali vs English language & voice selection
  const speak = useCallback((text, onEnd, langOverride) => {
    if (!hasSpeechSynthesis) return;

    window.speechSynthesis.cancel(); // Stop any ongoing speech

    // Strip markdown formatting for cleaner natural speech
    const cleanText = text
      .replace(/```[\s\S]*?```/g, '')
      .replace(/`([^`]+)`/g, '$1')
      .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
      .replace(/[*_#>-]/g, '')
      .trim();

    if (!cleanText) return;

    const utterance = new SpeechSynthesisUtterance(cleanText);
    utterance.rate = 1.0;
    utterance.pitch = 1.0;

    // Detect if content contains Bengali characters
    const hasBengali = /[\u0980-\u09FF]/.test(cleanText);
    const targetLang = langOverride || (hasBengali ? 'bn-BD' : language === 'bn-BD' ? 'bn-BD' : 'en-US');

    utterance.lang = targetLang;

    // Select suitable voice
    const voices = window.speechSynthesis.getVoices();
    if (hasBengali || targetLang.startsWith('bn')) {
      const bengaliVoice = voices.find(
        (v) => v.lang.startsWith('bn') || v.name.toLowerCase().includes('bangla') || v.name.toLowerCase().includes('bengali')
      );
      if (bengaliVoice) utterance.voice = bengaliVoice;
    } else {
      const englishVoice = voices.find(
        (v) => (v.name.includes('Natural') || v.name.includes('Samantha') || v.name.includes('Google') || v.name.includes('Alex')) && v.lang.startsWith('en')
      );
      if (englishVoice) utterance.voice = englishVoice;
    }

    utterance.onstart = () => setIsSpeaking(true);
    utterance.onend = () => {
      setIsSpeaking(false);
      if (onEnd) onEnd();
    };
    utterance.onerror = () => setIsSpeaking(false);

    window.speechSynthesis.speak(utterance);
  }, [hasSpeechSynthesis, language]);

  const stopSpeaking = useCallback(() => {
    if (hasSpeechSynthesis) {
      window.speechSynthesis.cancel();
      setIsSpeaking(false);
    }
  }, [hasSpeechSynthesis]);

  return {
    isListening,
    isSpeaking,
    transcript,
    language,
    setLanguage,
    hasSpeechRecognition,
    hasSpeechSynthesis,
    startListening,
    stopListening,
    speak,
    stopSpeaking,
  };
}
