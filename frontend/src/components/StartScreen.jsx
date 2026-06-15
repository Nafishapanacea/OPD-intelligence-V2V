import React from 'react';
import { Activity, ShieldAlert, ArrowRight } from 'lucide-react';

export const StartScreen = ({ onStart }) => {
  return (
    <div className="card glass-card fade-in text-center">
      <div className="logo-container">
        <Activity className="pulse-icon logo-svg" size={64} />
      </div>
      
      <h1 className="title-text">OPD Pre-Consultation Assistant</h1>
      
      <p className="subtitle-text">
        Welcome to the digital intake portal. This smart system will collect your medical history 
        via voice interactions before you meet your doctor, ensuring an efficient and detailed consultation.
      </p>

      <div className="feature-bullets">
        <div className="bullet-item">
          <span className="bullet-bullet">🔊</span>
          <p><strong>Voice Guided:</strong> The system reads out questions in your chosen language.</p>
        </div>
        <div className="bullet-item">
          <span className="bullet-bullet">🎤</span>
          <p><strong>Speech Input:</strong> Respond naturally by speaking into your microphone.</p>
        </div>
        <div className="bullet-item">
          <span className="bullet-bullet">🤖</span>
          <p><strong>Intelligent Verification:</strong> Powered by Gemini to ensure clear symptoms capture.</p>
        </div>
      </div>

      <div className="privacy-badge">
        <ShieldAlert size={16} className="text-accent" />
        <span>Your data is strictly confidential and stored securely.</span>
      </div>

      <button className="btn btn-primary btn-large btn-glow" onClick={onStart}>
        <span>Start Pre-Consultation Assessment</span>
        <ArrowRight size={20} className="btn-icon-right" />
      </button>
    </div>
  );
};
