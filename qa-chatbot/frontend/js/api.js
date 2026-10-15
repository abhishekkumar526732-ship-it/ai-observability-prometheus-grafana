/**
 * Q&A Chatbot API Client Module
 * 
 * Handles network requests to the FastAPI backend, session UUID generation,
 * timeout controls, and structured error normalization.
 */

class ChatApiClient {
  /**
   * @param {string} baseUrl - Base API endpoint prefix (defaults to relative '/api')
   */
  constructor(baseUrl = '/api') {
    this.baseUrl = baseUrl;
    this.sessionId = this.getOrCreateSessionId();
  }

  /**
   * Generate a standards-compliant UUID v4 session identifier.
   * Uses crypto.randomUUID() when available, with a cryptographically secure fallback.
   * @returns {string} UUID v4 string
   */
  getOrCreateSessionId() {
    if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
      return crypto.randomUUID();
    }
    // Fallback RFC4122 v4 generator using crypto.getRandomValues
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
      const r = (crypto.getRandomValues(new Uint8Array(1))[0] % 16) | 0;
      const v = c === 'x' ? r : (r & 0x3) | 0x8;
      return v.toString(16);
    });
  }

  /**
   * Reset session identifier for "New Chat" functionality.
   * @returns {string} Newly generated session ID
   */
  resetSession() {
    this.sessionId = this.getOrCreateSessionId();
    return this.sessionId;
  }

  /**
   * Check backend readiness without calling Groq API.
   * @returns {Promise<{ready: boolean, model: string, error?: string}>}
   */
  async checkReadiness() {
    try {
      const response = await fetch(`${this.baseUrl}/ready`, {
        method: 'GET',
        headers: { 'Accept': 'application/json' },
      });

      if (response.ok) {
        const data = await response.json();
        return { ready: data.status === 'ready', model: data.model || 'Unknown' };
      } else {
        const errData = await response.json().catch(() => ({}));
        return {
          ready: false,
          model: errData.model || 'Unset',
          error: errData.detail || `Readiness check returned status ${response.status}`,
        };
      }
    } catch (err) {
      return {
        ready: false,
        model: 'Unreachable',
        error: 'Unable to connect to the backend service. Check network or container status.',
      };
    }
  }

  /**
   * Submit a user query to POST /api/chat.
   * @param {string} message - Sanitized user input question
   * @param {Array<{role: string, content: string}>} [history=[]] - Optional client history
   * @returns {Promise<{session_id: string, answer: string, model: string}>}
   */
  async sendChatMessage(message, history = []) {
    const payload = {
      session_id: this.sessionId,
      message: message.trim(),
      history: history,
    };

    // 70-second client-side timeout (backend configured for 60s timeout)
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 70000);

    try {
      const response = await fetch(`${this.baseUrl}/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
        body: JSON.stringify(payload),
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      // Handle successful generation
      if (response.ok) {
        return await response.json();
      }

      // Handle structured API error responses
      let errorBody = {};
      try {
        errorBody = await response.json();
      } catch (_) {
        errorBody = { detail: response.statusText };
      }

      const errorMessage = errorBody.detail || `Server responded with status ${response.status}`;
      const errorObj = new Error(errorMessage);
      errorObj.status = response.status;
      errorObj.code = errorBody.code || `HTTP_${response.status}`;
      errorObj.type = errorBody.error || 'SERVER_ERROR';
      throw errorObj;

    } catch (err) {
      clearTimeout(timeoutId);

      if (err.name === 'AbortError') {
        const timeoutError = new Error('The request timed out while waiting for the AI response. Please try again.');
        timeoutError.status = 504;
        timeoutError.code = 'TIMEOUT';
        throw timeoutError;
      }

      // Re-throw already processed API errors
      if (err.status) {
        throw err;
      }

      // Network or fetch connection failure
      const netErr = new Error('Failed to communicate with backend server. Verify your connection or container status.');
      netErr.status = 0;
      netErr.code = 'NETWORK_ERROR';
      throw netErr;
    }
  }

  /**
   * Optional helper to inform backend of session termination.
   * @param {string} sessionId
   * @returns {Promise<void>}
   */
  async deleteSessionOnServer(sessionId) {
    if (!sessionId) return;
    try {
      await fetch(`${this.baseUrl}/chat/session/${sessionId}`, {
        method: 'DELETE',
      });
    } catch (_) {
      // Fire-and-forget; do not block user
    }
  }
}

// Attach to window for global access
window.ChatApiClient = ChatApiClient;
