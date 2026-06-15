import { useState, useEffect, useRef, useCallback } from 'react';

export const useSpeechRecognition = (language) => {
  const [isListening, setIsListening] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [error, setError] = useState(null);
  const recognitionRef = useRef(null);

  // Map internal language name to BCP-47 language tag
  const getLanguageTag = (langName) => {
    switch (langName) {
      case 'Hindi':
        return 'hi-IN';
      case 'Marathi':
        return 'mr-IN';
      case 'English':
      default:
        return 'en-IN';
    }
  };

  useEffect(() => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      setError('Web Speech API is not supported in this browser.');
      return;
    }

    const recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = getLanguageTag(language);

    recognition.onstart = () => {
      setIsListening(true);
      setError(null);
    };

    recognition.onresult = (event) => {
      if (event.results && event.results.length > 0) {
        const resultText = event.results[0][0].transcript;
        setTranscript(resultText);
      }
    };

    recognition.onerror = (event) => {
      // Ignore 'no-speech' error to keep UI clean, but handle others
      if (event.error !== 'no-speech') {
        logger_log('Speech recognition error:', event.error);
        setError(event.error);
      }
      setIsListening(false);
    };

    recognition.onend = () => {
      setIsListening(false);
    };

    recognitionRef.current = recognition;

    return () => {
      if (recognitionRef.current) {
        recognitionRef.current.abort();
      }
    };
  }, [language]);

  const startListening = useCallback(() => {
    if (!recognitionRef.current) return;
    setTranscript('');
    setError(null);
    try {
      recognitionRef.current.start();
    } catch (err) {
      console.warn('Speech recognition already active or error starting:', err);
    }
  }, []);

  const stopListening = useCallback(() => {
    if (!recognitionRef.current) return;
    try {
      recognitionRef.current.stop();
    } catch (err) {
      console.warn('Error stopping speech recognition:', err);
    }
  }, []);

  // Simple browser log wrapper
  const logger_log = (msg, err) => {
    console.error(msg, err);
  };

  return {
    isListening,
    transcript,
    setTranscript,
    error,
    startListening,
    stopListening,
    isSupported: !!(window.SpeechRecognition || window.webkitSpeechRecognition),
  };
};
