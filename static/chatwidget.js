/**
 * RAG Chatbot Widget - Embeddable Chat Interface
 * 
 * Usage:
 * <script src="chatwidget.js"></script>
 * <script>
 *   ChatWidget.init({
 *     apiUrl: 'http://localhost:5000',
 *     user_id: 'user123',
 *     username: 'John Doe',
 *     email: 'john@example.com',
 *     device_id: 'web_browser_001',
 *     theme: 'light',
 *     position: 'bottom-right'
 *   });
 * </script>
 */

(function() {
    'use strict';

    // Security configuration
    const SECURITY_CONFIG = {
        maxMessageLength: 2000,
        maxConversationHistory: 50,
        rateLimitWindow: 60000, // 1 minute
        rateLimitMaxRequests: 10,
        allowedOrigins: [], // Will be populated with apiUrl domain
        sessionTimeout: 30 * 60 * 1000, // 30 minutes
        maxRetries: 3,
        requestTimeout: 30000 // 30 seconds
    };

    // Rate limiting state
    let requestHistory = [];
    let lastActivityTime = Date.now();
    let requestCount = 0;
    let isBlocked = false;

    // Widget configuration
    let config = {
        apiUrl: 'http://localhost:5000',
        user_id: null,
        username: null,
        email: null,
        device_id: null,
        theme: 'light',
        position: 'bottom-right',
        title: 'Chat Assistant',
        welcomeMessage: 'Hi! How can I help you today?',
        apiKey: null, // Optional API key for authentication
        allowedDomains: [], // Domains allowed to use this widget
        persistentHistoryCount: 10, // Number of messages to persist across sessions
        autoScrollToBottom: true, // Automatically scroll to bottom to show latest messages
        smoothScrolling: false // Use smooth scrolling animation
    };

    // Widget state
    let isOpen = false;
    let isInitialized = false;
    let conversationHistory = [];
    let sessionId = null;

    // DOM elements
    let widgetContainer = null;
    let chatWindow = null;
    let messagesContainer = null;
    let inputField = null;
    let sendButton = null;
    let toggleButton = null;

    // Security functions
    const SecurityManager = {
        validateConfig: function(options) {
            // Validate API URL
            if (!options.apiUrl || typeof options.apiUrl !== 'string') {
                throw new Error('ChatWidget: apiUrl is required and must be a string');
            }
            
            try {
                const url = new URL(options.apiUrl);
                if (!['http:', 'https:'].includes(url.protocol)) {
                    throw new Error('ChatWidget: apiUrl must use http or https protocol');
                }
            } catch (e) {
                throw new Error('ChatWidget: Invalid apiUrl format');
            }

            // Validate domain restrictions
            if (options.allowedDomains && options.allowedDomains.length > 0) {
                const currentDomain = window.location.hostname;
                if (!options.allowedDomains.includes(currentDomain)) {
                    throw new Error(`ChatWidget: Domain ${currentDomain} is not authorized`);
                }
            }

            // Sanitize user inputs
            if (options.user_id) options.user_id = this.sanitizeInput(options.user_id);
            if (options.username) options.username = this.sanitizeInput(options.username);
            if (options.email) options.email = this.sanitizeInput(options.email);
            if (options.device_id) options.device_id = this.sanitizeInput(options.device_id);
            if (options.title) options.title = this.sanitizeInput(options.title);

            return options;
        },

        sanitizeInput: function(input, isUserInput = true) {
            if (typeof input !== 'string') return input;
            // Apply length limit only for user inputs, not bot responses
            if (isUserInput) {
                return input.replace(/[<>"\'/\\&]/g, '').trim().substring(0, 100);
            } else {
                // For bot responses, only sanitize dangerous characters but don't truncate
                return input.replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, '').trim();
            }
        },

        checkRateLimit: function() {
            const now = Date.now();
            
            // Clean old requests
            requestHistory = requestHistory.filter(time => now - time < SECURITY_CONFIG.rateLimitWindow);
            
            // Check rate limit
            if (requestHistory.length >= SECURITY_CONFIG.rateLimitMaxRequests) {
                isBlocked = true;
                setTimeout(() => { isBlocked = false; }, SECURITY_CONFIG.rateLimitWindow);
                return false;
            }
            
            requestHistory.push(now);
            return true;
        },

        validateMessage: function(message) {
            if (!message || typeof message !== 'string') {
                throw new Error('Invalid message format');
            }
            
            if (message.length > SECURITY_CONFIG.maxMessageLength) {
                throw new Error(`Message too long (max ${SECURITY_CONFIG.maxMessageLength} characters)`);
            }
            
            // Basic XSS protection
            const sanitized = message.replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, '');
            return sanitized.trim();
        },

        checkSession: function() {
            const now = Date.now();
            if (now - lastActivityTime > SECURITY_CONFIG.sessionTimeout) {
                conversationHistory = [];
                sessionId = null;
                return false;
            }
            lastActivityTime = now;
            return true;
        },

        generateSessionId: function() {
            return 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
        }
    };

    // ChatWidget object
    const ChatWidget = {
        init: function(options = {}) {
            if (isInitialized) {
                console.warn('ChatWidget already initialized');
                return;
            }

            try {
                // Validate configuration
                options = SecurityManager.validateConfig(options);
                
                // Merge options with default config
                config = { ...config, ...options };

                // Generate secure session ID
                sessionId = SecurityManager.generateSessionId();

                // Generate device_id if not provided
                if (!config.device_id) {
                    config.device_id = 'web_' + Math.random().toString(36).substr(2, 9);
                }

                // Initialize when DOM is ready
                if (document.readyState === 'loading') {
                    document.addEventListener('DOMContentLoaded', () => {
                        this.initializeWidget();
                    });
                } else {
                    this.initializeWidget();
                }
            } catch (error) {
                console.error('ChatWidget initialization failed:', error.message);
                return;
            }
        },

        initializeWidget: function() {
            // Initialize the widget
            this.createStyles();
            this.createWidget();
            this.bindEvents();
            
            isInitialized = true;
            console.log('ChatWidget initialized');
        },

        createStyles: function() {
            const style = document.createElement('style');
            style.textContent = `
                .chat-widget-container {
                    position: fixed;
                    z-index: 9999;
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                }

                .chat-widget-container.bottom-right {
                    bottom: 20px;
                    right: 20px;
                }

                .chat-widget-container.bottom-left {
                    bottom: 20px;
                    left: 20px;
                }

                .chat-widget-toggle {
                    width: 60px;
                    height: 60px;
                    border-radius: 50%;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    border: none;
                    cursor: pointer;
                    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2);
                    transition: all 0.3s ease;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    color: white;
                    font-size: 24px;
                }

                .chat-widget-toggle:hover {
                    transform: scale(1.1);
                    box-shadow: 0 6px 20px rgba(0, 0, 0, 0.3);
                }

                .chat-widget-window {
                    width: 350px;
                    height: 500px;
                    background: white;
                    border-radius: 12px;
                    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
                    display: none;
                    flex-direction: column;
                    position: absolute;
                    bottom: 80px;
                    right: 0;
                    overflow: hidden;
                }

                .chat-widget-container.bottom-left .chat-widget-window {
                    right: auto;
                    left: 0;
                }

                .chat-widget-header {
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 16px;
                    font-weight: 600;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                }

                .chat-widget-close {
                    background: none;
                    border: none;
                    color: white;
                    font-size: 18px;
                    cursor: pointer;
                    padding: 0;
                    width: 24px;
                    height: 24px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                }

                .chat-widget-messages {
                    flex: 1;
                    overflow-y: auto;
                    padding: 16px;
                    background: #f8f9fa;
                }

                .chat-widget-message {
                    margin-bottom: 12px;
                    display: flex;
                    align-items: flex-start;
                }

                .chat-widget-message.user {
                    justify-content: flex-end;
                }

                .chat-widget-message-bubble {
                    max-width: 80%;
                    padding: 10px 14px;
                    border-radius: 18px;
                    font-size: 14px;
                    line-height: 1.4;
                    word-wrap: break-word;
                    white-space: pre-wrap;
                    overflow-wrap: break-word;
                }

                .chat-widget-message.user .chat-widget-message-bubble {
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                }

                .chat-widget-message.bot .chat-widget-message-bubble {
                    background: white;
                    color: #333;
                    border: 1px solid #e0e0e0;
                }

                .chat-widget-input-container {
                    padding: 16px;
                    background: white;
                    border-top: 1px solid #e0e0e0;
                    display: flex;
                    gap: 8px;
                }

                .chat-widget-input {
                    flex: 1;
                    padding: 10px 14px;
                    border: 1px solid #e0e0e0;
                    border-radius: 20px;
                    font-size: 14px;
                    outline: none;
                    resize: none;
                    font-family: inherit;
                }

                .chat-widget-input:focus {
                    border-color: #667eea;
                }

                .chat-widget-send {
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    border: none;
                    border-radius: 50%;
                    width: 40px;
                    height: 40px;
                    cursor: pointer;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-size: 16px;
                    transition: all 0.2s ease;
                }

                .chat-widget-send:hover {
                    transform: scale(1.1);
                }

                .chat-widget-send:disabled {
                    background: #ccc;
                    cursor: not-allowed;
                    transform: none;
                }

                .chat-widget-typing {
                    display: flex;
                    align-items: center;
                    gap: 4px;
                    padding: 8px 14px;
                    background: white;
                    border-radius: 18px;
                    margin-bottom: 12px;
                    border: 1px solid #e0e0e0;
                }

                .chat-widget-typing-dot {
                    width: 8px;
                    height: 8px;
                    border-radius: 50%;
                    background: #667eea;
                    animation: typing 1.4s infinite ease-in-out;
                }

                .chat-widget-typing-dot:nth-child(1) { animation-delay: -0.32s; }
                .chat-widget-typing-dot:nth-child(2) { animation-delay: -0.16s; }

                @keyframes typing {
                    0%, 80%, 100% { transform: scale(0.8); opacity: 0.5; }
                    40% { transform: scale(1); opacity: 1; }
                }

                .chat-widget-session-info {
                    font-size: 12px;
                    color: #666;
                    padding: 8px 16px;
                    background: #f0f0f0;
                    border-bottom: 1px solid #e0e0e0;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                }

                .chat-widget-clear-btn {
                    background: none;
                    border: none;
                    color: #666;
                    font-size: 12px;
                    cursor: pointer;
                    text-decoration: underline;
                }

                .chat-widget-clear-btn:hover {
                    color: #333;
                }

                @media (max-width: 480px) {
                    .chat-widget-window {
                        width: calc(100vw - 40px);
                        height: calc(100vh - 100px);
                        bottom: 80px;
                        right: 20px;
                    }

                    .chat-widget-container.bottom-left .chat-widget-window {
                        left: 20px;
                        right: auto;
                    }
                }
            `;
            document.head.appendChild(style);
        },

        createWidget: function() {
            // Create container
            widgetContainer = document.createElement('div');
            widgetContainer.className = `chat-widget-container ${config.position}`;

            // Create toggle button
            toggleButton = document.createElement('button');
            toggleButton.className = 'chat-widget-toggle';
            toggleButton.innerHTML = '💬';
            toggleButton.title = 'Open Chat';

            // Create chat window
            chatWindow = document.createElement('div');
            chatWindow.className = 'chat-widget-window';

            // Create header
            const header = document.createElement('div');
            header.className = 'chat-widget-header';
            header.innerHTML = `
                <span>${config.title}</span>
                <button class="chat-widget-close">×</button>
            `;

            // Create session info
            const sessionInfo = document.createElement('div');
            sessionInfo.className = 'chat-widget-session-info';
            sessionInfo.innerHTML = `
                <span class="session-type">Loading...</span>
                <button class="chat-widget-clear-btn">Clear Chat</button>
            `;

            // Create messages container
            messagesContainer = document.createElement('div');
            messagesContainer.className = 'chat-widget-messages';

            // Create input container
            const inputContainer = document.createElement('div');
            inputContainer.className = 'chat-widget-input-container';

            inputField = document.createElement('textarea');
            inputField.className = 'chat-widget-input';
            inputField.placeholder = 'Type your message...';
            inputField.rows = 1;

            sendButton = document.createElement('button');
            sendButton.className = 'chat-widget-send';
            sendButton.innerHTML = '➤';
            sendButton.title = 'Send message';

            // Assemble the widget
            inputContainer.appendChild(inputField);
            inputContainer.appendChild(sendButton);

            chatWindow.appendChild(header);
            chatWindow.appendChild(sessionInfo);
            chatWindow.appendChild(messagesContainer);
            chatWindow.appendChild(inputContainer);

            widgetContainer.appendChild(toggleButton);
            widgetContainer.appendChild(chatWindow);

            // Add to page (ensure body exists)
            if (document.body) {
                document.body.appendChild(widgetContainer);
            } else {
                console.error('ChatWidget: document.body not available');
                return;
            }

            // Load chat history first, then add welcome message if no history exists
            this.loadChatHistory().then((historyLoaded) => {
                // Add welcome message only if no history was loaded
                if (config.welcomeMessage && !historyLoaded) {
                    this.addMessage(config.welcomeMessage, 'bot');
                }
                
                // Ensure we scroll to bottom after everything is loaded
                setTimeout(() => {
                    this.scrollToBottom();
                }, 100);
            });

            // Load session info
            this.loadSessionInfo();
        },

        bindEvents: function() {
            // Toggle button
            toggleButton.addEventListener('click', () => {
                this.toggleWidget();
            });

            // Close button
            chatWindow.querySelector('.chat-widget-close').addEventListener('click', () => {
                this.closeWidget();
            });

            // Clear button
            chatWindow.querySelector('.chat-widget-clear-btn').addEventListener('click', () => {
                this.clearConversation();
            });

            // Send button
            sendButton.addEventListener('click', () => {
                this.sendMessage();
            });

            // Input field
            inputField.addEventListener('keypress', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    this.sendMessage();
                }
            });

            // Auto-resize textarea
            inputField.addEventListener('input', () => {
                inputField.style.height = 'auto';
                inputField.style.height = Math.min(inputField.scrollHeight, 100) + 'px';
            });

            // Click outside to close
            document.addEventListener('click', (e) => {
                if (isOpen && !widgetContainer.contains(e.target)) {
                    this.closeWidget();
                }
            });
        },

        toggleWidget: function() {
            if (isOpen) {
                this.closeWidget();
            } else {
                this.openWidget();
            }
        },

        openWidget: function() {
            chatWindow.style.display = 'flex';
            toggleButton.innerHTML = '×';
            toggleButton.title = 'Close Chat';
            isOpen = true;
            
            // Focus input and scroll to bottom
            setTimeout(() => {
                inputField.focus();
                // Ensure we scroll to the bottom when opening
                this.scrollToBottom();
            }, 100);
        },

        closeWidget: function() {
            chatWindow.style.display = 'none';
            toggleButton.innerHTML = '💬';
            toggleButton.title = 'Open Chat';
            isOpen = false;
        },

        scrollToBottom: function(forceSmooth = null) {
            if (messagesContainer && config.autoScrollToBottom) {
                const useSmooth = forceSmooth !== null ? forceSmooth : config.smoothScrolling;
                if (useSmooth) {
                    messagesContainer.scrollTo({
                        top: messagesContainer.scrollHeight,
                        behavior: 'smooth'
                    });
                } else {
                    messagesContainer.scrollTop = messagesContainer.scrollHeight;
                }
            }
        },

        addMessage: function(text, sender, isError = false, enableTyping = false, storeInHistory = true) {
            const messageDiv = document.createElement('div');
            messageDiv.className = `chat-widget-message ${sender}`;
            
            const bubble = document.createElement('div');
            bubble.className = 'chat-widget-message-bubble';
            
            if (isError) {
                bubble.style.background = '#ffebee';
                bubble.style.color = '#c62828';
                bubble.style.border = '1px solid #ffcdd2';
            }
            
            messageDiv.appendChild(bubble);
            messagesContainer.appendChild(messageDiv);
            
            // Store in history with security limits (only for new messages, not loaded history)
            if (storeInHistory) {
                conversationHistory.push({ 
                    text: SecurityManager.sanitizeInput(text, sender === 'user'), 
                    sender, 
                    timestamp: new Date().toISOString(),
                    sessionId: sessionId
                });
                
                // Limit conversation history size
                if (conversationHistory.length > SECURITY_CONFIG.maxConversationHistory) {
                    conversationHistory = conversationHistory.slice(-SECURITY_CONFIG.maxConversationHistory);
                }
            }
            
            // Enable typing effect for bot messages
            if (enableTyping && sender === 'bot') {
                this.typeMessage(bubble, text);
            } else {
                bubble.innerHTML = this.formatMessage(text, sender === 'user');
                // Scroll to bottom
                this.scrollToBottom();
            }
        },

        typeMessage: function(element, text, index = 0) {
            const formattedText = this.formatMessage(text, false); // false = not user input
            
            // Simple character-by-character typing for better compatibility
            const plainText = text.replace(/\*\*(.*?)\*\*/g, '$1')
                                 .replace(/\*(.*?)\*/g, '$1')
                                 .replace(/`(.*?)`/g, '$1');
            
            if (index < plainText.length) {
                const currentText = plainText.substring(0, index + 1);
                
                // Apply formatting to the current text without truncation
                const displayText = SecurityManager.sanitizeInput(currentText, false)
                    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                    .replace(/\*(.*?)\*/g, '<em>$1</em>')
                    .replace(/`(.*?)`/g, '<code>$1</code>')
                    .replace(/\n/g, '<br>');
                
                element.innerHTML = displayText;
                
                // Scroll to bottom during typing
                this.scrollToBottom();
                
                // Continue typing
                setTimeout(() => {
                    this.typeMessage(element, text, index + 1);
                }, 25); // Adjust speed here (lower = faster)
            } else {
                // Typing complete - apply full formatting without truncation
                element.innerHTML = formattedText;
                messagesContainer.scrollTop = messagesContainer.scrollHeight;
            }
        },

        formatMessage: function(text, isUserInput = false) {
            // Sanitize and format text for display
            const sanitized = SecurityManager.sanitizeInput(text, isUserInput);
            
            // Simple formatting for bot responses
            return sanitized
                .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                .replace(/\*(.*?)\*/g, '<em>$1</em>')
                .replace(/`(.*?)`/g, '<code>$1</code>')
                .replace(/\n/g, '<br>');
        },

        showTyping: function() {
            const typingDiv = document.createElement('div');
            typingDiv.className = 'chat-widget-typing';
            typingDiv.innerHTML = `
                <div class="chat-widget-typing-dot"></div>
                <div class="chat-widget-typing-dot"></div>
                <div class="chat-widget-typing-dot"></div>
            `;
            messagesContainer.appendChild(typingDiv);
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
            return typingDiv;
        },

        hideTyping: function(typingDiv) {
            if (typingDiv && typingDiv.parentNode) {
                typingDiv.parentNode.removeChild(typingDiv);
            }
        },

        sendMessage: function() {
            const message = inputField.value.trim();
            if (!message) return;

            try {
                // Security validations
                if (isBlocked) {
                    this.addMessage('Rate limit exceeded. Please wait before sending another message.', 'bot', true);
                    return;
                }

                if (!SecurityManager.checkRateLimit()) {
                    this.addMessage('Too many requests. Please wait a moment before trying again.', 'bot', true);
                    return;
                }

                if (!SecurityManager.checkSession()) {
                    this.addMessage('Session expired. Please refresh the page to continue.', 'bot', true);
                    return;
                }

                // Validate and sanitize message
                const sanitizedMessage = SecurityManager.validateMessage(message);
                if (!sanitizedMessage) {
                    this.addMessage('Invalid message format. Please try again.', 'bot', true);
                    return;
                }

                // Disable input
                inputField.disabled = true;
                sendButton.disabled = true;

                // Add user message
                this.addMessage(sanitizedMessage, 'user');
                
                // Clear input
                inputField.value = '';
                inputField.style.height = 'auto';

                // Show typing indicator
                const typingDiv = this.showTyping();

                // Send to API
                this.sendToAPI(sanitizedMessage).then(response => {
                    this.hideTyping(typingDiv);
                    this.addMessage(response.answer, 'bot', false, true); // Enable typing effect
                    this.updateSessionInfo(response.user_info);
                }).catch(error => {
                    this.hideTyping(typingDiv);
                    this.addMessage('Sorry, I encountered an error. Please try again.', 'bot', true);
                    console.error('Chat error:', error);
                }).finally(() => {
                    // Re-enable input
                    inputField.disabled = false;
                    sendButton.disabled = false;
                    inputField.focus();
                });

            } catch (error) {
                this.addMessage(error.message, 'bot', true);
                console.error('Security validation failed:', error);
            }
        },

        sendToAPI: function(question) {
            const payload = {
                question: question,
                user_id: config.user_id,
                username: config.username,
                email: config.email,
                device_id: config.device_id,
                session_id: sessionId,
                timestamp: Date.now()
            };

            // Build headers
            const headers = {
                'Content-Type': 'application/json',
                'X-Widget-Origin': window.location.origin,
                'X-Widget-Referrer': window.location.href,
                'X-Widget-User-Agent': navigator.userAgent
            };

            // Add API key if configured
            if (config.apiKey) {
                headers['Authorization'] = `Bearer ${config.apiKey}`;
            }

            // Create abort controller for timeout
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), SECURITY_CONFIG.requestTimeout);

            return fetch(`${config.apiUrl}/ask`, {
                method: 'POST',
                headers: headers,
                body: JSON.stringify(payload),
                signal: controller.signal,
                credentials: 'same-origin'
            }).then(response => {
                clearTimeout(timeoutId);
                
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                
                // Validate response content type
                const contentType = response.headers.get('content-type');
                if (!contentType || !contentType.includes('application/json')) {
                    throw new Error('Invalid response format');
                }
                
                return response.json();
            }).then(data => {
                // Basic response validation
                if (!data || typeof data !== 'object') {
                    throw new Error('Invalid response data');
                }
                
                return data;
            }).catch(error => {
                clearTimeout(timeoutId);
                
                if (error.name === 'AbortError') {
                    throw new Error('Request timeout');
                }
                
                throw error;
            });
        },

        loadChatHistory: function() {
            // Only load history if user identification is available
            if (!config.user_id && !config.email && !config.device_id) {
                return Promise.resolve(false);
            }

            const payload = {
                user_id: config.user_id,
                username: config.username,
                email: config.email,
                device_id: config.device_id,
                limit: config.persistentHistoryCount
            };

            return fetch(`${config.apiUrl}/widget_history`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Widget-Origin': window.location.origin
                },
                body: JSON.stringify(payload)
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                console.log('Widget history loaded:', data);
                if (data.history && Array.isArray(data.history) && data.history.length > 0) {
                    console.log(`Loading ${data.history.length} messages from history`);
                    // Load messages without typing effect and without storing in history again
                    data.history.forEach((message, index) => {
                        console.log('Loading message:', message);
                        this.addMessage(message.content, message.role === 'user' ? 'user' : 'bot', false, false, false);
                        // Scroll to bottom after each message to ensure proper positioning
                        if (index === data.history.length - 1) {
                            setTimeout(() => this.scrollToBottom(), 50);
                        }
                    });
                    
                    // Scroll to bottom after loading history
                    if (data.history.length > 0) {
                        this.scrollToBottom();
                    }
                    
                    return true; // History was loaded
                } else {
                    return false; // No history found
                }
            })
            .catch(error => {
                console.error('Error loading chat history:', error);
                return false; // Return false on error
            });
        },

        loadSessionInfo: function() {
            const payload = {
                user_id: config.user_id,
                username: config.username,
                email: config.email,
                device_id: config.device_id
            };

            const options = {
                method: (config.user_id || config.email || config.device_id) ? 'POST' : 'GET',
                headers: {
                    'Content-Type': 'application/json',
                }
            };

            if (options.method === 'POST') {
                options.body = JSON.stringify(payload);
            }

            fetch(`${config.apiUrl}/session_info`, options)
                .then(response => response.json())
                .then(data => {
                    this.updateSessionInfo(data);
                })
                .catch(error => {
                    console.error('Error loading session info:', error);
                });
        },

        updateSessionInfo: function(data) {
            const sessionInfoEl = chatWindow.querySelector('.session-type');
            if (data && data.session_type) {
                const sessionType = data.session_type === 'persistent' ? 'Logged in' : 'Guest';
                const messageCount = data.stats ? data.stats.total_messages : 0;
                sessionInfoEl.textContent = `${sessionType} • ${messageCount} messages`;
            } else {
                sessionInfoEl.textContent = 'Guest • 0 messages';
            }
        },

        clearConversation: function() {
            if (!confirm('Are you sure you want to clear the conversation?')) {
                return;
            }

            const payload = {
                user_id: config.user_id,
                username: config.username,
                email: config.email,
                device_id: config.device_id
            };

            fetch(`${config.apiUrl}/clear_session`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(payload)
            }).then(response => response.json())
                .then(data => {
                    if (data.success) {
                        // Clear UI
                        messagesContainer.innerHTML = '';
                        conversationHistory = [];
                        
                        // Add welcome message
                        if (config.welcomeMessage) {
                            this.addMessage(config.welcomeMessage, 'bot');
                        }
                        
                        // Update session info
                        this.loadSessionInfo();
                    }
                })
                .catch(error => {
                    console.error('Error clearing conversation:', error);
                });
        },

        // Public methods
        destroy: function() {
            if (widgetContainer && widgetContainer.parentNode) {
                widgetContainer.parentNode.removeChild(widgetContainer);
            }
            isInitialized = false;
            isOpen = false;
        },

        updateConfig: function(newConfig) {
            config = { ...config, ...newConfig };
            this.loadSessionInfo();
        }
    };

    // Global object
    window.ChatWidget = ChatWidget;

    // Auto-initialize if config is provided
    if (window.chatWidgetConfig) {
        ChatWidget.init(window.chatWidgetConfig);
    }

})();