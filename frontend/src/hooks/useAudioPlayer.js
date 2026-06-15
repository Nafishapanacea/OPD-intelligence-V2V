import { useState, useEffect, useRef, useCallback } from 'react';

export const useAudioPlayer = () => {
  const [isPlaying, setIsPlaying] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const audioRef = useRef(null);

  // Play audio from a URL
  const playAudio = useCallback((url) => {
    if (!url) return;

    // Stop existing audio if playing
    if (audioRef.current) {
      try {
        audioRef.current.pause();
        audioRef.current.src = '';
      } catch (err) {
        console.warn('Error cleanup old audio:', err);
      }
    }

    setIsLoading(true);
    setIsPlaying(false);
    setError(null);

    const audio = new Audio(url);
    audioRef.current = audio;

    audio.oncanplaythrough = () => {
      setIsLoading(false);
      audio.play()
        .then(() => {
          setIsPlaying(true);
        })
        .catch((err) => {
          console.warn('Audio play was prevented by browser autoplay policy:', err);
          setError('Playback blocked by browser settings. Click the speaker to listen.');
          setIsPlaying(false);
        });
    };

    audio.onended = () => {
      setIsPlaying(false);
    };

    audio.onerror = (e) => {
      console.error('Audio playback error event:', e);
      setError('Failed to load text-to-speech audio.');
      setIsLoading(false);
      setIsPlaying(false);
    };
  }, []);

  const stopAudio = useCallback(() => {
    if (audioRef.current) {
      audioRef.current.pause();
      setIsPlaying(false);
    }
  }, []);

  // Clean up audio references on unmount
  useEffect(() => {
    return () => {
      if (audioRef.current) {
        try {
          audioRef.current.pause();
          audioRef.current.src = '';
        } catch (err) {
          // Ignore pause errors on unmount
        }
      }
    };
  }, []);

  return {
    isPlaying,
    isLoading,
    error,
    playAudio,
    stopAudio,
  };
};
