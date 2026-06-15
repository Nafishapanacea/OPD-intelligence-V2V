import React, { useState, useEffect } from 'react';
import { FileText, ChevronDown, CheckCircle2, RotateCcw, ListCollapse, User, Calendar } from 'lucide-react';
import { api } from '../services/api';

export const SummaryScreen = ({ sessionId, patientLanguage, onReset }) => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [summaries, setSummaries] = useState(null);
  const [history, setHistory] = useState([]);
  const [selectedLang, setSelectedLang] = useState(patientLanguage); // Default to patient's choice
  const [createdAt, setCreatedAt] = useState(null);

  useEffect(() => {
    const fetchSummaryAndHistory = async () => {
      try {
        setLoading(true);
        setError(null);

        // 1. Generate/Fetch summaries
        const summaryResult = await api.generateSummary(sessionId);
        setSummaries(summaryResult);

        // 2. Fetch full session details (to show raw interactions & date)
        const sessionDetails = await api.getSession(sessionId);
        setHistory(sessionDetails.interactions || []);
        if (sessionDetails.created_at) {
          setCreatedAt(new Date(sessionDetails.created_at).toLocaleString());
        }
      } catch (err) {
        console.error('Failed to generate summary:', err);
        setError('Could not generate medical summaries. Please contact support.');
      } finally {
        setLoading(false);
      }
    };

    if (sessionId) {
      fetchSummaryAndHistory();
    }
  }, [sessionId]);

  const getDisplayedSummary = () => {
    if (!summaries) return '';
    switch (selectedLang) {
      case 'Hindi':
        return summaries.hindi_summary;
      case 'Marathi':
        return summaries.marathi_summary;
      case 'English':
      default:
        return summaries.english_summary;
    }
  };

  if (loading) {
    return (
      <div className="card glass-card fade-in text-center loader-padding">
        <div className="loading-spinner-container">
          <div className="pulse-circle"></div>
          <FileText className="spinner-icon text-accent" size={32} />
        </div>
        <h3 className="title-text min-margin">Synthesizing Medical History...</h3>
        <p className="subtitle-text">
          Gemini is analyzing the patient's voice responses to generate formatted medical summaries in English, Hindi, and Marathi.
        </p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="card glass-card fade-in text-center">
        <div className="logo-container bg-error-light">
          <RotateCcw className="logo-svg text-error" size={48} />
        </div>
        <h2 className="title-text text-error">Synthesis Failed</h2>
        <p className="subtitle-text">{error}</p>
        <button className="btn btn-secondary hover-glow btn-center" onClick={onReset}>
          <RotateCcw size={18} className="btn-icon-left" />
          <span>Restart Assessment</span>
        </button>
      </div>
    );
  }

  return (
    <div className="card glass-card fade-in">
      {/* Summary Completed Header */}
      <div className="summary-success-header text-center">
        <CheckCircle2 size={48} className="text-success pulse-icon" />
        <h2 className="title-text compact-title">Assessment Complete</h2>
        <p className="subtitle-text minimal-margin">
          Pre-consultation history has been compiled and summarized successfully.
        </p>
      </div>

      {/* Session Metadata Info */}
      <div className="session-meta-grid">
        <div className="meta-box">
          <User size={14} className="meta-icon" />
          <span>ID: <code className="font-mono text-accent">{sessionId.substring(0, 8)}...</code></span>
        </div>
        <div className="meta-box">
          <Calendar size={14} className="meta-icon" />
          <span>{createdAt || 'Just now'}</span>
        </div>
      </div>

      {/* Language Selector Dropdown for Summaries */}
      <div className="summary-selector-row">
        <label htmlFor="summary-lang-select" className="selector-label text-light-gray">
          Display Summary Language:
        </label>
        <div className="custom-select-wrapper">
          <select
            id="summary-lang-select"
            className="dropdown-select hover-glow"
            value={selectedLang}
            onChange={(e) => setSelectedLang(e.target.value)}
          >
            <option value="English">English Summary</option>
            <option value="Hindi">Hindi Summary (हिन्दी)</option>
            <option value="Marathi">Marathi Summary (मराठी)</option>
          </select>
          <ChevronDown size={18} className="select-arrow-icon" />
        </div>
      </div>

      {/* Clinical Summary Markdown Container */}
      <div className="clinical-summary-box shadow-glow">
        <div className="summary-box-header">
          <FileText size={18} className="text-accent" />
          <span className="summary-box-title">CLINICAL PRE-CONSULTATION SUMMARY</span>
        </div>
        <div className="summary-box-body">
          {getDisplayedSummary().split('\n').map((line, idx) => (
            <p key={idx} className="summary-line">
              {line}
            </p>
          ))}
        </div>
      </div>

      {/* Raw Interaction History Logs Accordion */}
      <div className="raw-history-section">
        <div className="raw-history-header">
          <ListCollapse size={18} className="text-light-gray" />
          <h3 className="section-subtitle">Intake Conversation Log ({patientLanguage})</h3>
        </div>
        <div className="raw-history-list">
          {history.map((item, idx) => (
            <div key={item.id || idx} className="history-chat-bubble">
              <div className="chat-item question-bubble">
                <span className="chat-role text-accent">Q:</span>
                <p className="chat-text">{item.question}</p>
              </div>
              <div className="chat-item answer-bubble">
                <span className="chat-role text-success">A:</span>
                <p className="chat-text font-italic">{item.answer}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Bottom Actions */}
      <div className="actions-footer">
        <button className="btn btn-secondary btn-full hover-glow" onClick={onReset}>
          <RotateCcw size={18} className="btn-icon-left" />
          <span>New Assessment</span>
        </button>
      </div>
    </div>
  );
};
