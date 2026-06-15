import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const api = {
  // Start a new history-taking session
  startSession: async (language) => {
    const response = await apiClient.post('/api/start-session', { language });
    return response.data;
  },

  // Submit the patient's spoken/text answer
  submitAnswer: async (sessionId, question, answer) => {
    const response = await apiClient.post('/api/submit-answer', {
      sessionId,
      question,
      answer,
    });
    return response.data;
  },

  // Generate multilingual summaries after 5 questions
  generateSummary: async (sessionId) => {
    const response = await apiClient.post('/api/generate-summary', { sessionId });
    return response.data;
  },

  // Fetch full details of a session
  getSession: async (sessionId) => {
    const response = await apiClient.get(`/api/session/${sessionId}`);
    return response.data;
  },

  // Helper to construct URL for Text-To-Speech audio source
  getTTSUrl: (text, language) => {
    return `${API_BASE_URL}/api/tts?text=${encodeURIComponent(text)}&lang=${encodeURIComponent(language)}`;
  },
};
