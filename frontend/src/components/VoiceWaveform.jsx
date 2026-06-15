import React from 'react';

export const VoiceWaveform = ({ isActive }) => {
  if (!isActive) return null;

  return (
    <div className="voice-waveform-container">
      <div className="waveform-bar bar-1"></div>
      <div className="waveform-bar bar-2"></div>
      <div className="waveform-bar bar-3"></div>
      <div className="waveform-bar bar-4"></div>
      <div className="waveform-bar bar-5"></div>
      <div className="waveform-bar bar-6"></div>
      <div className="waveform-bar bar-7"></div>
      <div className="waveform-bar bar-8"></div>
    </div>
  );
};
