import React from 'react';
import { Languages, Globe } from 'lucide-react';

export const LanguageSelection = ({ onSelect }) => {
  const options = [
    { name: 'English', native: 'English', code: 'EN', desc: 'Proceed with voice assessment in English' },
    { name: 'Hindi', native: 'हिन्दी', code: 'HI', desc: 'हिंदी में अपनी स्वास्थ्य जानकारी दर्ज करें' },
    { name: 'Marathi', native: 'मराठी', code: 'MR', desc: 'मराठीत आपली आरोग्य माहिती नोंदवा' },
  ];

  const handleLanguageSelect = (langName) => {
    sessionStorage.setItem('preferred_language', langName);
    onSelect(langName);
  };

  return (
    <div className="card glass-card fade-in text-center">
      <div className="logo-container">
        <Languages className="logo-svg text-accent" size={48} />
      </div>

      <h2 className="title-text card-heading">Select Language</h2>
      <p className="subtitle-text">
        Choose your preferred language for the voice consultation. You will be able to speak your answers in this language.
      </p>

      <div className="language-grid">
        {options.map((opt) => (
          <button
            key={opt.name}
            className="language-card hover-glow"
            onClick={() => handleLanguageSelect(opt.name)}
          >
            <div className="lang-code-badge">{opt.code}</div>
            <div className="lang-names">
              <span className="lang-native">{opt.native}</span>
              {opt.name !== opt.native && <span className="lang-english">({opt.name})</span>}
            </div>
            <p className="lang-desc">{opt.desc}</p>
          </button>
        ))}
      </div>

      <div className="footer-info">
        <Globe size={14} className="info-icon" />
        <span>Speech-to-text uses standard accents for the chosen region.</span>
      </div>
    </div>
  );
};
