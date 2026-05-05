/**
 * Internal Chatbot Widget
 * A self-contained Vanilla JS chat widget for embedding on websites.
 * 
 * Usage:
 * <script src="widget.js" data-api-url="https://api.example.com" data-chatbot-id="abc123"></script>
 */
(function() {
  'use strict';

  // ============================================
  // CONFIGURATION & DEFAULTS
  // ============================================
  
  const DEFAULT_CONFIG = {
    apiUrl: '',
    chatbotId: '',
    position: 'right', // 'left' or 'right'
    theme: 'dark',
    offset: { bottom: 20, right: 20 },
    sessionExpiry: 24 * 60 * 60 * 1000, // 24 hours in milliseconds
    localStorageKey: 'chatbot_session_id'
  };

  // ============================================
  // STYLES (injected dynamically)
  // ============================================
  
  const STYLES = `
    .chatbot-widget * {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
    }

    .chatbot-widget {
      --cb-primary: #1a1a1a;
      --cb-secondary: #2d2d2d;
      --cb-border: #3d3d3d;
      --cb-text: #e5e5e5;
      --cb-text-muted: #888;
      --cb-accent: #4f46e5;
      --cb-accent-hover: #4338ca;
      --cb-radius: 12px;
      --cb-shadow: 0 10px 40px rgba(0, 0, 0, 0.3);
      
      position: fixed;
      z-index: 999999;
      font-size: 14px;
      line-height: 1.5;
    }

    .chatbot-widget.position-right {
      bottom: var(--cb-offset-bottom, 20px);
      right: var(--cb-offset-right, 20px);
    }

    .chatbot-widget.position-left {
      bottom: var(--cb-offset-bottom, 20px);
      left: var(--cb-offset-left, 20px);
    }

    /* Toggle Button */
    .chatbot-toggle {
      width: 60px;
      height: 60px;
      border-radius: 50%;
      background: var(--cb-accent);
      border: none;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      box-shadow: var(--cb-shadow);
      transition: transform 0.2s ease, background 0.2s ease;
      position: absolute;
      bottom: 0;
      right: 0;
    }

    .chatbot-toggle:hover {
      transform: scale(1.05);
      background: var(--cb-accent-hover);
    }

    .chatbot-toggle:focus {
      outline: 2px solid var(--cb-text);
      outline-offset: 2px;
    }

    .chatbot-toggle svg {
      width: 28px;
      height: 28px;
      fill: white;
      transition: transform 0.3s ease;
    }

    .chatbot-toggle.collapsed svg {
      transform: rotate(180deg);
    }

    /* Chat Container */
    .chatbot-container {
      position: absolute;
      bottom: 70px;
      width: 380px;
      max-width: calc(100vw - 40px);
      height: 500px;
      max-height: calc(100vh - 120px);
      background: var(--cb-primary);
      border-radius: var(--cb-radius);
      box-shadow: var(--cb-shadow);
      display: flex;
      flex-direction: column;
      overflow: hidden;
      transition: opacity 0.3s ease, transform 0.3s ease;
      border: 1px solid var(--cb-border);
    }

    .chatbot-widget.position-right .chatbot-container {
      right: 0;
    }

    .chatbot-widget.position-left .chatbot-container {
      left: 0;
    }

    .chatbot-container.hidden {
      opacity: 0;
      pointer-events: none;
      transform: translateY(20px);
    }

    .chatbot-container.collapsed {
      display: none;
    }

    /* Header */
    .chatbot-header {
      background: var(--cb-secondary);
      padding: 16px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      border-bottom: 1px solid var(--cb-border);
    }

    .chatbot-header-info {
      display: flex;
      align-items: center;
      gap: 12px;
    }

    .chatbot-avatar {
      width: 40px;
      height: 40px;
      border-radius: 50%;
      background: var(--cb-accent);
      display: flex;
      align-items: center;
      justify-content: center;
    }

    .chatbot-avatar svg {
      width: 24px;
      height: 24px;
      fill: white;
    }

    .chatbot-header-text h3 {
      color: var(--cb-text);
      font-size: 15px;
      font-weight: 600;
      margin-bottom: 2px;
    }

    .chatbot-header-text span {
      color: var(--cb-text-muted);
      font-size: 12px;
    }

    .chatbot-close {
      width: 32px;
      height: 32px;
      border-radius: 50%;
      background: transparent;
      border: none;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      transition: background 0.2s ease;
    }

    .chatbot-close:hover {
      background: var(--cb-border);
    }

    .chatbot-close:focus {
      outline: 2px solid var(--cb-accent);
      outline-offset: 2px;
    }

    .chatbot-close svg {
      width: 20px;
      height: 20px;
      fill: var(--cb-text-muted);
    }

    /* Messages Area */
    .chatbot-messages {
      flex: 1;
      overflow-y: auto;
      padding: 16px;
      display: flex;
      flex-direction: column;
      gap: 12px;
      scroll-behavior: smooth;
    }

    .chatbot-messages::-webkit-scrollbar {
      width: 6px;
    }

    .chatbot-messages::-webkit-scrollbar-track {
      background: var(--cb-primary);
    }

    .chatbot-messages::-webkit-scrollbar-thumb {
      background: var(--cb-border);
      border-radius: 3px;
    }

    .chatbot-messages::-webkit-scrollbar-thumb:hover {
      background: var(--cb-text-muted);
    }

    /* Message Bubbles */
    .chatbot-message {
      max-width: 80%;
      padding: 10px 14px;
      border-radius: 16px;
      word-wrap: break-word;
      white-space: pre-wrap;
    }

    .chatbot-message.user {
      background: var(--cb-accent);
      color: white;
      align-self: flex-end;
      border-bottom-right-radius: 4px;
      margin-left: auto;
    }

    .chatbot-message.bot {
      background: var(--cb-secondary);
      color: var(--cb-text);
      align-self: flex-start;
      border-bottom-left-radius: 4px;
      border: 1px solid var(--cb-border);
    }

    .chatbot-message.error {
      background: rgba(239, 68, 68, 0.1);
      color: #ef4444;
      border: 1px solid rgba(239, 68, 68, 0.3);
    }

    /* Typing Indicator */
    .chatbot-typing {
      display: flex;
      align-items: center;
      gap: 4px;
      padding: 10px 14px;
      background: var(--cb-secondary);
      border-radius: 16px;
      border-bottom-left-radius: 4px;
      align-self: flex-start;
      border: 1px solid var(--cb-border);
    }

    .chatbot-typing span {
      width: 8px;
      height: 8px;
      background: var(--cb-text-muted);
      border-radius: 50%;
      animation: chatbot-typing-bounce 1.4s infinite ease-in-out both;
    }

    .chatbot-typing span:nth-child(1) { animation-delay: -0.32s; }
    .chatbot-typing span:nth-child(2) { animation-delay: -0.16s; }
    .chatbot-typing span:nth-child(3) { animation-delay: 0s; }

    @keyframes chatbot-typing-bounce {
      0%, 80%, 100% { transform: scale(0.6); opacity: 0.4; }
      40% { transform: scale(1); opacity: 1; }
    }

    /* Input Area */
    .chatbot-input-area {
      padding: 12px 16px;
      background: var(--cb-secondary);
      border-top: 1px solid var(--cb-border);
      display: flex;
      gap: 8px;
    }

    .chatbot-input {
      flex: 1;
      background: var(--cb-primary);
      border: 1px solid var(--cb-border);
      border-radius: 24px;
      padding: 10px 16px;
      color: var(--cb-text);
      font-size: 14px;
      resize: none;
      outline: none;
      transition: border-color 0.2s ease;
    }

    .chatbot-input::placeholder {
      color: var(--cb-text-muted);
    }

    .chatbot-input:focus {
      border-color: var(--cb-accent);
    }

    .chatbot-send {
      width: 44px;
      height: 44px;
      border-radius: 50%;
      background: var(--cb-accent);
      border: none;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      transition: background 0.2s ease, transform 0.2s ease;
      flex-shrink: 0;
    }

    .chatbot-send:hover {
      background: var(--cb-accent-hover);
      transform: scale(1.05);
    }

    .chatbot-send:focus {
      outline: 2px solid var(--cb-text);
      outline-offset: 2px;
    }

    .chatbot-send:disabled {
      background: var(--cb-border);
      cursor: not-allowed;
      transform: none;
    }

    .chatbot-send svg {
      width: 20px;
      height: 20px;
      fill: white;
      margin-left: 2px;
    }

    /* Welcome Message */
    .chatbot-welcome {
      text-align: center;
      padding: 20px;
      color: var(--cb-text-muted);
    }

    .chatbot-welcome-icon {
      width: 48px;
      height: 48px;
      margin: 0 auto 12px;
      background: var(--cb-secondary);
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      border: 1px solid var(--cb-border);
    }

    .chatbot-welcome-icon svg {
      width: 24px;
      height: 24px;
      fill: var(--cb-text-muted);
    }

    .chatbot-welcome p {
      font-size: 13px;
    }
  `;

  // ============================================
  // SVG ICONS
  // ============================================
  
  const ICONS = {
    chat: `<svg viewBox="0 0 24 24"><path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm0 14H6l-2 2V4h16v12z"/></svg>`,
    close: `<svg viewBox="0 0 24 24"><path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/></svg>`,
    send: `<svg viewBox="0 0 24 24"><path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/></svg>`,
    bot: `<svg viewBox="0 0 24 24"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/></svg>`
  };

  // ============================================
  // SESSION MANAGEMENT
  // ============================================
  
  class SessionManager {
    constructor(config) {
      this.config = config;
    }

    generateSessionId() {
      return 'sess_' + Date.now().toString(36) + '_' + Math.random().toString(36).substr(2, 9);
    }

    createSession() {
      const session = {
        id: this.generateSessionId(),
        userId: null,
        created: Date.now(),
        expires: Date.now() + this.config.sessionExpiry,
        history: []
      };
      this.saveSession(session);
      return session;
    }

    getSession() {
      try {
        const stored = localStorage.getItem(this.config.localStorageKey);
        if (!stored) return null;

        const session = JSON.parse(stored);
        
        // Check if expired
        if (Date.now() > session.expires) {
          this.clearSession();
          return null;
        }

        return session;
      } catch (e) {
        console.error('[Chatbot] Error reading session:', e);
        return null;
      }
    }

    saveSession(session) {
      try {
        localStorage.setItem(this.config.localStorageKey, JSON.stringify(session));
      } catch (e) {
        console.error('[Chatbot] Error saving session:', e);
      }
    }

    clearSession() {
      try {
        localStorage.removeItem(this.config.localStorageKey);
      } catch (e) {
        console.error('[Chatbot] Error clearing session:', e);
      }
    }

    updateSession(updates) {
      const session = this.getSession() || this.createSession();
      Object.assign(session, updates);
      this.saveSession(session);
      return session;
    }

    ensureSession() {
      let session = this.getSession();
      if (!session) {
        session = this.createSession();
      }
      return session;
    }
  }

  // ============================================
  // CHAT WIDGET CLASS
  // ============================================
  
  class ChatWidget {
    constructor(config) {
      this.config = { ...DEFAULT_CONFIG, ...config };
      this.sessionManager = new SessionManager(this.config);
      this.session = null;
      this.isOpen = false;
      this.isLoading = false;
      this.events = {};

      this.init();
    }

    init() {
      // Inject styles
      this.injectStyles();

      // Create DOM structure
      this.createDOM();

      // Ensure session exists
      this.session = this.sessionManager.ensureSession();

      // Render existing history
      this.renderMessages();

      // Bind events
      this.bindEvents();

      // Setup public API
      this.setupPublicAPI();

      // Fire session create event
      this.emit('sessionCreate', this.session);
    }

    injectStyles() {
      if (document.getElementById('chatbot-styles')) return;
      
      const style = document.createElement('style');
      style.id = 'chatbot-styles';
      style.textContent = STYLES;
      document.head.appendChild(style);
    }

    createDOM() {
      // Main container
      this.widget = document.createElement('div');
      this.widget.className = `chatbot-widget position-${this.config.position}`;
      this.widget.style.setProperty('--cb-offset-bottom', `${this.config.offset.bottom}px`);
      this.widget.style.setProperty('--cb-offset-right', `${this.config.offset.right}px`);
      this.widget.style.setProperty('--cb-offset-left', `${this.config.offset.left}px`);

      // Toggle button
      this.toggleBtn = document.createElement('button');
      this.toggleBtn.className = 'chatbot-toggle collapsed';
      this.toggleBtn.setAttribute('aria-label', 'Open chat');
      this.toggleBtn.innerHTML = ICONS.chat;

      // Chat container
      this.container = document.createElement('div');
      this.container.className = 'chatbot-container hidden collapsed';

      // Header
      this.header = document.createElement('div');
      this.header.className = 'chatbot-header';
      this.header.innerHTML = `
        <div class="chatbot-header-info">
          <div class="chatbot-avatar">${ICONS.bot}</div>
          <div class="chatbot-header-text">
            <h3>Chat Assistant</h3>
            <span>Online</span>
          </div>
        </div>
        <button class="chatbot-close" aria-label="Minimize chat">${ICONS.close}</button>
      `;

      // Messages area
      this.messagesArea = document.createElement('div');
      this.messagesArea.className = 'chatbot-messages';

      // Input area
      this.inputArea = document.createElement('div');
      this.inputArea.className = 'chatbot-input-area';
      this.inputArea.innerHTML = `
        <input type="text" class="chatbot-input" placeholder="Type a message..." aria-label="Message input">
        <button class="chatbot-send" aria-label="Send message" disabled>${ICONS.send}</button>
      `;

      // Assemble
      this.container.appendChild(this.header);
      this.container.appendChild(this.messagesArea);
      this.container.appendChild(this.inputArea);
      this.widget.appendChild(this.container);
      this.widget.appendChild(this.toggleBtn);
      document.body.appendChild(this.widget);

      // Cache DOM references
      this.input = this.inputArea.querySelector('.chatbot-input');
      this.sendBtn = this.inputArea.querySelector('.chatbot-send');
      this.closeBtn = this.header.querySelector('.chatbot-close');
    }

    bindEvents() {
      // Toggle button
      this.toggleBtn.addEventListener('click', () => this.toggle());

      // Close button
      this.closeBtn.addEventListener('click', () => this.close());

      // Input events
      this.input.addEventListener('input', () => {
        this.sendBtn.disabled = !this.input.value.trim();
      });

      this.input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
          e.preventDefault();
          this.sendMessage();
        }
      });

      // Send button
      this.sendBtn.addEventListener('click', () => this.sendMessage());
    }

    setupPublicAPI() {
      window.Chatbot = {
        open: () => this.open(),
        close: () => this.close(),
        toggle: () => this.toggle(),
        clearHistory: () => this.clearHistory(),
        sendMessage: (text) => this.sendMessage(text),
        on: (event, callback) => this.on(event, callback),
        getSession: () => this.session,
        config: this.config
      };
    }

    // ============================================
    // PUBLIC API
    // ============================================

    on(event, callback) {
      if (!this.events[event]) {
        this.events[event] = [];
      }
      this.events[event].push(callback);
    }

    emit(event, data) {
      if (this.events[event]) {
        this.events[event].forEach(callback => {
          try {
            callback(data);
          } catch (e) {
            console.error(`[Chatbot] Error in ${event} callback:`, e);
          }
        });
      }
    }

    open() {
      this.isOpen = true;
      this.container.classList.remove('hidden', 'collapsed');
      this.toggleBtn.classList.remove('collapsed');
      this.toggleBtn.setAttribute('aria-label', 'Close chat');
      this.input.focus();
    }

    close() {
      this.isOpen = false;
      this.container.classList.add('hidden');
      this.container.classList.add('collapsed');
      this.toggleBtn.classList.add('collapsed');
      this.toggleBtn.setAttribute('aria-label', 'Open chat');
    }

    toggle() {
      if (this.isOpen) {
        this.close();
      } else {
        this.open();
      }
    }

    clearHistory() {
      this.session = this.sessionManager.updateSession({ history: [] });
      this.messagesArea.innerHTML = '';
      this.renderWelcome();
    }

    // ============================================
    // MESSAGE HANDLING
    // ============================================

    async sendMessage(text) {
      const messageText = text || this.input.value.trim();
      if (!messageText || this.isLoading) return;

      // Clear input
      this.input.value = '';
      this.sendBtn.disabled = true;

      // Add user message
      this.addMessage(messageText, 'user');

      // Save to history
      this.saveMessage(messageText, 'user');

      // Emit event
      this.emit('message', { text: messageText, role: 'user' });

      // Show typing indicator
      this.showTyping();

      try {
        const response = await this.apiChat(messageText);
        this.hideTyping();
        
        if (response.error) {
          this.addMessage(response.error, 'bot', 'error');
        } else {
          this.addMessage(response.answer, 'bot');
          this.saveMessage(response.answer, 'bot');
          this.emit('message', { text: response.answer, role: 'bot' });
        }
      } catch (error) {
        this.hideTyping();
        this.addMessage('Sorry, I encountered an error. Please try again.', 'bot', 'error');
        console.error('[Chatbot] API Error:', error);
      }
    }

    addMessage(text, role, type = '') {
      const message = document.createElement('div');
      message.className = `chatbot-message ${role} ${type}`;
      message.textContent = text;
      this.messagesArea.appendChild(message);
      this.scrollToBottom();
    }

    showTyping() {
      if (this.typingIndicator) return;
      
      this.typingIndicator = document.createElement('div');
      this.typingIndicator.className = 'chatbot-typing';
      this.typingIndicator.innerHTML = '<span></span><span></span><span></span>';
      this.messagesArea.appendChild(this.typingIndicator);
      this.scrollToBottom();
      this.isLoading = true;
    }

    hideTyping() {
      if (this.typingIndicator) {
        this.typingIndicator.remove();
        this.typingIndicator = null;
      }
      this.isLoading = false;
    }

    saveMessage(text, role) {
      this.session.history.push({
        text,
        role,
        timestamp: Date.now()
      });
      this.sessionManager.saveSession(this.session);
    }

    renderMessages() {
      this.messagesArea.innerHTML = '';
      
      if (this.session.history.length === 0) {
        this.renderWelcome();
        return;
      }

      this.session.history.forEach(msg => {
        this.addMessage(msg.text, msg.role);
      });
    }

    renderWelcome() {
      const welcome = document.createElement('div');
      welcome.className = 'chatbot-welcome';
      welcome.innerHTML = `
        <div class="chatbot-welcome-icon">${ICONS.chat}</div>
        <p>Hello! How can I help you today?</p>
      `;
      this.messagesArea.appendChild(welcome);
    }

    scrollToBottom() {
      this.messagesArea.scrollTop = this.messagesArea.scrollHeight;
    }

    // ============================================
    // API INTEGRATION
    // ============================================

    async apiChat(question) {
      const authToken = window.chatbotConfig?.authToken;
      const headers = {
        'Content-Type': 'application/json'
      };

      if (authToken) {
        headers['Authorization'] = `Bearer ${authToken}`;
      }

      const response = await fetch(`${this.config.apiUrl}/api/chat`, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          session_id: this.session.id,
          question,
          user_id: this.session.userId,
          email: window.chatbotConfig?.email
        })
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      return response.json();
    }
  }

  // ============================================
  // INITIALIZATION
  // ============================================

  function initWidget() {
    // Get configuration from script tag
    const script = document.currentScript || document.querySelector('script[data-api-url]');
    
    if (!script) {
      console.error('[Chatbot] No script tag with data-api-url found');
      return;
    }

    const config = {
      apiUrl: script.dataset.apiUrl || script.getAttribute('data-api-url'),
      chatbotId: script.dataset.chatbotId || script.getAttribute('data-chatbot-id'),
      position: script.dataset.position || 'right',
      offset: {
        bottom: parseInt(script.dataset.offsetBottom || '20', 10),
        right: parseInt(script.dataset.offsetRight || '20', 10),
        left: parseInt(script.dataset.offsetLeft || '20', 10)
      }
    };

    // Merge with window.chatbotConfig
    if (window.chatbotConfig) {
      Object.assign(config, window.chatbotConfig);
    }

    // Create widget instance
    new ChatWidget(config);
  }

  // Initialize when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initWidget);
  } else {
    initWidget();
  }

})();
