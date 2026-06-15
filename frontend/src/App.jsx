import React, { useState, useEffect } from 'react';
import { StartScreen } from './components/StartScreen';
import { LanguageSelection } from './components/LanguageSelection';
import { AssessmentFlow } from './components/AssessmentFlow';
import { SummaryScreen } from './components/SummaryScreen';
import { api } from './services/api';
import { Stethoscope, Loader2 } from 'lucide-react';
import './index.css';

// Screen states
const SCREENS = {
  START: 'START',
  LANGUAGE_SELECT: 'LANGUAGE_SELECT',
  ASSESSMENT: 'ASSESSMENT',
  SUMMARY: 'SUMMARY',
};

function App() {
  const [screen, setScreen] = useState(SCREENS.START);
  const [language, setLanguage] = useState('');
  const [sessionId, setSessionId] = useState('');
  const [loadingSession, setLoadingSession] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  // Persist language on reload if desired, or read from sessionStorage on load
  useEffect(() => {
    const cachedLanguage = sessionStorage.getItem('preferred_language');
    const cachedSessionId = sessionStorage.getItem('active_session_id');
    const cachedScreen = sessionStorage.getItem('current_screen');

    if (cachedLanguage) {
      setLanguage(cachedLanguage);
    }
    if (cachedSessionId) {
      setSessionId(cachedSessionId);
    }
    if (cachedScreen) {
      setScreen(cachedScreen);
    }
  }, []);

  const navigateTo = (nextScreen) => {
    setScreen(nextScreen);
    sessionStorage.setItem('current_screen', nextScreen);
  };

  const handleStart = () => {
    navigateTo(SCREENS.LANGUAGE_SELECT);
  };

  const handleLanguageSelect = async (selectedLang) => {
    setLanguage(selectedLang);
    setLoadingSession(true);
    setErrorMsg('');

    try {
      // Create session in the database
      const result = await api.startSession(selectedLang);
      
      setSessionId(result.sessionId);
      sessionStorage.setItem('active_session_id', result.sessionId);
      
      navigateTo(SCREENS.ASSESSMENT);
    } catch (err) {
      console.error('Failed to initialize session:', err);
      setErrorMsg('Could not connect to medical backend. Please check if server is running.');
    } finally {
      setLoadingSession(false);
    }
  };

  const handleAssessmentComplete = () => {
    navigateTo(SCREENS.SUMMARY);
  };

  const handleReset = () => {
    setLanguage('');
    setSessionId('');
    setErrorMsg('');
    sessionStorage.clear();
    navigateTo(SCREENS.START);
  };

  return (
    <div className="app-container">
      {/* Top Navbar */}
      <header className="navbar glass-nav">
        <div className="navbar-logo-row" onClick={handleReset} style={{ cursor: 'pointer' }}>
          <Stethoscope className="nav-logo-icon text-accent" size={24} />
          <span className="navbar-title">
            OPD <span className="text-accent">Intelligence</span>
          </span>
        </div>
        {language && (
          <div className="nav-lang-badge">
            <span className="badge-dot"></span>
            <span>Language: {language}</span>
          </div>
        )}
      </header>

      {/* Main Content Area */}
      <main className="main-content">
        {loadingSession ? (
          <div className="card glass-card text-center loader-padding">
            <Loader2 className="spin-icon text-accent logo-svg" size={48} />
            <h3 className="title-text">Initializing Secure Session...</h3>
            <p className="subtitle-text">Setting up patient intake configuration and voice parameters...</p>
          </div>
        ) : (
          <>
            {errorMsg && (
              <div className="card glass-card text-center margin-bottom">
                <p className="text-error font-medium">{errorMsg}</p>
                <button className="btn btn-secondary btn-center margin-top-sm" onClick={handleReset}>
                  Back to Start
                </button>
              </div>
            )}

            {!errorMsg && screen === SCREENS.START && (
              <StartScreen onStart={handleStart} />
            )}

            {!errorMsg && screen === SCREENS.LANGUAGE_SELECT && (
              <LanguageSelection onSelect={handleLanguageSelect} />
            )}

            {!errorMsg && screen === SCREENS.ASSESSMENT && (
              <AssessmentFlow
                sessionId={sessionId}
                language={language}
                onComplete={handleAssessmentComplete}
              />
            )}

            {!errorMsg && screen === SCREENS.SUMMARY && (
              <SummaryScreen
                sessionId={sessionId}
                patientLanguage={language}
                onReset={handleReset}
              />
            )}
          </>
        )}
      </main>

      {/* Footer */}
      <footer className="app-footer">
        <p>© 2026 OPD Intelligence Medical System v2.0 | Built with Gemini & Web Speech API</p>
      </footer>
    </div>
  );
}

export default App;
