import React, { useState, useEffect } from 'react';
import { Volume2, VolumeX, Mic, Send, AlertTriangle, HelpCircle, Loader2 } from 'lucide-react';
import { api } from '../services/api';
import { useSpeechRecognition } from '../hooks/useSpeechRecognition';
import { useAudioPlayer } from '../hooks/useAudioPlayer';
import { VoiceWaveform } from './VoiceWaveform';

export const AssessmentFlow = ({ sessionId, language, onComplete }) => {
  // Question sets matching the backend
  const questionsList = {
    English: [
      "Do you have a fever?",
      "Do you have a headache?",
      "Are you experiencing vomiting?",
      "Do you have chest pain?",
      "Do you have a cough?"
    ],
    Hindi: [
      "क्या आपको बुखार है?",
      "क्या आपको सिरदर्द है?",
      "क्या आपको उल्टी हो रही है?",
      "क्या आपको छाती में दर्द है?",
      "क्या आपको खांसी है?"
    ],
    Marathi: [
      "तुम्हाला ताप आहे का?",
      "तुम्हाला डोकेदुखी आहे का?",
      "तुम्हाला उलटी होत आहे का?",
      "तुम्हाला छातीत दुखत आहे का?",
      "तुम्हाला खोकला आहे का?"
    ]
  };

  const activeQuestions = questionsList[language] || questionsList.English;
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  const currentQuestion = activeQuestions[currentQuestionIndex];

  const [inputAnswer, setInputAnswer] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [repeatNotice, setRepeatNotice] = useState(false);
  const [networkError, setNetworkError] = useState(null);

  // Custom audio player hook
  const { isPlaying, isLoading: isAudioLoading, playAudio, stopAudio } = useAudioPlayer();

  // Custom speech recognition hook
  const {
    isListening,
    transcript,
    setTranscript,
    error: sttError,
    startListening,
    stopListening,
    isSupported: isSttSupported,
  } = useSpeechRecognition(language);

  // Sync transcription to text input
  useEffect(() => {
    if (transcript) {
      setInputAnswer(transcript);
    }
  }, [transcript]);

  // Auto-play TTS when question loads
  useEffect(() => {
    if (currentQuestion) {
      triggerTTS();
      setInputAnswer('');
      setRepeatNotice(false);
      setNetworkError(null);
    }
  }, [currentQuestionIndex]);

  const triggerTTS = () => {
    const ttsUrl = api.getTTSUrl(currentQuestion, language);
    playAudio(ttsUrl);
  };

  const handleSpeakClick = () => {
    stopAudio(); // Stop audio if it is currently playing before starting recording
    if (isListening) {
      stopListening();
    } else {
      startListening();
    }
  };

  const handleSubmit = async (e) => {
    if (e) e.preventDefault();
    if (!inputAnswer.trim() || isSubmitting) return;

    setIsSubmitting(true);
    setNetworkError(null);
    stopAudio();
    stopListening();

    try {
      const response = await api.submitAnswer(sessionId, currentQuestion, inputAnswer);
      
      if (response.action === 'Next') {
        setRepeatNotice(false);
        if (currentQuestionIndex + 1 < activeQuestions.length) {
          setCurrentQuestionIndex(prev => prev + 1);
        } else {
          // Completed all questions, trigger callback to summary page
          onComplete();
        }
      } else if (response.action === 'Complete') {
        setRepeatNotice(false);
        onComplete();
      } else {
        // Repeat logic
        setRepeatNotice(true);
        setInputAnswer('');
        setTranscript('');
        triggerTTS(); // Replay question audio
      }
    } catch (err) {
      console.error('Submit answer error:', err);
      setNetworkError('Server communication error. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const getProgressPercentage = () => {
    return ((currentQuestionIndex) / activeQuestions.length) * 100;
  };

  return (
    <div className="card glass-card fade-in">
      {/* Progress Header */}
      <div className="progress-section">
        <div className="progress-labels">
          <span className="progress-count text-light-gray">
            {language === 'English' && `Question ${currentQuestionIndex + 1} of ${activeQuestions.length}`}
            {language === 'Hindi' && `प्रश्न ${currentQuestionIndex + 1} / ${activeQuestions.length}`}
            {language === 'Marathi' && `प्रश्न ${currentQuestionIndex + 1} / ${activeQuestions.length}`}
          </span>
          <span className="progress-percent font-mono text-accent">
            {Math.round((currentQuestionIndex / activeQuestions.length) * 100)}%
          </span>
        </div>
        <div className="progress-bar-bg">
          <div className="progress-bar-fill" style={{ width: `${getProgressPercentage()}%` }}></div>
        </div>
      </div>

      {/* Main Question Display */}
      <div className="question-display-container text-center">
        <div className="question-heading-row">
          <button 
            className={`tts-speak-btn hover-glow ${isPlaying ? 'speaking' : ''}`}
            onClick={triggerTTS}
            title="Listen to question"
            disabled={isAudioLoading}
          >
            {isPlaying ? (
              <Volume2 className="pulse-icon text-accent" size={24} />
            ) : (
              <VolumeX className="text-light-gray" size={24} />
            )}
          </button>
          <span className="question-badge">
            {language === 'English' && "AI Physician"}
            {language === 'Hindi' && "एआई चिकित्सक"}
            {language === 'Marathi' && "एआय डॉक्टर"}
          </span>
        </div>

        <h2 className="question-text text-glow">
          {currentQuestion}
        </h2>
      </div>

      {/* Warning notices for repeating/unclear replies */}
      {repeatNotice && (
        <div className="alert-box alert-warning fade-in">
          <AlertTriangle size={20} className="alert-icon" />
          <div className="alert-content">
            <strong>
              {language === 'English' && "Answer unclear."}
              {language === 'Hindi' && "उत्तर स्पष्ट नहीं है।"}
              {language === 'Marathi' && "उत्तर स्पष्ट नाही."}
            </strong>
            <span>
              {language === 'English' && " Please rephrase or provide a clearer response (e.g. 'Yes', 'No', 'Since yesterday')."}
              {language === 'Hindi' && " कृपया सरल शब्दों में दोबारा बताएं (जैसे: 'हाँ', 'नहीं', 'कल से')।"}
              {language === 'Marathi' && " कृपया सोप्या शब्दांत सांगा (उदा: 'हो', 'नाही', 'कालपासून')."}
            </span>
          </div>
        </div>
      )}

      {sttError && (
        <div className="alert-box alert-error fade-in">
          <AlertTriangle size={20} className="alert-icon" />
          <div className="alert-content">
            <strong>Voice input issue:</strong>
            <span> {sttError}. You can type your answer in the box below instead.</span>
          </div>
        </div>
      )}

      {networkError && (
        <div className="alert-box alert-error fade-in">
          <AlertTriangle size={20} className="alert-icon" />
          <div className="alert-content">
            <strong>Connection issue:</strong>
            <span> {networkError}</span>
          </div>
        </div>
      )}

      {/* Voice and Text Input Area */}
      <form onSubmit={handleSubmit} className="input-section-form">
        <div className="voice-control-panel text-center">
          <button
            type="button"
            className={`btn-mic-trigger ${isListening ? 'listening shadow-glow-mic' : 'hover-glow'}`}
            onClick={handleSpeakClick}
            disabled={isSubmitting}
          >
            <Mic size={32} className="mic-svg" />
            <VoiceWaveform isActive={isListening} />
          </button>
          <div className="listening-label">
            {isListening ? (
              <span className="listening-pulse">● Recording... Speak now</span>
            ) : (
              <span className="text-light-gray">Click microphone and speak your answer</span>
            )}
          </div>
        </div>

        {/* Text modification / Fallback typing field */}
        <div className="answer-text-area-container">
          <label className="text-label text-light-gray">
            {language === 'English' && "Your Transcript (you can edit if needed):"}
            {language === 'Hindi' && "आपका उत्तर (यदि आवश्यक हो तो सुधारें):"}
            {language === 'Marathi' && "तुमचे उत्तर (आवश्यक असल्यास दुरुस्त करा):"}
          </label>
          <textarea
            className="answer-textarea"
            placeholder={
              language === 'English' ? "Speak or type your response here..." :
              language === 'Hindi' ? "यहाँ बोलें या लिखें..." : "येथे बोला किंवा लिहा..."
            }
            value={inputAnswer}
            onChange={(e) => setInputAnswer(e.target.value)}
            disabled={isSubmitting}
            rows={3}
          />
        </div>

        {/* Action Controls */}
        <div className="actions-row">
          <button
            type="submit"
            className="btn btn-primary btn-full hover-glow btn-submit-answer"
            disabled={!inputAnswer.trim() || isSubmitting}
          >
            {isSubmitting ? (
              <>
                <Loader2 size={18} className="spin-icon btn-icon-left" />
                <span>Evaluating...</span>
              </>
            ) : (
              <>
                <span>Submit Response</span>
                <Send size={18} className="btn-icon-right" />
              </>
            )}
          </button>
        </div>
      </form>

      {/* Non-supported Speech API alert */}
      {!isSttSupported && (
        <div className="stt-browser-notice">
          <HelpCircle size={14} className="notice-icon" />
          <span>Speech Recognition is best supported on Google Chrome desktop.</span>
        </div>
      )}
    </div>
  );
};
