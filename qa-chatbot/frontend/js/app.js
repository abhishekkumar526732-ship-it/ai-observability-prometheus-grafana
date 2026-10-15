/**
 * ChatGPT-style Frontend Controller
 * 
 * Features:
 * - Exact ChatGPT UI behavior with Collapsible Sidebar, Model Pill, Floating Input Capsule
 * - Safe DOM manipulation using textContent & createElement (Zero innerHTML XSS injection)
 * - Safe syntax-highlighted code blocks with dark header and one-click copy button
 * - Real-time auto-resizing textarea with Enter to submit and Shift+Enter for newline
 * - Multi-turn conversation state preservation and dynamic chat history in sidebar
 * - Service readiness verification against /api/ready
 */

document.addEventListener('DOMContentLoaded', () => {
  // ----------------------------------------------------------------------------
  // State Initialization
  // ----------------------------------------------------------------------------
  const api = new window.ChatApiClient();
  let isSubmitting = false;
  let lastFailedMessage = '';
  const messageHistory = [];

  // ----------------------------------------------------------------------------
  // DOM Selectors
  // ----------------------------------------------------------------------------
  const sidebar = document.getElementById('sidebar');
  const openSidebarBtn = document.getElementById('open-sidebar-btn');
  const closeSidebarBtn = document.getElementById('close-sidebar-btn');
  const newChatBtn = document.getElementById('new-chat-btn');
  const headerNewChatBtn = document.getElementById('header-new-chat-btn');
  const currentChatItem = document.getElementById('current-chat-item');
  const historyTitle = document.getElementById('history-title');
  const activeModelDisplay = document.getElementById('active-model-display');
  const sidebarModelName = document.getElementById('sidebar-model-name');

  const statusDot = document.getElementById('status-dot');
  const statusLabel = document.getElementById('status-label');
  const sessionIdDisplay = document.getElementById('session-id-display');
  const copySessionBtn = document.getElementById('copy-session-btn');

  const errorBanner = document.getElementById('error-banner');
  const errorMessage = document.getElementById('error-message');
  const retryBtn = document.getElementById('retry-btn');
  const dismissErrorBtn = document.getElementById('dismiss-error-btn');

  const chatViewport = document.getElementById('chat-viewport');
  const welcomeScreen = document.getElementById('welcome-screen');
  const messagesList = document.getElementById('messages-list');
  const typingIndicator = document.getElementById('typing-indicator');
  const scrollAnchor = document.getElementById('scroll-anchor');

  const chatForm = document.getElementById('chat-form');
  const chatInput = document.getElementById('chat-input');
  const sendBtn = document.getElementById('send-btn');
  const sendIcon = document.getElementById('send-icon');
  const sendSpinner = document.getElementById('send-spinner');

  // ----------------------------------------------------------------------------
  // Sidebar Controls
  // ----------------------------------------------------------------------------
  if (openSidebarBtn && sidebar) {
    openSidebarBtn.addEventListener('click', () => {
      sidebar.classList.remove('collapsed');
    });
  }

  if (closeSidebarBtn && sidebar) {
    closeSidebarBtn.addEventListener('click', () => {
      sidebar.classList.add('collapsed');
    });
  }

  // ----------------------------------------------------------------------------
  // UI Helper Functions
  // ----------------------------------------------------------------------------
  function updateSessionIdUI() {
    const sid = api.sessionId;
    if (sid.length > 14) {
      sessionIdDisplay.textContent = `${sid.slice(0, 8)}...${sid.slice(-4)}`;
    } else {
      sessionIdDisplay.textContent = sid;
    }
    sessionIdDisplay.setAttribute('title', sid);
  }

  function setStatus(state, labelText) {
    statusDot.className = 'status-dot';
    if (state === 'ready') {
      statusDot.classList.add('status-ready');
    } else if (state === 'checking') {
      statusDot.classList.add('status-checking');
    } else {
      statusDot.classList.add('status-error');
    }
    statusLabel.textContent = labelText;
  }

  function showError(msg, allowRetry = false) {
    errorMessage.textContent = msg;
    if (allowRetry && lastFailedMessage) {
      retryBtn.classList.remove('hidden');
    } else {
      retryBtn.classList.add('hidden');
    }
    errorBanner.classList.remove('hidden');
    scrollToBottom();
  }

  function hideError() {
    errorBanner.classList.add('hidden');
    errorMessage.textContent = '';
  }

  function scrollToBottom() {
    requestAnimationFrame(() => {
      scrollAnchor.scrollIntoView({ behavior: 'smooth', block: 'end' });
    });
  }

  function setSubmittingState(submitting) {
    isSubmitting = submitting;
    chatInput.disabled = submitting;
    sendBtn.disabled = submitting || chatInput.value.trim().length === 0;

    if (submitting) {
      sendIcon.classList.add('hidden');
      sendSpinner.classList.remove('hidden');
      typingIndicator.classList.remove('hidden');
    } else {
      sendIcon.classList.remove('hidden');
      sendSpinner.classList.add('hidden');
      typingIndicator.classList.add('hidden');
      chatInput.focus();
    }
    scrollToBottom();
  }

  // ----------------------------------------------------------------------------
  // Safe DOM Message Rendering (No unsafe innerHTML)
  // ----------------------------------------------------------------------------

  /**
   * Safely append a user message (right-aligned light grey bubble).
   */
  function appendUserMessage(text) {
    welcomeScreen.classList.add('hidden');
    messagesList.classList.remove('hidden');

    const row = document.createElement('div');
    row.className = 'msg-row user-row';

    const bubble = document.createElement('div');
    bubble.className = 'user-bubble';

    const lines = text.split('\n');
    lines.forEach((line, index) => {
      bubble.appendChild(document.createTextNode(line));
      if (index < lines.length - 1) {
        bubble.appendChild(document.createElement('br'));
      }
    });

    row.appendChild(bubble);
    messagesList.appendChild(row);

    // Update sidebar title to user prompt on first message
    if (messageHistory.length === 0 && historyTitle) {
      const cleanTitle = text.length > 26 ? `${text.slice(0, 26)}...` : text;
      historyTitle.textContent = cleanTitle;
    }

    scrollToBottom();
  }

  /**
   * Safely append an assistant message with OpenAI avatar and parsed code blocks.
   */
  function appendAssistantMessage(rawText, modelName) {
    welcomeScreen.classList.add('hidden');
    messagesList.classList.remove('hidden');

    const row = document.createElement('div');
    row.className = 'msg-row assistant-row';

    // OpenAI circular avatar
    const avatar = document.createElement('div');
    avatar.className = 'assistant-avatar';
    avatar.setAttribute('aria-hidden', 'true');
    avatar.innerHTML = `
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="12" cy="12" r="9"/>
        <path d="M12 7v10M7 12h10"/>
      </svg>
    `;

    const body = document.createElement('div');
    body.className = 'assistant-body';

    // Decompose into safe paragraphs and syntax code blocks
    renderFormattedSafeText(body, rawText);

    // Bottom action row: Copy Response
    const actions = document.createElement('div');
    actions.className = 'msg-actions';

    const copyResponseBtn = document.createElement('button');
    copyResponseBtn.type = 'button';
    copyResponseBtn.className = 'msg-action-btn';
    copyResponseBtn.innerHTML = `
      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
        <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
      </svg>
      <span>Copy</span>
    `;

    copyResponseBtn.addEventListener('click', async () => {
      try {
        await navigator.clipboard.writeText(rawText);
        copyResponseBtn.querySelector('span').textContent = 'Copied!';
        setTimeout(() => {
          copyResponseBtn.querySelector('span').textContent = 'Copy';
        }, 2000);
      } catch (_) {
        // Fallback
      }
    });

    actions.appendChild(copyResponseBtn);
    body.appendChild(actions);

    row.appendChild(avatar);
    row.appendChild(body);
    messagesList.appendChild(row);

    messageHistory.push({ role: 'user', content: lastFailedMessage || '' });
    messageHistory.push({ role: 'assistant', content: rawText });

    scrollToBottom();
  }

  /**
   * Parse code blocks (```lang ... ```) and prose safely.
   */
  function renderFormattedSafeText(parentElem, text) {
    const codeBlockRegex = /```([a-zA-Z0-9_-]*)\n([\s\S]*?)```/g;
    let lastIndex = 0;
    let match;

    while ((match = codeBlockRegex.exec(text)) !== null) {
      const textBefore = text.substring(lastIndex, match.index);
      if (textBefore.trim()) {
        renderProseBlock(parentElem, textBefore);
      }

      const lang = match[1].trim() || 'code';
      const codeContent = match[2];
      renderCodeBlock(parentElem, lang, codeContent);

      lastIndex = match.index + match[0].length;
    }

    if (lastIndex < text.length) {
      const remainingText = text.substring(lastIndex);
      if (remainingText.trim()) {
        renderProseBlock(parentElem, remainingText);
      }
    }
  }

  function renderProseBlock(parentElem, text) {
    const paragraphs = text.split(/\n\s*\n/);

    paragraphs.forEach((paraText) => {
      const trimmed = paraText.trim();
      if (!trimmed) return;

      const p = document.createElement('p');
      const inlineCodeRegex = /`([^`]+)`/g;
      let lastIdx = 0;
      let match;

      while ((match = inlineCodeRegex.exec(trimmed)) !== null) {
        if (match.index > lastIdx) {
          p.appendChild(document.createTextNode(trimmed.substring(lastIdx, match.index)));
        }

        const codeNode = document.createElement('code');
        codeNode.textContent = match[1];
        p.appendChild(codeNode);

        lastIdx = match.index + match[0].length;
      }

      if (lastIdx < trimmed.length) {
        p.appendChild(document.createTextNode(trimmed.substring(lastIdx)));
      }

      parentElem.appendChild(p);
    });
  }

  function renderCodeBlock(parentElem, lang, code) {
    const blockWrapper = document.createElement('div');
    blockWrapper.className = 'code-container';

    const header = document.createElement('div');
    header.className = 'code-header-bar';

    const langSpan = document.createElement('span');
    langSpan.textContent = lang;

    const copyBtn = document.createElement('button');
    copyBtn.type = 'button';
    copyBtn.className = 'copy-btn';
    copyBtn.textContent = 'Copy code';

    copyBtn.addEventListener('click', async () => {
      try {
        await navigator.clipboard.writeText(code);
        copyBtn.textContent = 'Copied!';
        setTimeout(() => { copyBtn.textContent = 'Copy code'; }, 2000);
      } catch (_) {
        copyBtn.textContent = 'Failed';
      }
    });

    header.appendChild(langSpan);
    header.appendChild(copyBtn);

    const pre = document.createElement('pre');
    const codeElem = document.createElement('code');
    codeElem.textContent = code;
    pre.appendChild(codeElem);

    blockWrapper.appendChild(header);
    blockWrapper.appendChild(pre);

    parentElem.appendChild(blockWrapper);
  }

  // ----------------------------------------------------------------------------
  // Query Submission Handler
  // ----------------------------------------------------------------------------
  async function handleSubmitMessage(userPrompt) {
    const message = (userPrompt || chatInput.value).trim();
    if (!message || isSubmitting) return;

    hideError();
    lastFailedMessage = message;

    // Reset input
    chatInput.value = '';
    adjustTextareaHeight();
    updateSendButtonState();

    appendUserMessage(message);
    setSubmittingState(true);

    try {
      const response = await api.sendChatMessage(message, messageHistory);
      appendAssistantMessage(response.answer, response.model);
      lastFailedMessage = '';
    } catch (err) {
      console.error('Chat error:', err);
      let userFriendlyMsg = err.message || 'An error occurred while generating your answer.';

      if (err.status === 429) {
        userFriendlyMsg = 'AI rate limit exceeded. Please wait a moment and try again.';
      } else if (err.status === 504 || err.code === 'TIMEOUT') {
        userFriendlyMsg = 'The request timed out. Groq inference took too long to reply.';
      } else if (err.status === 422) {
        userFriendlyMsg = `Validation error: ${err.message}`;
      } else if (err.status === 502) {
        userFriendlyMsg = 'AI provider error. Verify your Groq API key in .env.';
      }

      showError(userFriendlyMsg, true);
    } finally {
      setSubmittingState(false);
    }
  }

  // ----------------------------------------------------------------------------
  // Textarea Controls & Keyboard Shortcuts
  // ----------------------------------------------------------------------------
  function adjustTextareaHeight() {
    chatInput.style.height = 'auto';
    const newHeight = Math.min(chatInput.scrollHeight, 160);
    chatInput.style.height = `${newHeight}px`;
  }

  function updateSendButtonState() {
    const len = chatInput.value.trim().length;
    sendBtn.disabled = isSubmitting || len === 0;
  }

  chatInput.addEventListener('input', () => {
    adjustTextareaHeight();
    updateSendButtonState();
  });

  chatInput.addEventListener('keydown', (e) => {
    // Enter without Shift submits; Shift+Enter creates a new line
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmitMessage();
    }
  });

  chatForm.addEventListener('submit', (e) => {
    e.preventDefault();
    handleSubmitMessage();
  });

  // ----------------------------------------------------------------------------
  // Quick Prompt Suggestion Chips
  // ----------------------------------------------------------------------------
  document.querySelectorAll('.suggestion-chip').forEach((chip) => {
    chip.addEventListener('click', () => {
      const prompt = chip.getAttribute('data-prompt');
      if (prompt) {
        handleSubmitMessage(prompt);
      }
    });
  });

  // ----------------------------------------------------------------------------
  // Reset Conversation ("New Chat")
  // ----------------------------------------------------------------------------
  function handleNewChat() {
    if (isSubmitting) return;

    const oldSessionId = api.sessionId;
    api.resetSession();
    updateSessionIdUI();

    messageHistory.length = 0;
    messagesList.innerHTML = '';
    messagesList.classList.add('hidden');
    welcomeScreen.classList.remove('hidden');
    hideError();
    lastFailedMessage = '';

    if (historyTitle) {
      historyTitle.textContent = 'New conversation';
    }

    chatInput.value = '';
    adjustTextareaHeight();
    updateSendButtonState();
    chatInput.focus();

    api.deleteSessionOnServer(oldSessionId);
  }

  if (newChatBtn) newChatBtn.addEventListener('click', handleNewChat);
  if (headerNewChatBtn) headerNewChatBtn.addEventListener('click', handleNewChat);

  if (copySessionBtn) {
    copySessionBtn.addEventListener('click', async () => {
      try {
        await navigator.clipboard.writeText(api.sessionId);
        copySessionBtn.setAttribute('title', 'Copied!');
        setTimeout(() => copySessionBtn.setAttribute('title', 'Copy Session ID'), 2000);
      } catch (_) {}
    });
  }

  // ----------------------------------------------------------------------------
  // Error Banner Controls
  // ----------------------------------------------------------------------------
  if (retryBtn) {
    retryBtn.addEventListener('click', () => {
      if (lastFailedMessage) {
        handleSubmitMessage(lastFailedMessage);
      }
    });
  }

  if (dismissErrorBtn) {
    dismissErrorBtn.addEventListener('click', hideError);
  }

  // ----------------------------------------------------------------------------
  // Service Readiness Initialization
  // ----------------------------------------------------------------------------
  async function performInitialCheck() {
    updateSessionIdUI();
    setStatus('checking', 'Connecting...');

    const readiness = await api.checkReadiness();
    if (readiness.ready) {
      setStatus('ready', 'Ready');
      if (activeModelDisplay && readiness.model) {
        activeModelDisplay.textContent = readiness.model;
      }
      if (sidebarModelName && readiness.model) {
        sidebarModelName.textContent = readiness.model;
      }
    } else {
      setStatus('error', 'Setup Needed');
      if (readiness.error) {
        showError(`Service notice: ${readiness.error}`);
      }
    }
  }

  performInitialCheck();
});
